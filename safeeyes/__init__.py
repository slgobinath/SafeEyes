import os

SAFE_EYES_VERSION = "3.0.0"

SAFE_EYES_HOME_DIR = os.path.dirname(os.path.realpath(__file__))
SAFE_EYES_CONFIG_DIR = os.path.join(
    os.environ.get('XDG_CONFIG_HOME') or os.path.join((os.environ.get('HOME') or os.path.expanduser('~')), '.config'),
    'safeeyes')
