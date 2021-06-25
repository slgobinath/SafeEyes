import gettext
import locale
import logging

from safeeyes import utility


def init_locale():
    system_locale = gettext.translation('safeeyes', localedir=utility.LOCALE_PATH,
                                        languages=[utility.system_locale(), 'en_US'], fallback=True)
    system_locale.install()
    locale.bindtextdomain('safeeyes', utility.LOCALE_PATH)
    return system_locale


def _(message: str) -> str:
    try:
        return gettext.gettext(message)
    except BaseException:
        logging.exception("Error in getting the translation for %s", message)
        return message
