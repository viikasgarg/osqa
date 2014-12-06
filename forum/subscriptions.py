import os
import re
import datetime
import logging
from forum.models import User, Question, Comment, QuestionSubscription, SubscriptionSettings, Answer
from forum.utils.mail import send_template_email
from django.utils.translation import ugettext as _
from forum.actions import AskAction, AnswerAction, CommentAction, AcceptAnswerAction, UserJoinsAction, QuestionViewAction, ReviseAction
from forum import settings
from django.db.models import Q, F
from django import template
from django.utils.safestring import mark_safe
from forum.utils.diff import textDiff as htmldiff


def create_subscription_if_not_exists(question, user):
    try:
        subscription = QuestionSubscription.objects.get(question=question, user=user)
        return subscription
    except QuestionSubscription.MultipleObjectsReturned:
        pass
    except QuestionSubscription.DoesNotExist:
        subscription = QuestionSubscription(question=question, user=user)
        subscription.save()
        return subscription
    except Exception, e:
        logging.error(e)

    return False

def remove_subscription_if_exists(question, user):
    try:
        subscription = QuestionSubscription.objects.get(question=question, user=user)
        subscription.delete()
    except QuestionSubscription.MultipleObjectsReturned:
        pass
    except QuestionSubscription.DoesNotExist:
        pass
    except Exception, e:
        logging.error(e)

    return True


def create_subscription_for_mailing_list(question,userquery):
        userlist = [user for user in userquery if user != question.author]
        existingUserList = [subscription.user for  subscription in QuestionSubscription.objects.filter(question=question)]

## remove deleted Mailing List subscriptions
        for sub_remove in list(set(existingUserList) - set (userlist)):
                subscriptions = QuestionSubscription.objects.filter(question=question, user=sub_remove)
                subscriptions.delete()

## Add Mailing List subscriptions
        for sub_add in list(set(userlist) - set (existingUserList)):
                subscription = QuestionSubscription(question=question, user=sub_add)
                subscription.save()


def filter_subscribers(subscribers):
    subscribers = subscribers.exclude(is_active=False)

    if settings.DONT_NOTIFY_UNVALIDATED:
        return subscribers.exclude(email_isvalid=False)
    else:
        return subscribers

def question_posted(action, new):
    question = action.node

    if not question.is_notifiable:
        return

    '''
## Mailing List Depending Upon Category
    _recipient_ids = ",".join([category.mail_recipients for category in OsqaCategory.objects.filter(id__in = question.category.split(','))]).split(",")
    recipient_ids =[ recipient.strip()  for recipient in _recipient_ids if recipient.strip() ]
    if len(recipient_ids):
        category_subscribers = User.objects.filter(id__in =recipient_ids ).distinct()
        all_subscribers = category_subscribers

## Mailing List Subscribers
    recipient_list = [ recipient.strip()  for recipient in question.recipientnames.split(',') if recipient.strip() ]

    if len(recipient_list):
        mailing_subscribers = User.objects.filter(id__in = recipient_list ).distinct()

        if len(recipient_ids):
                all_subscribers = category_subscribers  | mailing_subscribers
        else:
                all_subscribers = mailing_subscribers
    '''
    send_template_email(all_subscribers, "notifications/newquestion.html", {'question': question})

    subscription = QuestionSubscription(question=question, user=question.author)
    subscription.save()

    new_subscribers = User.objects.filter(
            Q(subscription_settings__all_questions=True) |
            Q(subscription_settings__all_questions_watched_tags=True,
                    marked_tags__name__in=question.tagnames.split(' '),
                    tag_selections__reason='good'))

    for user in new_subscribers:
        create_subscription_if_not_exists(question, user)

AskAction.hook(question_posted)


def answer_posted(action, new):
    answer = action.node
    question = answer.question

    logging.error("Answer posted: %s" % str(answer.is_notifiable))

    if not answer.is_notifiable or not question.is_notifiable:
        return

    subscribers = question.subscribers.filter(
            subscription_settings__enable_notifications=True,
            subscription_settings__notify_answers=True,
            subscription_settings__subscribed_questions='i'
    ).exclude(id=answer.author.id).distinct()

    subscribers = filter_subscribers(subscribers)

    send_template_email(subscribers, "notifications/newanswer.html", {'answer': answer})

    create_subscription_if_not_exists(question, answer.author)

AnswerAction.hook(answer_posted)


def revision_posted(action, new):
    post = action.node

    if post.node_type =="question":
        question = post

    else:
        question = post.abs_parent

    revisions = list(post.revisions.order_by('revised_at'))
    rev_ctx = []

    for i, revision in enumerate(revisions):
        rev_ctx.append(dict(inst=revision, html=template.loader.get_template('node/revision.html').render(template.Context({
        'title': revision.title,
        'html': revision.html,
        'category':revision.category_name(),
        'tags': revision.tagname_list(),
#        'recipients':revision.recipientname_list(),
        }))))

        if i > 0:
            rev_ctx[i]['diff'] = mark_safe(htmldiff(rev_ctx[i-1]['html'], rev_ctx[i]['html']))
        else:
            rev_ctx[i]['diff'] = mark_safe(rev_ctx[i]['html'])

        if not (revision.summary):
            rev_ctx[i]['summary'] = _('Revision n. %(rev_number)d') % {'rev_number': revision.revision}
        else:
            rev_ctx[i]['summary'] = revision.summary

    rev_ctx.reverse()

    #update mailing list according to last revision of category

    if post.node_type =="question":
       prev_question = revisions[-2]
       present_question = revisions[-1]
       if (prev_question.category != present_question.category):
           ## remove previous category subscriptions
           _recipient_ids = ",".join([category.mail_recipients for category in OsqaCategory.objects.filter(id__in =  prev_question.category.split(','))]).split(",")
           recipient_ids =[ recipient.strip()  for recipient in _recipient_ids if recipient.strip() ]
           if len(recipient_ids):
               category_subscribers = User.objects.filter(id__in =recipient_ids ).distinct()
               for subscriber in category_subscribers:
                   remove_subscription_if_exists(question, subscriber)

           ## remove previous mailing subscriptions
       if (prev_question.recipientnames != present_question.recipientnames):
           recipient_list = [ recipient.strip()  for recipient in prev_question.recipientnames.split(',') if recipient.strip() ]
           if len(recipient_list):
               mailing_subscribers = User.objects.filter(id__in = recipient_list ).distinct()
               for subscriber in mailing_subscribers:
                   remove_subscription_if_exists(question, subscriber)

        ## Add present mailing subscriptions
       if (prev_question.recipientnames != present_question.recipientnames):
           recipient_list = [ recipient.strip()  for recipient in present_question.recipientnames.split(',') if recipient.strip() ]
           if len(recipient_list):
               mailing_subscribers = User.objects.filter(id__in = recipient_list ).distinct()
               for subscriber in mailing_subscribers:
                   create_subscription_if_not_exists(question, subscriber)



       if (prev_question.category != present_question.category):
        ## Add present category subscriptions
        _recipient_ids = ",".join([category.mail_recipients for category in OsqaCategory.objects.filter(id__in =  present_question.category.split(','))]).split(",")
        recipient_ids =[ recipient.strip()  for recipient in _recipient_ids if recipient.strip() ]
        if len(recipient_ids):
            category_subscribers = User.objects.filter(id__in =recipient_ids ).distinct()
            for subscriber in category_subscribers:
                create_subscription_if_not_exists(question, subscriber)


    if not post.is_notifiable or not question.is_notifiable:
        return

    subscribers = question.subscribers.all().distinct()
    '''
    addressbook_contacts = question.addressbook_contacts() ## query containing all users which are in address book
    if  addressbook_contacts.exists():
        if subscribers.exists():
             subscribers |= addressbook_contacts ## adding address book contacts
        else:
             subscribers = addressbook_contacts
    '''
    if subscribers.exists():
        subscribers = filter_subscribers(subscribers.exclude(id=post.author.id))


        try:
            sender_mail = User.objects.get(user = post.author).mail;
            sender = {'name':post.author.username,'email':sender_mail }
        except: ## Use Default forum mail address in case of error
            sender_mail = unicode(settings.DEFAULT_FROM_EMAIL)
            sender = u'%s <%s>' % (unicode(settings.APP_SHORT_NAME), unicode(settings.DEFAULT_FROM_EMAIL))

        if subscribers.exists():
            send_template_email(subscribers, "notifications/emailrevision.html", {'post': post, 'revisions' : rev_ctx,'question':question},sender = sender, reply_to = sender_mail)

    create_subscription_if_not_exists(question, post.author)

ReviseAction.hook(revision_posted)




def comment_posted(action, new):
    comment = action.node
    post = comment.parent
    question = comment.abs_parent
    answers = comment.author.get_visible_answers(question)

    if not comment.is_notifiable or not post.is_notifiable:
        return

    if post.__class__ == Question:
        question = post
    else:
        question = post.question

    q_filter = Q(subscription_settings__notify_comments=True) | Q(subscription_settings__notify_comments_own_post=True, id=post.author.id)

    inreply = re.search('@\w+', comment.comment)
    if inreply is not None:
        q_filter = q_filter | Q(subscription_settings__notify_reply_to_comments=True,
                                username__istartswith=inreply.group(0)[1:],
                                nodes__parent=post, nodes__node_type="comment")

    subscribers = question.subscribers.filter(
            q_filter, subscription_settings__subscribed_questions='i', subscription_settings__enable_notifications=True
    ).exclude(id=comment.user.id).distinct()

    subscribers = filter_subscribers(subscribers)


    send_template_email(subscribers, "notifications/newcomment.html", {'comment': comment})

    create_subscription_if_not_exists(question, comment.user)

CommentAction.hook(comment_posted)


def answer_accepted(action, new):
    question = action.node.question

    if not question.is_notifiable:
        return

    subscribers = question.subscribers.filter(
            subscription_settings__enable_notifications=True,
            subscription_settings__subscribed_questions='i'
    ).exclude(id=action.node.nstate.accepted.by.id).distinct()

    subscribers = filter_subscribers(subscribers)

    send_template_email(subscribers, "notifications/answeraccepted.html", {'answer': action.node})

AcceptAnswerAction.hook(answer_accepted)


def member_joined(action, new):
    subscribers = User.objects.filter(
            subscription_settings__enable_notifications=True,
            subscription_settings__member_joins='i'
    ).exclude(id=action.user.id).distinct()

    subscribers = filter_subscribers(subscribers)

    send_template_email(subscribers, "notifications/newmember.html", {'newmember': action.user})

UserJoinsAction.hook(member_joined)

def question_viewed(action, new):
    if not action.viewuser.is_authenticated():
        return

    try:
        subscription = QuestionSubscription.objects.get(question=action.node, user=action.viewuser)
        subscription.last_view = datetime.datetime.now()
        subscription.save()
    except:
        if action.viewuser.subscription_settings.questions_viewed:
            subscription = QuestionSubscription(question=action.node, user=action.viewuser)
            subscription.save()

QuestionViewAction.hook(question_viewed)


#todo: translate this
#record_answer_event_re = re.compile("You have received (a|\d+) .*new response.*")
#def record_answer_event(instance, created, **kwargs):
#    if created:
#        q_author = instance.question.author
#        found_match = False
#        #print 'going through %d messages' % q_author.message_set.all().count()
#        for m in q_author.message_set.all():
##            #print m.message
# #           match = record_answer_event_re.search(m.message)
#            if match:
#                found_match = True
#                try:
#                    cnt = int(match.group(1))
#                except:
#                    cnt = 1
##                m.message = u"You have received %d <a href=\"%s?sort=responses\">new responses</a>."\
# #                           % (cnt+1, q_author.get_profile_url())
#
#                m.save()
#                break
#        if not found_match:
#            msg = u"You have received a <a href=\"%s?sort=responses\">new response</a>."\
#                    % q_author.get_profile_url()
#
#            q_author.message_set.create(message=msg)
#
#post_save.connect(record_answer_event, sender=Answer)
