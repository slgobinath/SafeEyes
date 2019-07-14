#!/usr/bin/env python
# Safe Eyes is a utility to remind you to take break frequently
# to protect your eyes from eye strain.

# Copyright (C) 2017  Gobinath

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
This module contains utility functions for Safe Eyes and its plugins.
"""

import errno
import imp
import importlib
import json
import locale
import logging
import os
import re
import shutil
import subprocess
import threading
from distutils.version import LooseVersion
from logging.handlers import RotatingFileHandler

import babel.dates
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GdkPixbuf

gi.require_version('Gdk', '3.0')

BIN_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
HOME_DIRECTORY = os.environ.get('HOME') or os.path.expanduser('~')
CONFIG_DIRECTORY = os.path.join(os.environ.get(
    'XDG_CONFIG_HOME') or os.path.join(HOME_DIRECTORY, '.config'), 'safeeyes')
CONFIG_FILE_PATH = os.path.join(CONFIG_DIRECTORY, 'safeeyes.json')
CONFIG_RESOURCE = os.path.join(CONFIG_DIRECTORY, 'resource')
SESSION_FILE_PATH = os.path.join(CONFIG_DIRECTORY, 'session.json')
STYLE_SHEET_PATH = os.path.join(CONFIG_DIRECTORY, 'style/safeeyes_style.css')
SYSTEM_CONFIG_FILE_PATH = os.path.join(BIN_DIRECTORY, "config/safeeyes.json")
SYSTEM_STYLE_SHEET_PATH = os.path.join(
    BIN_DIRECTORY, "config/style/safeeyes_style.css")
LOG_FILE_PATH = os.path.join(HOME_DIRECTORY, 'safeeyes.log')
SYSTEM_PLUGINS_DIR = os.path.join(BIN_DIRECTORY, 'plugins')
USER_PLUGINS_DIR = os.path.join(CONFIG_DIRECTORY, 'plugins')
LOCALE_PATH = os.path.join(BIN_DIRECTORY, 'config/locale')
DESKTOP_ENVIRONMENT = None
IS_WAYLAND = False


def get_resource_path(resource_name):
    """
    Return the user-defined resource if a system resource is overridden by the user.
    Otherwise, return the system resource. Return None if the specified resource does not exist.
    """
    if resource_name is None:
        return None
    resource_location = os.path.join(CONFIG_RESOURCE, resource_name)
    if not os.path.isfile(resource_location):
        resource_location = os.path.join(
            BIN_DIRECTORY, 'resource', resource_name)
        if not os.path.isfile(resource_location):
            # Resource not found
            resource_location = None

    return resource_location


def start_thread(target_function, **args):
    """
    Execute the function in a separate thread.
    """
    thread = threading.Thread(target=target_function, name="WorkThread", daemon=False, kwargs=args)
    thread.start()


def execute_main_thread(target_function, args=None):
    """
    Execute the given function in main thread.
    """
    if args:
        GLib.idle_add(lambda: target_function(args))
    else:
        GLib.idle_add(target_function)


def system_locale(category=locale.LC_MESSAGES):
    """
    Return the system locale. If not available, return en_US.UTF-8.
    """
    try:
        locale.setlocale(locale.LC_ALL, '')
        sys_locale = locale.getlocale(category)[0]
        if not sys_locale:
            sys_locale = 'en_US.UTF-8'
        return sys_locale
    except BaseException:
        # Some systems does not return proper locale
        return 'en_US.UTF-8'


def format_time(time):
    """
    Format time based on the system time.
    """
    sys_locale = system_locale(locale.LC_TIME)
    return babel.dates.format_time(time, format='short', locale=sys_locale)


def mkdir(path):
    """
    Create directory if not exists.
    """
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            logging.error('Error while creating ' + str(path))
            raise


def load_json(json_path):
    """
    Load the JSON file from the given path.
    """
    json_obj = None
    if os.path.isfile(json_path):
        try:
            with open(json_path) as config_file:
                json_obj = json.load(config_file)
        except BaseException:
            pass
    return json_obj


def write_json(json_path, json_obj):
    """
    Write the JSON object at the given path
    """
    try:
        with open(json_path, 'w') as json_file:
            json.dump(json_obj, json_file, indent=4, sort_keys=True)
    except BaseException:
        pass


def delete(file_path):
    """
    Delete the given file or directory
    """
    try:
        os.remove(file_path)
    except OSError:
        pass


def check_plugin_dependencies(plugin_id, plugin_config, plugin_path):
    """
    Check the plugin dependencies.
    """
    # Check the desktop environment
    if plugin_config['dependencies']['desktop_environments']:
        # Plugin has restrictions on desktop environments
        if DESKTOP_ENVIRONMENT not in plugin_config['dependencies']['desktop_environments']:
            return _('Plugin does not support %s desktop environment') % DESKTOP_ENVIRONMENT

    # Check the Python modules
    for module in plugin_config['dependencies']['python_modules']:
        if not module_exist(module):
            return _("Please install the Python module '%s'") % module

    # Check the shell commands
    for command in plugin_config['dependencies']['shell_commands']:
        if not command_exist(command):
            return _("Please install the command-line tool '%s'") % command

    # Check the resources
    for resource in plugin_config['dependencies']['resources']:
        if get_resource_path(resource) is None:
            return _('Please add the resource %(resource)s to %(config_resource)s directory') % {'resource': resource, 'config_resource': CONFIG_RESOURCE}

    plugin_dependency_checker = os.path.join(plugin_path, 'dependency_checker.py')
    if os.path.isfile(plugin_dependency_checker):
        dependency_checker = importlib.import_module((plugin_id + '.dependency_checker'))
        if dependency_checker and hasattr(dependency_checker, "validate"):
            return dependency_checker.validate(plugin_config)

    return None


def load_plugins_config(safeeyes_config):
    """
    Load all the plugins from the given directory.
    """
    configs = []
    for plugin in safeeyes_config.get('plugins'):
        plugin_path = os.path.join(SYSTEM_PLUGINS_DIR, plugin['id'])
        if not os.path.isdir(plugin_path):
            # User plugin
            plugin_path = os.path.join(USER_PLUGINS_DIR, plugin['id'])
        plugin_config_path = os.path.join(plugin_path, 'config.json')
        plugin_icon_path = os.path.join(plugin_path, 'icon.png')
        plugin_module_path = os.path.join(plugin_path, 'plugin.py')
        if not os.path.isfile(plugin_module_path):
            return
        icon = None
        if os.path.isfile(plugin_icon_path):
            icon = plugin_icon_path
        else:
            icon = get_resource_path('ic_plugin.png')
        config = load_json(plugin_config_path)
        if config is None:
            continue
        dependency_description = check_plugin_dependencies(plugin['id'], config, plugin_path)
        if dependency_description:
            plugin['enabled'] = False
            config['error'] = True
            config['meta']['description'] = dependency_description
            icon = get_resource_path('ic_warning.png')
        else:
            config['error'] = False
        config['id'] = plugin['id']
        config['icon'] = icon
        config['enabled'] = plugin['enabled']
        for setting in config['settings']:
            setting['safeeyes_config'] = plugin['settings']
        configs.append(config)
    return configs


def desktop_environment():
    """
    Detect the desktop environment.
    """
    global DESKTOP_ENVIRONMENT
    desktop_session = os.environ.get('DESKTOP_SESSION')
    current_desktop = os.environ.get('XDG_CURRENT_DESKTOP')
    env = 'unknown'
    if desktop_session is not None:
        desktop_session = desktop_session.lower()
        if desktop_session in ['gnome', 'unity', 'budgie-desktop', 'cinnamon', 'mate', 'xfce4', 'lxde', 'pantheon', 'fluxbox', 'blackbox', 'openbox', 'icewm', 'jwm', 'afterstep', 'trinity', 'kde']:
            env = desktop_session
        elif desktop_session.startswith('xubuntu') or (current_desktop is not None and 'xfce' in current_desktop):
            env = 'xfce'
        elif desktop_session.startswith('lubuntu'):
            env = 'lxde'
        elif 'plasma' in desktop_session or desktop_session.startswith('kubuntu') or os.environ.get('KDE_FULL_SESSION') == 'true':
            env = 'kde'
        elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
            env = 'gnome'
        elif desktop_session.startswith('ubuntu'):
            env = 'unity'
    DESKTOP_ENVIRONMENT = env
    return env

def is_wayland():
    """
    Determine if Wayland is running
    https://unix.stackexchange.com/a/325972/222290
    """
    global IS_WAYLAND
    try:
        session_id = subprocess.check_output(['loginctl']).split(b'\n')[1].split()[0]
        output = subprocess.check_output(
            ['loginctl', 'show-session', session_id, '-p', 'Type']
        )
    except BaseException:
        logging.warning('Unable to determine if wayland is running. Assuming no.')
        IS_WAYLAND = False
    else:
        IS_WAYLAND = bool(re.search(b'wayland', output, re.IGNORECASE))
    return IS_WAYLAND


def execute_command(command, args=[]):
    """
    Execute the shell command without waiting for its response.
    """
    if command:
        command_to_execute = []
        if isinstance(command, str):
            command_to_execute.append(command)
        else:
            command_to_execute.extend(command)
        if args:
            command_to_execute.extend(args)
        try:
            subprocess.Popen(command_to_execute)
        except BaseException:
            logging.error('Error in executing the command ' + str(command))


def command_exist(command):
    """
    Check whether the given command exist in the system or not.
    """
    if shutil.which(command):
        return True
    return False


def module_exist(module):
    """
    Check wther the given Python module exists or not.
    """
    try:
        imp.find_module(module)
        return True
    except ImportError:
        return False


def merge_configs(new_config, old_config):
    """
    Merge the values of old_config into the new_config.
    """
    new_config = new_config.copy()
    new_config.update(old_config)
    return new_config


def initialize_safeeyes():
    """
    Create the config file and style sheet in ~/.config/safeeyes directory.
    """
    logging.info('Copy the config files to ~/.config/safeeyes')

    style_dir_path = os.path.join(HOME_DIRECTORY, '.config/safeeyes/style')
    startup_dir_path = os.path.join(HOME_DIRECTORY, '.config/autostart')

    # Remove the ~/.config/safeeyes/safeeyes.json file
    delete(CONFIG_FILE_PATH)

    # Remove the startup file
    delete(os.path.join(HOME_DIRECTORY, os.path.join(
        startup_dir_path, 'safeeyes.desktop')))

    # Create the ~/.config/safeeyes/style directory
    mkdir(style_dir_path)
    mkdir(startup_dir_path)

    # Copy the safeeyes.json
    shutil.copy2(SYSTEM_CONFIG_FILE_PATH, CONFIG_FILE_PATH)

    # Copy the new startup file
    try:
        os.symlink("/usr/share/applications/safeeyes.desktop",
                   os.path.join(startup_dir_path, 'safeeyes.desktop'))
    except OSError:
        pass

    # Copy the new style sheet
    if not os.path.isfile(STYLE_SHEET_PATH):
        shutil.copy2(SYSTEM_STYLE_SHEET_PATH, STYLE_SHEET_PATH)


def reset_config():
    # Remove the ~/.config/safeeyes/safeeyes.json and safeeyes_style.css
    delete(CONFIG_FILE_PATH)
    delete(STYLE_SHEET_PATH)

    # Copy the safeeyes.json and safeeyes_style.css
    shutil.copy2(SYSTEM_CONFIG_FILE_PATH, CONFIG_FILE_PATH)
    shutil.copy2(SYSTEM_STYLE_SHEET_PATH, STYLE_SHEET_PATH)

def replace_style_sheet():
    """
    Replace the user style sheet by system style sheet.
    """
    delete(STYLE_SHEET_PATH)
    shutil.copy2(SYSTEM_STYLE_SHEET_PATH, STYLE_SHEET_PATH)


def intialize_logging(debug):
    """
    Initialize the logging framework using the Safe Eyes specific configurations.
    """
    # Configure logging.
    root_logger = logging.getLogger()
    log_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s]:[%(threadName)s] %(message)s')

    # Append the logs and overwrite once reached 1MB
    if debug:
        # Log to file
        file_handler = RotatingFileHandler(
            LOG_FILE_PATH, maxBytes=1024 * 1024, backupCount=5, encoding=None, delay=0)
        file_handler.setFormatter(log_formatter)
        # Log to console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)

        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    else:
        root_logger.propagate = False


def __open_plugin_config(plugins_dir, plugin_id):
    """
    Open the given plugin's configuration.
    """
    plugin_config_path = os.path.join(plugins_dir, plugin_id, 'config.json')
    plugin_module_path = os.path.join(plugins_dir, plugin_id, 'plugin.py')
    if not os.path.isfile(plugin_config_path) or not os.path.isfile(plugin_module_path):
        # Either the config.json or plugin.py is not available
        return None
    return load_json(plugin_config_path)


def __update_plugin_config(plugin, plugin_config, config):
    """
    Update the plugin configuration.
    """
    if plugin_config is None:
        config['plugins'].remove(plugin)
    else:
        if LooseVersion(plugin.get('version', '0.0.0')) != LooseVersion(plugin_config['meta']['version']):
            # Update the configuration
            plugin['version'] = plugin_config['meta']['version']
            setting_ids = []
            # Add the new settings
            for setting in plugin_config['settings']:
                setting_ids.append(setting['id'])
                if 'settings' not in plugin:
                    plugin['settings'] = {}
                if plugin['settings'].get(setting['id'], None) is None:
                    plugin['settings'][setting['id']] = setting['default']
            # Remove the removed ids
            keys_to_remove = []
            for key in plugin.get('settings', []):
                if key not in setting_ids:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del plugin['settings'][key]


def __add_plugin_config(plugin_id, plugin_config, safe_eyes_config):
    """
    """
    if plugin_config is None:
        return
    config = {}
    config['id'] = plugin_id
    config['enabled'] = False   # By default plugins are disabled
    config['version'] = plugin_config['meta']['version']
    if plugin_config['settings']:
        config['settings'] = {}
        for setting in plugin_config['settings']:
            config['settings'][setting['id']] = setting['default']
    safe_eyes_config['plugins'].append(config)


def merge_plugins(config):
    """
    Merge plugin configurations with Safe Eyes configuration.
    """
    system_plugins = None
    user_plugins = None

    # Load system plugins id
    if os.path.isdir(SYSTEM_PLUGINS_DIR):
        system_plugins = os.listdir(SYSTEM_PLUGINS_DIR)
    else:
        system_plugins = []

    # Load user plugins id
    if os.path.isdir(USER_PLUGINS_DIR):
        user_plugins = os.listdir(USER_PLUGINS_DIR)
    else:
        user_plugins = []

    # Create a list of existing plugins
    for plugin in config['plugins']:
        plugin_id = plugin['id']
        if plugin_id in system_plugins:
            plugin_config = __open_plugin_config(SYSTEM_PLUGINS_DIR, plugin_id)
            __update_plugin_config(plugin, plugin_config, config)
            system_plugins.remove(plugin_id)
        elif plugin_id in user_plugins:
            plugin_config = __open_plugin_config(USER_PLUGINS_DIR, plugin_id)
            __update_plugin_config(plugin, plugin_config, config)
            user_plugins.remove(plugin_id)
        else:
            config['plugins'].remove(plugin)

    # Add all system plugins
    for plugin_id in system_plugins:
        plugin_config = __open_plugin_config(SYSTEM_PLUGINS_DIR, plugin_id)
        __add_plugin_config(plugin_id, plugin_config, config)

    # Add all user plugins
    for plugin_id in user_plugins:
        plugin_config = __open_plugin_config(USER_PLUGINS_DIR, plugin_id)
        __add_plugin_config(plugin_id, plugin_config, config)


def open_session():
    """
    Open the last session.
    """
    logging.info('Reading the session file')

    session = load_json(SESSION_FILE_PATH)
    if session is None:
        session = {'plugin': {}}
    return session


def create_gtk_builder(glade_file):
    """
    Create a Gtk builder and load the glade file.
    """
    builder = Gtk.Builder()
    builder.set_translation_domain('safeeyes')
    builder.add_from_file(glade_file)
    # Tranlslate all sub components
    for obj in builder.get_objects():
        if (not isinstance(obj, Gtk.SeparatorMenuItem)) and hasattr(obj, "get_label"):
            label = obj.get_label()
            if label is not None:
                obj.set_label(_(label))
        elif hasattr(obj, "get_title"):
            title = obj.get_title()
            if title is not None:
                obj.set_title(_(title))
    return builder


def load_and_scale_image(path, width, height):
    if not os.path.isfile(path):
        return None
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
        filename=path,
        width=width,
        height=height,
        preserve_aspect_ratio=True)
    image = Gtk.Image.new_from_pixbuf(pixbuf)
    return image
