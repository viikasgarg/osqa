# encoding:utf-8
import os.path

import datetime
import time
from django.core.urlresolvers import reverse
from django.core.files.storage import FileSystemStorage
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.utils.html import *
from django.utils.translation import ugettext as _

from django.contrib import messages

from forum.actions import AskAction, AnswerAction, ReviseAction, RollbackAction, RetagAction, AnswerToQuestionAction, CommentToQuestionAction
from forum.forms import *
from forum.models import *
from forum.utils import html
from forum.http_responses import HttpResponseUnauthorized
from django.utils.safestring import mark_safe

from vars import PENDING_SUBMISSION_SESSION_ATTR

@csrf_exempt
def upload(request):#ajax upload file to a question or answer
    class FileTypeNotAllow(Exception):
        pass
    class FileSizeNotAllow(Exception):
        pass
    class UploadPermissionNotAuthorized(Exception):
        pass

    xml_template = "<result><msg><![CDATA[%s]]></msg><error><![CDATA[%s]]></error><file_url>%s</file_url></result>"

    try:
        f = request.FILES['file-upload']
        # check upload permission
        if not request.user.can_upload_files():
            raise UploadPermissionNotAuthorized()

        # check file type
        try:
            file_name_suffix = os.path.splitext(f.name)[1].lower()
        except KeyError:
            raise FileTypeNotAllow()

        if not file_name_suffix in ('.jpg', '.jpeg', '.gif', '.png', '.bmp', '.tiff', '.ico'):
            raise FileTypeNotAllow()

        storage = FileSystemStorage(str(settings.UPFILES_FOLDER), str(settings.UPFILES_ALIAS))
        new_file_name = storage.save("_".join(f.name.split()), f)
        # check file size
        # byte
        size = storage.size(new_file_name)

        if size > float(settings.ALLOW_MAX_FILE_SIZE) * 1024 * 1024:
            storage.delete(new_file_name)
            raise FileSizeNotAllow()

        result = xml_template % ('Good', '', str(settings.UPFILES_ALIAS) + new_file_name)
    except UploadPermissionNotAuthorized:
        result = xml_template % ('', _('uploading images is limited to users with >60 reputation points'), '')
    except FileTypeNotAllow:
        result = xml_template % ('', _("allowed file types are 'jpg', 'jpeg', 'gif', 'bmp', 'png', 'tiff'"), '')
    except FileSizeNotAllow:
        result = xml_template % ('', _("maximum upload file size is %sM") % settings.ALLOW_MAX_FILE_SIZE, '')
    except Exception, e:
        result = xml_template % ('', _('Error uploading file. Please contact the site administrator. Thank you. %s' % e), '')

    return HttpResponse(result, mimetype="application/xml")

@csrf_exempt
def upload_attachments(request):
    class FileTypeNotAllow(Exception):
        pass
    class FileSizeNotAllow(Exception):
        pass

    result = '{"status" : "%s","message":"%s","filename":"%s","filesize":"%s"}'
    new_file_name = ''
    size = 0
    try:
        token = request.POST.get('token','default')
        f = request.FILES.get('upload_files')
        # check upload permission
        if not request.user.can_upload_files():
            raise UploadPermissionNotAuthorized()

        # check file type
        try:
            file_name_suffix = os.path.splitext(f.name)[1].lower()
        except KeyError:
            raise FileTypeNotAllow()

        if file_name_suffix in ('.exe','.bat','.sh'):
            raise FileTypeNotAllow()

        storage = FileSystemStorage(os.path.join(settings.UPFILES_ATTACH_FOLDER,token), str(settings.UPFILES_ATTACH_ALIAS))
        new_file_name = storage.save("_".join(f.name.split()), f)
        # check file size
        # byte
        size = storage.size(new_file_name)

        if size > float(settings.ALLOW_ATTACH_MAX_FILE_SIZE) * 1024 * 1024:
            storage.delete(new_file_name)
            raise FileSizeNotAllow()

        Attachment(name=new_file_name, folder_name=token, size=size).save()

        result = result % (('upload'),_('File Uploaded'),new_file_name,size)
    except FileTypeNotAllow:
        result = result % (('error'),_("Non allowed file types are '.exe','.bat','.sh'"),new_file_name,size)
    except FileSizeNotAllow:
        result = result % (('error'),_("Maximum upload file size is %sM") % settings.ALLOW_ATTACH_MAX_FILE_SIZE,new_file_name,size)
    except Exception, e:
        result = result % (('error'),_('Error uploading file. Please contact the site administrator. Thank you. %s' % e),new_file_name,size)

    return HttpResponse(result, mimetype="text/plain")


@csrf_exempt
def delete_attachments(request):
    result = '{"status" : "%s","message":"%s","filename":"%s"}'

    try:
        token = request.POST.get('token','default')
        file_name = request.POST.get('fileNames')
        folder_name = os.path.join(settings.UPFILES_ATTACH_FOLDER,token) 
        storage = FileSystemStorage(folder_name, str(settings.UPFILES_ATTACH_ALIAS))
        #new_file_name = storage.save("_".join(f.split()), f)

        storage.delete(file_name)
        if os.path.isdir(folder_name):
            if len(os.listdir(folder_name)) == 0:
                os.rmdir(folder_name)
        attachment = Attachment.objects.filter(folder_name=token,name=file_name)
        if len(attachment) != 0:
            attachment.delete()
        result = result % (('delete'),_('File Deleted'),file_name)
    except:
        result = result % (('error'),_('Error on Server Side'),file_name)

    return HttpResponse(result, mimetype="text/plain")

def ask(request,category):
    form = None
    folder_name = None
    if request.POST:
        folder_name = request.POST.get('attachement_token')
        if request.session.pop('reviewing_pending_data', False):
            form = AskForm(initial=request.POST, user=request.user)
        elif "text" in request.POST:
            form = AskForm(request.POST, user=request.user)
            if form.is_valid():
                if request.user.is_authenticated() and request.user.email_valid_and_can_ask():
                    ask_action = AskAction(user=request.user, ip=request.META['REMOTE_ADDR']).save(data=form.cleaned_data)
                    question = ask_action.node
                    #folder_name = int(form.cleaned_data['attachement_token'])
                    Attachment.objects.filter(folder_name = folder_name).update(node = question)

                    messages.add_message(request, messages.INFO, message=ask_action.describe(request.user))
                    if settings.WIKI_ON and request.POST.get('wiki', False):
                        question.nstate.wiki = ask_action

                    return HttpResponseRedirect(question.get_absolute_url())
                else:
                    request.session[PENDING_SUBMISSION_SESSION_ATTR] = {
                        'POST': request.POST,
                        'data_name': _("question"),
                        'type': 'ask',
                        'submission_url': reverse('ask'),
                        'time': datetime.datetime.now()
                    }

                    if request.user.is_authenticated():
                        messages.info(request, _("Your question is pending until you %s.") % html.hyperlink(
                            django_settings.APP_URL + reverse('send_validation_email', prefix='/'), _("validate your email")
                        ))
                        return HttpResponseRedirect(reverse('index'))
                    else:
                        return HttpResponseRedirect(reverse('auth_signin'))
        elif "go" in request.POST:
            form = AskForm({'title': request.POST['q']}, user=request.user)
            
    if not form:
        form = AskForm(user=request.user)
        form.fields['defaultrecipients'].widget.attrs['style'] = "width:53%;display:block"
        form.fields['defaultrecipients'].widget.attrs['readonly'] = "readonly"

    upload_template = ""
    upload_file_template = "{name:'%s',size:%s,extension:'%s'},"
    if not folder_name:
        folder_name = form.fields['attachement_token'].initial

    attachments = Attachment.objects.filter(folder_name=folder_name)
    for attachment in attachments:
        if len(attachment.name):
            upload_template += upload_file_template%(attachment.name,attachment.size,"."+attachment.name.split('.')[-1])
    upload_template  = "[" + upload_template[:-1] + "]"
    
    return render_to_response('ask.html', {
        'form' : form,
        'tab' : 'ask',
        'uploaded_files':mark_safe(upload_template),
        #'notice':category.notice,
        }, context_instance=RequestContext(request))

def convert_to_question(request, id):
    user = request.user

    node_type = request.GET.get('node_type', 'answer')
    if node_type == 'comment':
        node = get_object_or_404(Comment, id=id)
        action_class = CommentToQuestionAction
    else:
        node = get_object_or_404(Answer, id=id)
        action_class = AnswerToQuestionAction

    if not user.can_convert_to_question(node):
        return HttpResponseUnauthorized(request)

    return _edit_question(request, node, template='node/convert_to_question.html', summary=_("Converted to question"),
                           action_class =action_class, allow_rollback=False, url_getter=lambda a: Question.objects.get(id=a.id).get_absolute_url())

def edit_question(request, id):
    question = get_object_or_404(Question, id=id)
    if question.nis.deleted and not request.user.can_view_deleted_post(question):
        raise Http404
    if request.user.can_edit_post(question):
        return _edit_question(request, question)
    elif request.user.can_retag_questions():
        return _retag_question(request, question)
    else:
        raise Http404

def _retag_question(request, question):
    if request.method == 'POST':
        form = RetagQuestionForm(question, request.POST)
        if form.is_valid():
            if form.has_changed():
                RetagAction(user=request.user, node=question, ip=request.META['REMOTE_ADDR']).save(data=dict(tagnames=form.cleaned_data['tags']))

            return HttpResponseRedirect(question.get_absolute_url())
    else:
        form = RetagQuestionForm(question)
    return render_to_response('question_retag.html', {
        'question': question,
        'form' : form,
        #'tags' : _get_tags_cache_json(),
    }, context_instance=RequestContext(request))

def _edit_question(request, question, template='question_edit.html', summary='', action_class=ReviseAction,
                   allow_rollback=True, url_getter=lambda q: q.get_absolute_url(), additional_context=None):
    if request.method == 'POST':
        revision_form = RevisionForm(question, data=request.POST)
        revision_form.is_valid()
        revision = question.revisions.get(revision=revision_form.cleaned_data['revision'])

        if 'select_revision' in request.POST:
            form = EditQuestionForm(question, request.user, revision)
        else:
            form = EditQuestionForm(question, request.user, revision, data=request.POST)

        if not 'select_revision' in request.POST and form.is_valid():
            folder_name = int(form.cleaned_data['attachement_token'])
            Attachment.objects.filter(folder_name = folder_name).update(node = question)
            if form.has_changed():
                action = action_class(user=request.user, node=question, ip=request.META['REMOTE_ADDR']).save(data=form.cleaned_data)

                if settings.WIKI_ON:
                    if request.POST.get('wiki', False) and not question.nis.wiki:
                        question.nstate.wiki = action
                    elif question.nis.wiki and (not request.POST.get('wiki', False)) and request.user.can_cancel_wiki(question):
                        question.nstate.wiki = None
            else:
                if not revision == question.active_revision:
                    if allow_rollback:
                        RollbackAction(user=request.user, node=question).save(data=dict(activate=revision))
                    else:
                        pass

            return HttpResponseRedirect(url_getter(question))
    else:
        revision_form = RevisionForm(question)
        form = EditQuestionForm(question, request.user, initial={'summary': summary})

    folder_name  = form.fields['attachement_token'].initial

    upload_template = ""
    upload_file_template = "{name:'%s',size:%s,extension:'%s'},"
    attachments = Attachment.objects.filter(folder_name=folder_name)
    for attachment in attachments:
        if len(attachment.name):
            upload_template += upload_file_template%(attachment.name,attachment.size,"."+attachment.name.split('.')[-1])
    upload_template  = "[" + upload_template[:-1] + "]"

    context = {
        'question': question,
        'revision_form': revision_form,
        'form' : form,
        'uploaded_files':mark_safe(upload_template),
    }

    if not (additional_context is None):
        context.update(additional_context)

    return render_to_response(template, context, context_instance=RequestContext(request))


def edit_answer(request, id):
    answer = get_object_or_404(Answer, id=id)
    if answer.deleted and not request.user.can_view_deleted_post(answer):
        raise Http404
    elif not request.user.can_edit_post(answer):
        raise Http404

    if request.method == "POST":
        revision_form = RevisionForm(answer, data=request.POST)
        revision_form.is_valid()
        revision = answer.revisions.get(revision=revision_form.cleaned_data['revision'])

        if 'select_revision' in request.POST:
            form = EditAnswerForm(answer, request.user, revision)
        else:
            form = EditAnswerForm(answer, request.user, revision, data=request.POST)

        if not 'select_revision' in request.POST and form.is_valid():
            if form.has_changed():
                action = ReviseAction(user=request.user, node=answer, ip=request.META['REMOTE_ADDR']).save(data=form.cleaned_data)

                if settings.WIKI_ON:
                    if request.POST.get('wiki', False) and not answer.nis.wiki:
                        answer.nstate.wiki = action
                    elif answer.nis.wiki and (not request.POST.get('wiki', False)) and request.user.can_cancel_wiki(answer):
                        answer.nstate.wiki = None
            else:
                if not revision == answer.active_revision:
                    RollbackAction(user=request.user, node=answer, ip=request.META['REMOTE_ADDR']).save(data=dict(activate=revision))

            return HttpResponseRedirect(answer.get_absolute_url())

    else:
        revision_form = RevisionForm(answer)
        form = EditAnswerForm(answer, request.user)
    return render_to_response('answer_edit.html', {
                              'answer': answer,
                              'revision_form': revision_form,
                              'form': form,
                              }, context_instance=RequestContext(request))

def answer(request, id):
    question = get_object_or_404(Question, id=id)

    if request.POST:
        form = AnswerForm(request.POST, request.user)

        if request.session.pop('reviewing_pending_data', False) or not form.is_valid():
            request.session['redirect_POST_data'] = request.POST
            return HttpResponseRedirect(question.get_absolute_url() + '#fmanswer')

        if request.user.is_authenticated() and request.user.email_valid_and_can_answer():
            answer_action = AnswerAction(user=request.user, ip=request.META['REMOTE_ADDR']).save(dict(question=question, **form.cleaned_data))
            answer = answer_action.node
            messages.add_message(request, messages.INFO, message=answer_action.describe(request.user))
            if settings.WIKI_ON and request.POST.get('wiki', False):
                answer.nstate.wiki = answer_action

            return HttpResponseRedirect(answer.get_absolute_url())
        else:
            request.session[PENDING_SUBMISSION_SESSION_ATTR] = {
                'POST': request.POST,
                'data_name': _("answer"),
                'type': 'answer',
                'submission_url': reverse('answer', kwargs={'id': id}),
                'time': datetime.datetime.now()
            }

            if request.user.is_authenticated():
                messages.info(request, _("Your answer is pending until you %s.") % html.hyperlink(
                    django_settings.APP_URL + reverse('send_validation_email', prefix='/'), _("validate your email")
                ))
                return HttpResponseRedirect(question.get_absolute_url())
            else:
                return HttpResponseRedirect(reverse('auth_signin'))

    return HttpResponseRedirect(question.get_absolute_url())


def manage_pending_data(request, action, forward=None):
    pending_data = request.session.pop(PENDING_SUBMISSION_SESSION_ATTR, None)

    if not pending_data:
        raise Http404

    if action == _("cancel"):
        return HttpResponseRedirect(forward or request.META.get('HTTP_REFERER', '/'))
    else:
        if action == _("review"):
            request.session['reviewing_pending_data'] = True

        request.session['redirect_POST_data'] = pending_data['POST']
        return HttpResponseRedirect(pending_data['submission_url'])


