# -*- coding: utf-8 -*-

import cgi
import logging

from urllib import urlopen,  urlencode
from forum.authentication.base import AuthenticationConsumer, ConsumerTemplateContext, InvalidAuthentication

from django.conf import settings as django_settings
from django.utils.encoding import smart_unicode
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

import settings

from json import load as load_json


class googleAuthConsumer(AuthenticationConsumer):

    def prepare_authentication_request(self, request, redirect_to):
        args = dict(#"225108411153-i28bb8kou45pfpudvc7kq54fqaoetbu6.apps.googleusercontent.com"
            client_id=settings.GOOGLE_API_KEY,
            redirect_uri="%s%s" % (django_settings.APP_URL, redirect_to),
            scope="email",
            response_type="code"
        )
        print "there"
        google_api_authentication_url = "https://accounts.google.com/o/oauth2/auth?" + urlencode(args)

        return google_api_authentication_url

    def process_authentication_request(self, request):
        try:
            redirect_uri = "%s%s" % (django_settings.APP_URL, reverse('auth_provider_done', prefix='/', kwargs={'provider': 'google'}))
            args = dict(client_id=settings.GOOGLE_API_KEY, redirect_uri=redirect_uri)

            args["client_secret"] = settings.GOOGLE_APP_SECRET  #google APP Secret

            args["code"] = request.GET.get("code", None)
            response = cgi.parse_qs(urlopen("https://accounts.google.com/o/oauth2/access_token?" + urlencode(args)).read())
            access_token = response["access_token"][-1]


            user_data = self.get_user_data(access_token)
            assoc_key = user_data["id"]

            # Store the access token in cookie
            request.session["access_token"] = access_token
            request.session["assoc_key"] = assoc_key

            # Return the association key
            return assoc_key
        except Exception, e:
            logging.error("Problem during google authentication: %s" % e)
            raise InvalidAuthentication(_("Something wrond happened during google authentication, administrators will be notified"))

    def get_user_data(self, access_token):
        profile = load_json(urlopen("https://accounts.google.com/o/oauth2/me?" + urlencode(dict(access_token=access_token))))

        name = profile["name"]

        # Check whether the length if the email is greater than 75, if it is -- just replace the email
        # with a blank string variable, otherwise we're going to have trouble with the Django model.
        email = smart_unicode(profile['email'])
        if len(email) > 75:
            email = ''

        # If the name is longer than 30 characters - leave it blank
        if len(name) > 30:
            name = ''

        # Return the user data.
        return {
            'id' : profile['id'],
            'username': name,
            'email': email,
        }

class googleAuthContext(ConsumerTemplateContext):
    mode = 'BIGICON'
    type = 'CUSTOM'
    weight = 100
    human_name = 'Google+'
    code_template = 'modules/googleauth/button.html'
    extra_css = []

    API_KEY = settings.GOOGLE_API_KEY
