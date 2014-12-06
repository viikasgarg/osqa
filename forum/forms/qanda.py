import re
from datetime import date
import time
from django import forms
from forum.models import *
from django.utils.translation import ugettext as _
import settings as django_settings
from django.utils.encoding import smart_unicode
from general import NextUrlField, UserNameField

from forum import settings, REQUEST_HOLDER

from forum.modules import call_all_handlers

from django.core.urlresolvers import reverse
import logging
from django.utils.html import strip_tags

#from addressbook.models import AddressBook
from django.db.models import Q

class TitleField(forms.CharField):
    def __init__(self, *args, **kwargs):
        super(TitleField, self).__init__(*args, **kwargs)

        self.required = True
        self.max_length = 255
        self.widget = forms.TextInput(attrs={'size' : 70, 'autocomplete' : 'off', 'style' : 'width:53%','maxlength' : self.max_length})
        self.label  = _('Title')
        self.help_text = _('please enter a descriptive title for your question')
        self.initial = ''

    def clean(self, value):
        super(TitleField, self).clean(value)

        if len(strip_tags(value).strip()) < settings.FORM_MIN_QUESTION_TITLE:
            raise forms.ValidationError(_('title must be at least %s characters without HTML tags and spaces') % settings.FORM_MIN_QUESTION_TITLE)

        return strip_tags(value)

class EditorField(forms.CharField):
    def __init__(self, *args, **kwargs):
        super(EditorField, self).__init__(*args, **kwargs)

        self.widget = forms.Textarea(attrs={'id':'editor'})
        self.label  = _('Content')
        self.help_text = u''
        self.initial = ''


class QuestionEditorField(EditorField):
    def __init__(self, *args, **kwargs):
        super(QuestionEditorField, self).__init__(*args, **kwargs)
        self.required = not bool(settings.FORM_EMPTY_QUESTION_BODY)


    def clean(self, value):
        super(QuestionEditorField, self).clean(value)

        if not bool(settings.FORM_EMPTY_QUESTION_BODY) and (len(re.sub('[ ]{2,}', ' ', value)) < settings.FORM_MIN_QUESTION_BODY):
            raise forms.ValidationError(_('question content must be at least %s characters') % settings.FORM_MIN_QUESTION_BODY)

        return value

class AnswerEditorField(EditorField):
    def __init__(self, *args, **kwargs):
        super(AnswerEditorField, self).__init__(*args, **kwargs)
        self.required = True

    def clean(self, value):
        super(AnswerEditorField, self).clean(value)

        if len(re.sub('[ ]{2,}', ' ', value)) < settings.FORM_MIN_QUESTION_BODY:
            raise forms.ValidationError(_('answer content must be at least %s characters') % settings.FORM_MIN_QUESTION_BODY)

        return value


class CategoryNameField(forms.ChoiceField):
    def __init__(self, user=None, *args, **kwargs):
        super(CategoryNameField, self).__init__(*args, **kwargs)

        self.widget.attrs["onchange"]="category_selected(event,this.value)"
        self.widget.attrs["id"]="category"
        self.required = True

        choices = [(category.id, category.name) for category in OsqaCategory.objects.order_by('order_no')]  ## removing "System Authentication" category" (Hard-coded)
        choices.insert(0, (-1,"Select Category"))
        self.choices= choices
        self.initial = self.choices[0]
        #self.max_length = 255
        self.label  = _('Category')
        #self.help_text = _('please use space to separate tags (this enables autocomplete feature)')
        self.help_text = _('Categories are associated with each question asked. Please choose from available categories.')
        #self.user = user

    def clean(self, value):
        super(CategoryNameField, self).clean(value)

        if value == "-1":
            raise forms.ValidationError(_('Please select category (*required)'))

        return value





class TagNamesField(forms.CharField):
    def __init__(self, user=None, *args, **kwargs):
        super(TagNamesField, self).__init__(*args, **kwargs)

        self.required = False
        self.widget = forms.TextInput(attrs={'size' : 70, 'autocomplete' : 'off','style':'width:53%'})
        self.max_length = 255
        self.label  = _('Tags')
        #self.help_text = _('please use space to separate tags (this enables autocomplete feature)')
        self.help_text = _('Tags are short keywords, with no spaces within. At least %(min)s and up to %(max)s tags can be used.') % {
            'min': settings.FORM_MIN_NUMBER_OF_TAGS, 'max': settings.FORM_MAX_NUMBER_OF_TAGS
        }
        self.initial = ''
        self.user = user

    def clean(self, value):
        super(TagNamesField, self).clean(value)

        value = super(TagNamesField, self).clean(value)
        data = value.strip().lower()

        split_re = re.compile(r'[ ,]+')
        list = {}
        for tag in split_re.split(data):
            if len(tag):
                list[tag] = tag

        if len(list) > settings.FORM_MAX_NUMBER_OF_TAGS or len(list) < settings.FORM_MIN_NUMBER_OF_TAGS:
            raise forms.ValidationError(_('please use between %(min)s and %(max)s tags') % { 'min': settings.FORM_MIN_NUMBER_OF_TAGS, 'max': settings.FORM_MAX_NUMBER_OF_TAGS})

        list_temp = []
        tagname_re = re.compile(r'^[\w+#\.-]+$', re.UNICODE)
        for key,tag in list.items():
            if len(tag) > settings.FORM_MAX_LENGTH_OF_TAG or len(tag) < settings.FORM_MIN_LENGTH_OF_TAG:
                raise forms.ValidationError(_('please use between %(min)s and %(max)s characters in you tags') % { 'min': settings.FORM_MIN_LENGTH_OF_TAG, 'max': settings.FORM_MAX_LENGTH_OF_TAG})
            if not tagname_re.match(tag):
                raise forms.ValidationError(_('please use following characters in tags: letters , numbers, and characters \'.#-_\''))
            # only keep one same tag
            if tag not in list_temp and len(tag.strip()) > 0:
                list_temp.append(tag)

        if settings.LIMIT_TAG_CREATION and not self.user.can_create_tags():
            existent = Tag.objects.filter(name__in=list_temp).values_list('name', flat=True)

            if len(existent) < len(list_temp):
                unexistent = [n for n in list_temp if not n in existent]
                raise forms.ValidationError(_("You don't have enough reputation to create new tags. The following tags do not exist yet: %s") %
                        ', '.join(unexistent))


        return u','.join(list_temp)

class MailNamesField(forms.CharField):
    def __init__(self, user=None, *args, **kwargs):
        super(MailNamesField, self).__init__(*args, **kwargs)

        '''
        self.widget = AutoCompleteInput(search_model=User, token_limit=75,
                    placeholder="Please enter mail recipient Names.",
                    search_url=reverse('matching_mails'))
        '''
        self.widget = forms.TextInput(attrs={'size' : 70, 'autocomplete' : 'off','style':'width:53%'})

        self.max_length = 255
        self.label  = _('Add Mail Recipients')
        self.help_text = _('Email Notification will be send to the users added in this field')
        self.initial = ''
        self.user = user
        self.required = False

    def clean(self, value):
        super(MailNamesField, self).clean(value)

        value = super(MailNamesField, self).clean(value)
        data = value.strip().lower()

        split_re = re.compile(r',')
        list = {}
        for mail in split_re.split(data):
            if len(mail):
                list[mail] = mail


        list_temp = []
        for key,mail in list.items():
            # only keep one same mail -- if 1 user is added two times,mail will be send one time.
            if mail not in list_temp and len(mail.strip()) > 0:
                list_temp.append(mail)

        return str(u','.join(list_temp))


class WikiField(forms.BooleanField):
    def __init__(self, disabled=False, *args, **kwargs):
        super(WikiField, self).__init__(*args, **kwargs)
        self.required = False
        self.label  = _('community wiki')
        self.help_text = _('if you choose community wiki option, the question and answer do not generate points and name of author will not be shown')
        if disabled:
            self.widget=forms.CheckboxInput(attrs={'disabled': "disabled"})
    def clean(self,value):
        return value

class EmailNotifyField(forms.BooleanField):
    def __init__(self, *args, **kwargs):
        super(EmailNotifyField, self).__init__(*args, **kwargs)
        self.required = False
        self.widget.attrs['class'] = 'nomargin'

class SummaryField(forms.CharField):
    def __init__(self, *args, **kwargs):
        super(SummaryField, self).__init__(*args, **kwargs)
        self.required = False
        self.widget = forms.TextInput(attrs={'size' : 70, 'autocomplete' : 'off'})
        self.max_length = 300
        self.label  = _('update summary:')
        self.help_text = _('enter a brief summary of your revision (e.g. fixed spelling, grammar, improved style, this field is optional)')


class FeedbackForm(forms.Form):
    message = forms.CharField(label=_('Your message:'), max_length=800,widget=forms.Textarea(attrs={'cols':60}))
    next = NextUrlField()

    def __init__(self, user, *args, **kwargs):
        super(FeedbackForm, self).__init__(*args, **kwargs)
        if not user.is_authenticated():
            self.fields['name'] = forms.CharField(label=_('Your name:'), required=False)
            self.fields['email'] = forms.EmailField(label=_('Email (not shared with anyone):'), required=True)

        # Create anti spam fields
        spam_fields = call_all_handlers('create_anti_spam_field')
        if spam_fields:
            spam_fields = dict(spam_fields)
            for name, field in spam_fields.items():
                self.fields[name] = field

            self._anti_spam_fields = spam_fields.keys()
        else:
            self._anti_spam_fields = []



class AskForm(forms.Form):
    title  = TitleField()
    text   = QuestionEditorField()

    def __init__(self, data=None, user=None, *args, **kwargs):
        super(AskForm, self).__init__(data, *args, **kwargs)
        self.fields['category']   = CategoryNameField(user)
        self.fields['tags']   = TagNamesField(user)
        #self.fields['recipients'] = MailNamesField(user)
        #self.fields['defaultrecipients'] = forms.CharField(label=_('Category Mailing List:'), required=False)
       # self.fields['addressbooks'] = AddressBookField(user)
        self.fields['upload_files'] = forms.FileField(required=False,label=_('Upload Files:'),
                                    help_text='Select files to attach')
        self.fields['form_attachments'] = forms.CharField(widget=forms.HiddenInput(),required=False)
        self.fields['attachement_token'] = forms.CharField(required=False,widget=forms.HiddenInput(),initial = int(time.time() * 1000))

        if not user.is_authenticated() or (int(user.reputation) < settings.CAPTCHA_IF_REP_LESS_THAN and not (user.is_superuser or user.is_staff)):
            spam_fields = call_all_handlers('create_anti_spam_field')
            if spam_fields:
                spam_fields = dict(spam_fields)
                for name, field in spam_fields.items():
                    self.fields[name] = field

                self._anti_spam_fields = spam_fields.keys()
            else:
                self._anti_spam_fields = []

        if settings.WIKI_ON:
            self.fields['wiki'] = WikiField()

class AnswerForm(forms.Form):
    text   = AnswerEditorField()
    wiki   = WikiField()

    def __init__(self, data=None, user=None, *args, **kwargs):
        super(AnswerForm, self).__init__(data, *args, **kwargs)

        if not user.is_authenticated() or (int(user.reputation) < settings.CAPTCHA_IF_REP_LESS_THAN and not (user.is_superuser or user.is_staff)):
            spam_fields = call_all_handlers('create_anti_spam_field')
            if spam_fields:
                spam_fields = dict(spam_fields)
                for name, field in spam_fields.items():
                    self.fields[name] = field

                self._anti_spam_fields = spam_fields.keys()
            else:
                self._anti_spam_fields = []

        if settings.WIKI_ON:
            self.fields['wiki'] = WikiField()


class RecategoryQuestionForm(forms.Form):
    category   = CategoryNameField()
    # initialize the default values
    def __init__(self, question, *args, **kwargs):
        super(RecategoryQuestionForm, self).__init__(*args, **kwargs)
        self.fields['category'].initial = question.category

class RetagQuestionForm(forms.Form):
    tags   = TagNamesField()
    # initialize the default values
    def __init__(self, question, *args, **kwargs):
        super(RetagQuestionForm, self).__init__(*args, **kwargs)
        self.fields['tags'].initial = question.tagnames

class RevisionForm(forms.Form):
    """
    Lists revisions of a Question or Answer
    """
    revision = forms.ChoiceField(widget=forms.Select(attrs={'style' : 'width:520px'}))

    def __init__(self, post, *args, **kwargs):
        super(RevisionForm, self).__init__(*args, **kwargs)

        revisions = post.revisions.all().values_list('revision', 'author__username', 'revised_at', 'summary').order_by('-revised_at')

        date_format = '%c'
        self.fields['revision'].choices = [
            (r[0], u'%s - %s (%s) %s' % (r[0], smart_unicode(r[1]), r[2].strftime(date_format), r[3]))
            for r in revisions]

        self.fields['revision'].initial = post.active_revision.revision

class EditQuestionForm(forms.Form):
    title  = TitleField()
    text   = QuestionEditorField()
    summary = SummaryField()

    def __init__(self, question, user, revision=None, *args, **kwargs):
        super(EditQuestionForm, self).__init__(*args, **kwargs)

        if revision is None:
            revision = question.active_revision

        self.fields['title'].initial = revision.title
        self.fields['text'].initial = revision.body

        self.fields['category'] = CategoryNameField(user)
        self.fields['category'].initial = revision.category

        self.fields['tags'] = TagNamesField(user)
        self.fields['tags'].initial = revision.tagnames

        #self.fields['recipients'] = MailNamesField(user)
        #self.fields['recipients'].initial = revision.recipientnames

#        self.fields['addressbooks'] = AddressBookField(user)
#        self.fields['addressbooks'].initial = revision.addressbooks.split(',')

        self.fields['upload_files'] = forms.FileField(required=False,label=_('Upload Files:'),
                                    help_text='Select files to attach')
        self.fields['form_attachments'] = forms.CharField(widget=forms.HiddenInput(),required=False)
        self.fields['attachement_token'] = forms.CharField(required=False,widget=forms.HiddenInput(),initial = int(time.time() * 1000))

        attachments = Attachment.objects.filter(node=question)
        if len(attachments):
             self.fields['attachement_token'].initial = attachments[0].folder_name
             self.fields['form_attachments'].initial = ";".join([a.name  for a in attachments])

        if not user.is_authenticated() or (int(user.reputation) < settings.CAPTCHA_IF_REP_LESS_THAN and not (user.is_superuser or user.is_staff)):
            spam_fields = call_all_handlers('create_anti_spam_field')
            if spam_fields:
                spam_fields = dict(spam_fields)
                for name, field in spam_fields.items():
                    self.fields[name] = field

                self._anti_spam_fields = spam_fields.keys()
            else:
                self._anti_spam_fields = []

        if settings.WIKI_ON:
            self.fields['wiki'] = WikiField(disabled=(question.nis.wiki and not user.can_cancel_wiki(question)), initial=question.nis.wiki)

class EditAnswerForm(forms.Form):
    text = AnswerEditorField()
    summary = SummaryField()

    def __init__(self, answer, user, revision=None, *args, **kwargs):
        super(EditAnswerForm, self).__init__(*args, **kwargs)

        if revision is None:
            revision = answer.active_revision

        self.fields['text'].initial = revision.body

        if not user.is_authenticated() or (int(user.reputation) < settings.CAPTCHA_IF_REP_LESS_THAN and not (user.is_superuser or user.is_staff)):
            spam_fields = call_all_handlers('create_anti_spam_field')
            if spam_fields:
                spam_fields = dict(spam_fields)
                for name, field in spam_fields.items():
                    self.fields[name] = field

                self._anti_spam_fields = spam_fields.keys()
            else:
                self._anti_spam_fields = []

        if settings.WIKI_ON:
            self.fields['wiki'] = WikiField(disabled=(answer.nis.wiki and not user.can_cancel_wiki(answer)), initial=answer.nis.wiki)

class EditUserForm(forms.Form):
    email = forms.EmailField(label=u'Email', help_text=_('this email does not have to be linked to gravatar'), required=True, max_length=75, widget=forms.TextInput(attrs={'size' : 35}))
    realname = forms.CharField(label=_('Real name'), required=False, max_length=255, widget=forms.TextInput(attrs={'size' : 35}))
    website = forms.URLField(label=_('Website'), required=False, max_length=255, widget=forms.TextInput(attrs={'size' : 35}))
    city = forms.CharField(label=_('Location'), required=False, max_length=255, widget=forms.TextInput(attrs={'size' : 35}))
    birthday = forms.DateField(label=_('Date of birth'), help_text=_('will not be shown, used to calculate age, format: YYYY-MM-DD'), required=False, widget=forms.TextInput(attrs={'size' : 35}))
    about = forms.CharField(label=_('Profile'), required=False, widget=forms.Textarea(attrs={'cols' : 60}))

    def __init__(self, user, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        if settings.EDITABLE_SCREEN_NAME or (REQUEST_HOLDER.request.user.is_authenticated() and REQUEST_HOLDER.request.user.is_superuser):
            self.fields['username'] = UserNameField(label=_('Screen name'))
            self.fields['username'].initial = user.username
            self.fields['username'].user_instance = user
        self.fields['email'].initial = user.email
        self.fields['realname'].initial = user.real_name
        self.fields['website'].initial = user.website
        self.fields['city'].initial = user.location

        if user.date_of_birth is not None:
            self.fields['birthday'].initial = user.date_of_birth

        self.fields['about'].initial = user.about
        self.user = user

    def clean_email(self):
        if self.user.email != self.cleaned_data['email']:
            if settings.EMAIL_UNIQUE:
                if 'email' in self.cleaned_data:
                    from forum.models import User
                    try:
                        User.objects.get(email = self.cleaned_data['email'])
                    except User.DoesNotExist:
                        return self.cleaned_data['email']
                    except User.MultipleObjectsReturned:
                        logging.error("Found multiple users sharing the same email: %s" % self.cleaned_data['email'])

                    raise forms.ValidationError(_('this email has already been registered, please use another one'))
        return self.cleaned_data['email']


NOTIFICATION_CHOICES = (
    ('i', _('Instantly')),
    #('d', _('Daily')),
    #('w', _('Weekly')),
    ('n', _('No notifications')),
)

class SubscriptionSettingsForm(forms.ModelForm):
    enable_notifications = forms.BooleanField(widget=forms.HiddenInput, required=False)
    member_joins = forms.ChoiceField(widget=forms.RadioSelect, choices=NOTIFICATION_CHOICES)
    new_question = forms.ChoiceField(widget=forms.RadioSelect, choices=NOTIFICATION_CHOICES)
    new_question_watched_tags = forms.ChoiceField(widget=forms.RadioSelect, choices=NOTIFICATION_CHOICES)
    subscribed_questions = forms.ChoiceField(widget=forms.RadioSelect, choices=NOTIFICATION_CHOICES)

    class Meta:
        model = SubscriptionSettings
        fields = ['enable_notifications', 'member_joins', 'new_question', 'new_question_watched_tags', 'subscribed_questions']

class UserPreferencesForm(forms.Form):
    sticky_sorts = forms.BooleanField(required=False, initial=False)


class MultiSelectWidget(forms.SelectMultiple):
    css_class = 'multiselect'
    class Media:
        css = {
            'all': (

                django_settings.STATIC_URL + 'multiselect/css/ui.multiselect.css',
            )
        }
        js = (
#            'https://ajax.googleapis.com/ajax/libs/jquery/1.4.4/jquery.min.js',
#            'https://ajax.googleapis.com/ajax/libs/jqueryui/1.8.6/jquery-ui.min.js',

             django_settings.STATIC_URL + 'multiselect/js/ui.multiselect.js',

        )

    def add_css_class(self, attrs):
        attrs = attrs or {}
        if 'class' in attrs:
            attrs['class'] += " %s" % self.css_class
        else:
            attrs['class'] = self.css_class
        return attrs

    def __init__(self, attrs=None):
        attrs = self.add_css_class(attrs)
        super(MultiSelectWidget, self).__init__(attrs=attrs)
