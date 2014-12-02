import os.path
from base import Setting, SettingSet
from django.utils.translation import ugettext_lazy as _

UPLOAD_SET = SettingSet('paths', _('File upload settings'), _("File uploads related settings."), 600)

UPFILES_FOLDER = Setting('UPFILES_FOLDER', os.path.join(os.path.dirname(os.path.dirname(__file__)),'upfiles'), UPLOAD_SET, dict(
label = _("Uploaded files folder"),
help_text = _("The filesystem path where uploaded files will be stored. Please note that this folder must exist.")))

UPFILES_ALIAS = Setting('UPFILES_ALIAS', '/upfiles/', UPLOAD_SET, dict(
label = _("Uploaded files alias"),
help_text = _("The url alias for uploaded files. Notice that if you change this setting, you'll need to restart your site.")))

ALLOW_MAX_FILE_SIZE = Setting('ALLOW_MAX_FILE_SIZE', 2.5, UPLOAD_SET, dict(
label = _("Max file size"),
help_text = _("The maximum allowed file size for uploads in mb.")))

UPFILES_ATTACH_FOLDER = Setting('UPFILES_ATTACH_FOLDER', os.path.join(os.path.dirname(os.path.dirname(__file__)),'upfiles_attach'), UPLOAD_SET, dict(
label = _("Uploaded attach files folder"),
help_text = _("The filesystem path where uploaded files will be stored. Please note that this folder must exist.")))

UPFILES_ATTACH_ALIAS = Setting('UPFILES_ATTACH_ALIAS','/forum/upfiles_attach/', UPLOAD_SET, dict(
label = _("Uploaded attach files alias"),
help_text = _("The url alias for uploaded files. Notice that if you change this setting, you'll need to restart your site.")))

ALLOW_ATTACH_MAX_FILE_SIZE = Setting('ALLOW_ATTACH_MAX_FILE_SIZE', 5, UPLOAD_SET, dict(
label = _("Max attach file size"),
help_text = _("The maximum allowed attach file size for uploads in mb.")))

CLEANUP_BY_DAY = Setting('CLEANUP_BY_DAY', 30, UPLOAD_SET, dict(
label = _("Cleanup By Days"),
help_text = _("Server Deletes files Older By Given days")))
