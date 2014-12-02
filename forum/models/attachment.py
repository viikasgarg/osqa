from base import *
from django.utils.translation import ugettext as _
from django.db import models
class Attachment(models.Model):
    name      = models.CharField(max_length=300)
    node      = models.ForeignKey(Node, related_name='nodeid', null=True) ##Delete entries on cleanup
    folder_name = models.CharField(max_length=50)
    size = models.IntegerField(default=0)
    added_at  = models.DateTimeField(default=datetime.datetime.now)

    class Meta:
        app_label = 'forum'
