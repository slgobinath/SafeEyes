import os

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk
from gi.repository import GdkPixbuf

WIDGET_HORIZONTAL_LINE_LENGTH = 64
WIDGET_HORIZONTAL_LINE = '─' * WIDGET_HORIZONTAL_LINE_LENGTH


class TrayAction:
    """
    Data object wrapping name, icon and action.
    """

    def __init__(self, name, icon, action, system_icon):
        self.name = name
        self.__icon = icon
        self.action = action
        self.system_icon = system_icon
        self.__toolbar_buttons = []

    def get_icon(self):
        if self.system_icon:
            return self.__icon
        else:
            image = TrayAction.__load_and_scale_image(self.__icon, 16, 16)
            image.show()
            return image

    def add_toolbar_button(self, button):
        self.__toolbar_buttons.append(button)

    def reset(self):
        for button in self.__toolbar_buttons:
            button.hide()
        self.__toolbar_buttons.clear()

    @staticmethod
    def build(name, icon_path, icon_id, action):
        image = TrayAction.__load_and_scale_image(icon_path, 12, 12)
        if image is None:
            return TrayAction(name, icon_id, action, True)
        else:
            return TrayAction(name, icon_path, action, False)

    @staticmethod
    def __load_and_scale_image(path: str, width: int, height: int):
        if not os.path.isfile(path):
            return None
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename=path,
            width=width,
            height=height,
            preserve_aspect_ratio=True)
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        return image


class Widget:
    """
    Break screen widget.
    """

    def __init__(self, title: str, content: str):
        self.title: str = title
        self.content: str = content

    def is_empty(self) -> bool:
        return self.title is None or self.content is None

    def format(self) -> str:
        if self.is_empty():
            return ''
        else:
            return '<b>{}</b>\n{}\n{}\n\n\n'.format(self.title, WIDGET_HORIZONTAL_LINE, self.content)


class BreakAction:

    def __init__(self, skipped: bool, postponed: bool, postpone_duration: int):
        self.skipped = skipped
        self.postponed = postponed
        self.postpone_duration = postpone_duration

    def not_allowed(self) -> bool:
        return self.skipped or self.postponed

    @staticmethod
    def allow():
        return BreakAction(False, False, -1)

    @staticmethod
    def skip():
        return BreakAction(True, False, -1)

    @staticmethod
    def postpone(duration: int = -1):
        return BreakAction(False, True, duration)
