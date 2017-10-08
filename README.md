# Safe Eyes

[![GitHub version](https://badge.fury.io/gh/slgobinath%2FSafeEyes.svg)](https://badge.fury.io/gh/slgobinath%2FSafeEyes)
[![PyPI version](https://badge.fury.io/py/safeeyes.svg)](https://badge.fury.io/py/safeeyes)
[![Translation status](https://hosted.weblate.org/widgets/safe-eyes/-/translations/svg-badge.svg)](https://hosted.weblate.org/engage/safe-eyes/?utm_source=widget)


Protect your eyes from eye strain using this simple and beautiful, yet extensible break reminder. A Free and Open Source Linux alternative to EyeLeo.

Visit to the official site: http://slgobinath.github.io/SafeEyes/ for more details.

## Safe Eyes command-line arguements
```
usage: safeeyes [-h] [-a | -d | -e | -q | -s | -t] [--debug] [--version]

Safe Eyes protects your eyes from eye strain (asthenopia) by reminding you to
take breaks while you're working long hours at the computer.

optional arguments:
  -h, --help        show this help message and exit
  -a, --about       show the about dialog
  -d, --disable     disable the currently running safeeyes instance
  -e, --enable      enable the currently running safeeyes instance
  -q, --quit        quit the running safeeyes instance and exit
  -s, --settings    show the settings dialog
  -t, --take-break  take a break now
  --debug           start safeeyes in debug mode
  --version         show program's version number and exit
```

## Installation guide
Safe Eyes is available in Ubuntu PPA, Arch AUR and Python PyPI. You can choose any installation source and install on any Linux system with Python 3. To see how to install Safe Eyes, visit [Getting Started](http://slgobinath.github.io/SafeEyes/#introduction)

### Compile from source
Ensure to meet the following dependencies when compiling from source:

- gir1.2-appindicator3-0.1
- gir1.2-notify-0.7
- libappindicator-gtk3
- python3-psutil
- xprintidle (optional)

## Features
 - Remind you to take breaks
 - Disable keyboard during breaks
 - Notification before and after breaks
 - Smart pause if system is idle
 - Customizable using plug-ins
 - Multi-screen support
 - Customizable user interface
 - RPC API to control externally
 - Command-line arguments to control the running instance

## Writing Safe Eyes plug-in
A plugin is a combination of two files: `plugin.py` and `config.json`. These two files must be placed in a directory: `~/.config/safeeyes/plugins/<plugin-id>`. Optionally a plugin also can have an image file `icon.png` which is used to represent the plugin in the Settings dialog.

For example, a Weather plugin may have the following file structure:
```
~
└── .config
    └── safeeyes
        └── plugins
            └── weather
                ├── config.json
                ├── icon.png
                └── plugin.py
```

The `icon.png` must be `24x24` pixels size. If `icon.png` is not available, the default gear icon <img src="https://github.com/slgobinath/SafeEyes/raw/master/safeeyes/resource/ic_plugin.png" width="16" height="16"/> will be shown in the Settings dialog.

A sample `config.json` is provided below:
```json
{
    "meta": {
        "name": "Weather",
        "description": "Show the current weather on break screen",
        "version": "0.0.1"
    },
    "dependencies": {
        "python_modules": ["pyowm"],
        "shell_commands": [],
        "operating_systems": [],
        "desktop_environments": [],
        "resources": []
    },
    "settings": [
        {
            "id": "api",
            "label": "OpenWeatherMap API Key",
            "type": "TEXT",
            "default": ""
        },
        {
            "id": "location",
            "label": "Location",
            "type": "TEXT",
            "default": ""
        }
    ],
    "break_override_allowed": true
}
```

The `meta` properties must provide the name of the plugin, a short description and the current version of the plugin.

The `dependencies` property defines various dependency constraints of the plugin. The dependencies can be Python modules, commandline tools, desktop environments or Safe Eyes resources. The `operating_systems` property is reserved for operating system dependency but not checked for at the moment.
If a dependency is not available, the Safe Eyes will not load the plugin. The Settings dialog will show a warning symbol <img src="https://github.com/slgobinath/SafeEyes/raw/master/safeeyes/resource/ic_warning.png" width="16" height="16"> and a message to install/check the missing dependencies. Dependencies are checked in the order of *Desktop Environment*, *Python Modules*, *Commandline Tools* and *Resources*. If a dependency is not available, Safe Eyes will stop looking for the rest.

The configurations related to the plugin must be defined in `settings`. Each setting must have an `id`, `label`, `type` and a default value matching the `type`. Safe Eyes 2.0.0 supports only the following types: `INT`, `TEXT` and `BOOL`. According to the types, Settings dialog will show a *Spin*, *Text Field* or *Switch Button* as the input field.

The optional `break_override_allowed` property lets users to override the status of plugins by enable or disable based on break.

The `plugin.py` can have one or more of the following functions:

```python
def on_init(context, safeeyes_config, plugin_config):
    """
    Executes after loading the plugin for the first time and after every changes in configuration.
    """
    pass

def on_start():
    """
    Executes when Safe Eyes is enabled.
    """
    pass

def on_stop():
    """
    Executes when Safe Eyes is disabled.
    """
    pass

def enable():
    """
    Executes after plugin.py is loaded as a module.
    """
    pass

def disable():
    """
    Executes after disabling the plugin at the runtime.
    """
    pass

def update_next_break(date_time):
    """
    Update the next break time.
    """
    pass

def on_pre_break(break_obj):
    """
    Executes before on_start_break break.
    """
    pass

def on_start_break(break_obj):
    """
    Executes when starting a break.
    """
    pass

def on_countdown(countdown, seconds):
    """
    Keep track of seconds passed from the beginning of break.
    """
    pass

def on_stop_break():
    """
    Executes at the end of breaks.
    """
    pass

def on_exit():
    """
    Executes before Safe Eyes exits
    """
    pass

def get_widget_title(break_obj):
    """
    Return the widget title.
    """
    return 'Widget Title'

def get_widget_content(break_obj):
    """
    Return the widget content.
    """
    return 'Widget Content'
```

All the above functions are optional and it is the developer's choice to choose the functions to implement. The `pre_break` and  `start_break` methods can return `True` if they want to skip the specific break. If a plugin skips the break by returning `True`, the corresponding lifecycle method will not be invoked from the upcoming plugins. The execution order of plugins is not predefined so the plugins should not make any assumption about other plugins.

Plugins willing to show an entry in the break screen must implement both `get_widget_title` and `get_widget_content`. They should return a single line string as the output. If either the title or content is an empty string, the message will not be displayed in the break screen. It is added as an option to skip selective breaks depending on the domain.

A sample `plugin.py` is shown below to disaplay the current weather information:
```python
import logging
import pyowm

api = None
location = None
owm = None
weather_details = None

def init(ctx, safeeyes_config, plugin_config):
    """
    Initialize the plugin.
    """
    logging.debug('Initialize Weather plugin')
    global api
    global location
    global owm
    api = plugin_config['api']
    location = plugin_config['location']
    if api != "" and location != "":
        owm = pyowm.OWM(api)
    

def get_widget_title(break_obj):
    """
    Return the widget title.
    """
    logging.debug('Get the weather information')
    global weather_details
    if owm:
        try:
            observation = owm.weather_at_place(location)
            weather = observation.get_weather()
            temp = weather.get_temperature('celsius').get('temp')
            humidity = weather.get_humidity()
            wind_speed = weather.get_wind().get('speed')
            weather_details = 'Temperature: %s℃\t\tHumidity: %s\tWind Speed: %s' % (temp, humidity, wind_speed)
        except BaseException:
            # Can be a network error
            weather_details = None
    if weather_details:
        return 'Weather'

def get_widget_content(break_obj):
    """
    Return the weather details.
    """
    return weather_details
```
To get more ideas, go through the existing plugins available in [system plugins](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/plugins).

## License

GNU General Public License v3
