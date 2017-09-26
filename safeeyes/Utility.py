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
import json
import locale
import logging
import os
import shutil
import subprocess
import threading
from distutils.version import LooseVersion

import babel.dates
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

gi.require_version('Gdk', '3.0')

BIN_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
HOME_DIRECTORY = os.path.expanduser('~')
config_directory = os.path.join(HOME_DIRECTORY, '.config/safeeyes')
config_file_path = os.path.join(config_directory, 'safeeyes.json')
style_sheet_path = os.path.join(config_directory, 'style/safeeyes_style.css')
system_config_file_path = os.path.join(BIN_DIRECTORY, "config/safeeyes.json")
system_style_sheet_path = os.path.join(BIN_DIRECTORY, "config/style/safeeyes_style.css")
log_file_path = os.path.join(config_directory, 'safeeyes.log')
SYSTEM_PLUGINS_DIR = os.path.join(BIN_DIRECTORY, 'plugins')
USER_PLUGINS_DIR = os.path.join(config_directory, 'plugins')
LOCALE_PATH = os.path.join(BIN_DIRECTORY, 'config/locale')

def get_resource_path(resource_name):
    """
    Return the user-defined resource if a system resource is overridden by the user.
    Otherwise, return the system resource. Return None if the specified resource does not exist.
    """
    if resource_name is None:
        return None
    resource_location = os.path.join(config_directory, 'resource', resource_name)
    if not os.path.isfile(resource_location):
        resource_location = os.path.join(BIN_DIRECTORY, 'resource', resource_name)
        if not os.path.isfile(resource_location):
            logging.error('Resource not found: ' + resource_name)
            resource_location = None

    return resource_location


def start_thread(target_function, **args):
    """
    Execute the function in a separate thread.
    """
    thread = threading.Thread(target=target_function, kwargs=args)
    thread.start()


def execute_main_thread(target_function, args=None):
    """
    Execute the given function in main thread.
    """
    if args:
        GLib.idle_add(lambda: target_function(args))
    else:
        GLib.idle_add(target_function)


def system_locale():
    """
    Return the system locale. If not available, return en_US.UTF-8.
    """
    try:
        locale.setlocale(locale.LC_ALL, '')
        sys_locale = locale.getlocale(locale.LC_TIME)[0]
        if not sys_locale:
            sys_locale = 'en_US.UTF-8'
        return sys_locale
    except BaseException:
        # Some systems does not return proper locale
        logging.error('Error in reading system locale')
        return 'en_US.UTF-8'


def format_time(time):
    """
    Format time based on the system time.
    """
    sys_locale = system_locale()
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


def load_plugins_config(plugins_dir):
    """
    Load all the plugins from the given directory.
    """
    configs = []
    for plugin_dir in os.listdir(plugins_dir):
        plugin_config_path = os.path.join(plugins_dir, plugin_dir, 'config.json')
        plugin_icon_path = os.path.join(plugins_dir, plugin_dir, 'icon.png')
        plugin_module_path = os.path.join(plugins_dir, plugin_dir, 'plugin.py')
        if not os.path.isfile(plugin_module_path):
            return
        icon = None
        if os.path.isfile(plugin_icon_path):
            icon = plugin_icon_path
        else:
            icon = get_resource_path('ic_plugin.png')
        if os.path.isfile(plugin_config_path):
            with open(plugin_config_path) as config_file:
                config = json.load(config_file)
                config['id'] = plugin_dir
                config['icon'] = icon
                config['module_path'] = plugin_module_path
                configs.append(config)
    return configs

def load_plugins_config_gobi(safeeyes_config):
    """
    Load all the plugins from the given directory.
    """
    configs = []
    for plugin in safeeyes_config['plugins']:
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
        if os.path.isfile(plugin_config_path):
            with open(plugin_config_path) as config_file:
                config = json.load(config_file)
                config['id'] = plugin['id']
                config['icon'] = icon
                config['enabled'] = plugin['enabled']
                for setting in config['settings']:
                    setting['safeeyes_config'] = plugin['settings']
                configs.append(config)
    return configs

def merge_plugins_config(safeeyes_config, plugins_dir):
    """
    Add the settings related to plugins to the Safe Eyes configuration.
    """
    if not os.path.isdir(plugins_dir):
        return
    existing_plugins = []
    # Create a list of existing plugins
    for plugin in safeeyes_config['plugins']:
        existing_plugins.append(plugin['id'])

    for plugin_dir in os.listdir(plugins_dir):
        if plugin_dir in existing_plugins:
            # Already added to the Safe Eyes config
            continue
        plugin_config_path = os.path.join(plugins_dir, plugin_dir, 'config.json')
        plugin_module_path = os.path.join(plugins_dir, plugin_dir, 'plugin.py')
        if not os.path.isfile(plugin_config_path) or not os.path.isfile(plugin_module_path):
            # Either the config.json or plugin.py is not available
            continue
        config = {}
        config['id'] = plugin_dir   # Plugin directory name is the id
        config['enabled'] = False   # By default plugins are disabled
        with open(plugin_config_path) as config_file:
            plugin_config = json.load(config_file)
            if plugin_config['settings']:
                config['settings'] = {}
                for setting in plugin_config['settings']:
                    config['settings'][setting['id']] = setting['default']
        safeeyes_config['plugins'].append(config)

def desktop_environment():
    """
    Detect the desktop environment.
    """
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
    return env


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
            logging.error('Error in executing the commad' + str(command))


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


def __initialize_safeeyes():
    """
    Create the config file and style sheet in ~/.config/safeeyes directory.
    """
    logging.info('Copy the config files to ~/.config/safeeyes')

    style_dir_path = os.path.join(HOME_DIRECTORY, '.config/safeeyes/style')
    startup_dir_path = os.path.join(HOME_DIRECTORY, '.config/autostart')

    # Remove the ~/.config/safeeyes directory
    try:
        os.remove(os.path.join(config_directory, 'safeeyes.json'))
    except OSError:
        pass

    # Remove the startup file
    try:
        os.remove(os.path.join(HOME_DIRECTORY, os.path.join(startup_dir_path, 'safeeyes.desktop')))
    except OSError:
        pass

    # Create the ~/.config/safeeyes/style directory
    mkdir(style_dir_path)
    mkdir(startup_dir_path)

    # Copy the safeeyes.json
    shutil.copy2(system_config_file_path, config_file_path)

    # Copy the new startup file
    try:
        os.symlink("/usr/share/applications/safeeyes.desktop", os.path.join(startup_dir_path, 'safeeyes.desktop'))
    except OSError:
        pass

    # Copy the new style sheet
    if not os.path.isfile(style_sheet_path):
        shutil.copy2(system_style_sheet_path, style_sheet_path)


def intialize_logging():
    """
    Initialize the logging framework using the Safe Eyes specific configurations.
    """
    # Create the directory to store log file if not exist
    if not os.path.exists(config_directory):
        try:
            os.makedirs(config_directory)
        except OSError:
            pass

    # Configure logging.
    log_formatter = logging.Formatter('%(asctime)s [%(levelname)s]:[%(threadName)s] %(message)s')

    # Apped the logs and overwrite once reached 5MB
    handler = logging.StreamHandler()  # RotatingFileHandler(log_file_path, mode='a', maxBytes=5 * 1024 * 1024, backupCount=2, encoding=None, delay=0)
    handler.setFormatter(log_formatter)
    handler.setLevel(logging.DEBUG)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)


def read_config():
    """
    Read the configuration from the config directory.
    If does not exist or outdated by major version, copy the system config and
    startup script to user directory.
    If the user config is outdated by minor version, update the config by the new values.
    """
    logging.info('Reading the configuration file')

    if not os.path.isfile(config_file_path):
        logging.info('Safe Eyes configuration file not found')
        __initialize_safeeyes()

    # Read the configurations
    with open(config_file_path) as config_file:
        user_config = json.load(config_file)

    with open(system_config_file_path) as config_file:
        system_config = json.load(config_file)

    user_config_version = str(user_config['meta']['config_version'])
    system_config_version = str(system_config['meta']['config_version'])

    if LooseVersion(user_config_version) < LooseVersion(system_config_version):
        # Outdated user config
        logging.info('Update the old config version %s with new config version %s', user_config_version, system_config_version)
        user_config_major_version = user_config_version.split('.')[0]
        system_config_major_version = system_config_version.split('.')[0]

        if LooseVersion(user_config_major_version) < LooseVersion(system_config_major_version):
            # Major version change
            __initialize_safeeyes()
            # Update the user_config
            user_config = system_config
        else:
            # Minor version change
            new_config = system_config.copy()
            new_config.update(user_config)
            # Update the version
            new_config['meta']['config_version'] = system_config_version

            # Write the configuration to file
            with open(config_file_path, 'w') as config_file:
                json.dump(new_config, config_file, indent=4, sort_keys=True)

            # Update the user_config
            user_config = new_config

    merge_plugins_config(user_config, SYSTEM_PLUGINS_DIR)
    merge_plugins_config(user_config, USER_PLUGINS_DIR)
    with open(config_file_path, 'w') as config_file:
        json.dump(user_config, config_file, indent=4, sort_keys=True)

    return user_config


def create_gtk_builder(glade_file):
    """
    Create a Gtk builder and load the glade file.
    """
    builder = Gtk.Builder()
    builder.set_translation_domain('safeeyes')
    builder.add_from_file(glade_file)
    return builder
