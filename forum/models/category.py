import datetime
from base import *

from django.conf import settings as django_settings
from django.core.cache.backends.base import BaseCache
from django.utils.translation import ugettext as _
from django.utils.encoding import  force_unicode


class ActiveCategoryManager(CachedManager):
    use_for_related_fields = True

    def get_query_set(self):
        return super(ActiveCategoryManager, self).get_query_set()
#.exclude(used_count__lt=1)
class OsqaCategory(BaseModel):
    name            = models.CharField(max_length=255,unique = True)
    order_no        = models.PositiveIntegerField(default=0)
    created_by      = models.ForeignKey(User, related_name='created_category')
    created_at      = models.DateTimeField(default=datetime.datetime.now, blank=True, null=True)

    # Denormalised data
    used_count      = models.PositiveIntegerField(default=0)
    mail_recipients  = models.CharField(max_length=300,blank=True,null=True) ##vikas.garg
    body_template    = models.TextField(blank=True,null=True)  ##vikas garg
    notice           = models.TextField(blank=True,null=True)  ##vikas garg
    active = ActiveCategoryManager()

    class Meta:
        ordering = ('-used_count', 'name')
        app_label = 'forum'

    def __unicode__(self):
        return force_unicode(self.name)

    def add_to_usage_count(self, value):
        print "Value ", value
        if self.used_count + value < 0:
            self.used_count = 0
        else:
            self.used_count = models.F('used_count') + value

    def cache_key(self):
        return self._generate_cache_key(OsqaCategory.safe_cache_name(self.name))

    @classmethod
    def safe_cache_name(cls, name):
        return "".join([str(ord(c)) for c in name])

    @classmethod
    def infer_cache_key(cls, querydict):
        if 'name' in querydict:
            cache_key = cls._generate_cache_key(cls.safe_cache_name(querydict['name']))

            if len(cache_key) > django_settings.CACHE_MAX_KEY_LENGTH:
                cache_key = cache_key[:django_settings.CACHE_MAX_KEY_LENGTH]

            return cache_key

        return None

    @classmethod
    def value_to_list_on_cache_query(cls):
        return 'name'

    @models.permalink
    def get_absolute_url(self):
        return ('category_questions', (), {'category': self.name})

    def get_mail_recipients(self):
       if self.mail_recipients and self.mail_recipients.strip():
           return "  ".join([user.username for user in User.objects.filter(id__in =self.mail_recipients.split(',')).distinct()])
       else:
           return None

    def get_recipient_list(self):
       if self.mail_recipients and self.mail_recipients.strip():
           return ([user.username for user in User.objects.filter(id__in =self.mail_recipients.split(',')).distinct()])

