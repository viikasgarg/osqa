# -*- coding: utf-8 -*-

from forum.settings import EXT_KEYS_SET
from forum.settings.base import Setting

GOOGLE_API_KEY = Setting('GOOGLE_API_KEY', "225108411153-i28bb8kou45pfpudvc7kq54fqaoetbu6.apps.googleusercontent.com", EXT_KEYS_SET, dict(
label = "google API key",
help_text = """
Get this key at the <a href="https://console.developers.google.com/project/">google developers network</a> to enable
authentication in your site through google.
""",
required=False))

GOOGLE_APP_SECRET = Setting('GOOGLE_APP_SECRET', "QQDrIULVr1ARCYmXqO3aLj32", EXT_KEYS_SET, dict(
label = "google APP secret",
help_text = """
This your google app secret that you'll get in the same place as the API key.
""",
required=False))
