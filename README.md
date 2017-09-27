# Safe Eyes
Protect your eyes from eye strain using this simple and beautiful, yet extensible break reminder. A Free and Open Source Linux alternative to EyeLeo.

Visit to the official site: http://slgobinath.github.io/SafeEyes/ for more details.

## Installation guide
Safe Eyes is available in Ubuntu PPA, Arch AUR and Python PyPI. You can choose any installation source and install on any Linux system with Python 3. To see how to install Safe Eyes, visit [Getting Started](http://slgobinath.github.io/SafeEyes/#introduction)

### Compile from source
Ensure to meet the following dependencies when compiling from source:

- gir1.2-appindicator3-0.1
- gir1.2-notify-0.7
- libappindicator-gtk3
- python3-psutil
- xprintidle (optional)

## Writing Plug-in for Safe Eyes
A plugin is a combination of two files: `plugin.py` and `config.json`. These two files must be placed in a directory: `~/.config/safeeyes/plugins/<plugin-id>`. Optionally a plugin also can have an image file `icon.png` which is used to represent the plugin in the Settings dialog.

For example, a Weather plugin may have the following file structure:
```
~
└── .config
    └── safeeyes
        └── weather
            ├── config.json
            ├── icon.png
            └── plugin.py
```

The icon.png must be `24x24` pixels size. If `icon.png` is not available, the default gear icon <img src="https://github.com/slgobinath/SafeEyes/raw/safeeyes-2.0.0/safeeyes/resource/ic_plugin.png" width="16" height="16"/> will be shown in the Settings dialog.

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
        "desktop_environments": []
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
    "resources": [],
    "break_override_allowed": true
}
```

The `meta` properties must provide the name of the plugin, a short description and the current version of the plugin.

The `dependencies` property defines various dependency constraints of the plugin. The dependencies can be Python modules, commandline tools or desktop environments. The `operating_systems` property is reserved for operating system dependency but not checked for at the moment.

The configurations related to the plugin must be defined in `settings`. Each setting must have an `id`, `label`, `type` and a default value matching the `type`. Safe Eyes 2.0.0 supports only the following types: `INT`, `TEXT` and `BOOL`. According to the types, Settings dialog will show a *Spin*, *Text Field* or *Switch Button* as the input field.
## License

GNU General Public License v3
