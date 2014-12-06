# -*- coding: utf-8 -*-

from django.contrib import admin
from forum.models import OsqaCategory,User
from forum.forms import QuestionEditorField
#from library.uicomponent.inputs.widgets import AutoCompleteInput
from django.core.urlresolvers import reverse
from django.forms import forms
import settings
import os
from wmd.widgets import WMDWidget


#
#class AnonymousQuestionAdmin(admin.ModelAdmin):
#    """AnonymousQuestion admin class"""
#
#class NodeAdmin(admin.ModelAdmin):
#    """Question admin class"""
#
class CategoryAdmin(admin.ModelAdmin):
    """Category admin class"""

    fields = ('name','order_no','notice','body_template',)
    def formfield_for_dbfield(self, db_field, **kwargs):
#        if db_field.name == 'mail_recipients':
#           kwargs['widget'] = AutoCompleteInput(search_model=User, token_limit=75,
#                    placeholder="Please enter mail recipient Names.",
#                    search_url=reverse('matching_mails'))

        if db_field.name == 'body_template':
           kwargs['widget'] = WMDWidget

        if db_field.name == 'notice':
           kwargs['widget'] = WMDWidget

        return super(CategoryAdmin,self).formfield_for_dbfield(db_field,**kwargs)


    def save_model(self, request, obj, form, change):
        obj.created_by = User.objects.get(username = request.user) # no need to check for it.
        obj.save()

    class Media:
        static_url = getattr(settings, 'STATIC_URL', '/static')
        js = (os.path.join(static_url,'common/jquery-ui-1.9.2/js/jquery-1.8.3.js'),)


#class TagAdmin(admin.ModelAdmin):
#    """Tag admin class"""
#
#class Answerdmin(admin.ModelAdmin):
#    """Answer admin class"""
#
#class CommentAdmin(admin.ModelAdmin):
#    """  admin class"""
#
#class VoteAdmin(admin.ModelAdmin):
#    """  admin class"""
#
#class FlaggedItemAdmin(admin.ModelAdmin):
#    """  admin class"""
#
#class FavoriteQuestionAdmin(admin.ModelAdmin):
#    """  admin class"""
#
#class QuestionRevisionAdmin(admin.ModelAdmin):
#    """  admin class"""
#
#class AnswerRevisionAdmin(admin.ModelAdmin):
#    """  admin class"""
#
#class AwardAdmin(admin.ModelAdmin):
#    """  admin class"""
#
#class BadgeAdmin(admin.ModelAdmin):
#    """  admin class"""
#
#class ReputeAdmin(admin.ModelAdmin):
#    """  admin class"""
#
#class ActionAdmin(admin.ModelAdmin):
#    """  admin class"""

#class BookAdmin(admin.ModelAdmin):
#    """  admin class"""

#class BookAuthorInfoAdmin(admin.ModelAdmin):
#    """  admin class"""

#class BookAuthorRssAdmin(admin.ModelAdmin):
#    """  admin class"""

#admin.site.register(Node, NodeAdmin)
admin.site.register(OsqaCategory, CategoryAdmin)
#admin.site.register(QuestionRevision, QuestionRevisionAdmin)
#admin.site.register(AnswerRevision, AnswerRevisionAdmin)
#admin.site.register(Badge, BadgeAdmin)
#admin.site.register(Award, AwardAdmin)
#admin.site.register(Action, ActionAdmin)
#admin.site.register(Book, BookAdmin)
#admin.site.register(BookAuthorInfo, BookAuthorInfoAdmin)
#admin.site.register(BookAuthorRss, BookAuthorRssAdmin)
