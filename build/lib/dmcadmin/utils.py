import os
from hashlib import md5

from django.conf import settings
from django.utils.timezone import now


def get_path(dir):
    if not os.path.exists(dir):
        try:
            oldmask = os.umask(000)
            os.makedirs(dir, mode=0o777)
            os.umask(oldmask)
        except Exception:
            pass
    return dir


def get_manage_command_log_dir(app, cls_name, file_name=None):
    media_root = settings.MEDIA_ROOT
    media_url = settings.MEDIA_URL
    subdir = cls_name  # maybe manage_command name
    dir = os.path.join(media_root, 'managecommand', 'logs', app, subdir)
    url = os.path.join(media_url, 'managecommand', 'logs', app, subdir)
    if not os.path.exists(dir):
        try:
            oldmask = os.umask(000)
            os.makedirs(dir, mode=0o777)
            os.umask(oldmask)
        except Exception:
            pass
    if file_name:
        dir = os.path.join(dir, file_name)
        url = os.path.join(url, file_name)
    return dir, url


def get_manage_command_log_file(app,cls_name):
    log_file_name = ''.join([now().strftime('%Y_%m_%d_%H_%M_%S'), '.log'])
    log_dir, log_url = get_manage_command_log_dir(app, cls_name, log_file_name)
    console_log_dir, console_log_url = get_manage_command_log_dir(app, cls_name, 'console_' + log_file_name)
    return log_dir, log_url, console_log_dir, console_log_url


def get_instance_file_name(instance, fn):
    subdir = instance.__class__.__name__.lower()
    name = '%s.%s' % (now().strftime('%Y-%m-%d_%H.%M.%S'), fn)
    hash_md5 = md5(name.encode()).hexdigest()
    dir = os.path.join('files', subdir, hash_md5[0], hash_md5[1], hash_md5[2])
    if not os.path.exists(dir):
        try:
            os.makedirs(dir, mode=0o777)
        except Exception:
            pass
    return os.path.join(dir, name)
