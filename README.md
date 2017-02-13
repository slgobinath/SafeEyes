# Safe Eyes
Protect your eyes from eye strain using this continuous breaks reminder. A Free and Open Source Linux alternative for EyeLeo.

For more details: [SafeEyes Protects You From Eye Strain When Working On The Computer](http://www.webupd8.org/2016/10/safeeyes-protects-you-from-eye-strain.html)

## INSTALLATION

### Ubuntu:
1: Add the PPA: `sudo add-apt-repository ppa:slgobinath/safeeyes`

2: Download the package list: `sudo apt update`

3: Install Safe Eyes: `sudo apt install safeeyes`

4: Start Safe Eyes from start menu.

### Arch:
Install SafeEyes via [AUR](https://aur.archlinux.org/packages/safeeyes/). Credits to [Yamakaky](https://github.com/Yamakaky)

### Other Linux:
1: Install the dependencies:

   * Arch: `hicolor-icon-theme`, `libappindicator-gtk3`, `xorg-xprop`, `python2-xlib`, `python2-gobject`, `python2-dbus`, `python2-babel`, `xprintidle` and `mpg123`

   * Debian: `gir1.2-appindicator3-0.1`, `python-xlib`, `python-gobject`, `python-gi`, `python-dbus`, `gir1.2-notify-0.7`, `python-gtk2`, `python-babel`, `xprintidle` and `mpg123`

   * Fedora 24: `libappindicator-gtk3`, `python-xlib`, `python-gobject`, `xorg-x11-utils`, `python-dbus`, `python-babel`, `xprintidle` and `mpg123`

2: Download and extract [safeeyes.tar.gz](https://github.com/slgobinath/SafeEyes/releases/download/v1.1.5/safeeyes.tar.gz) into `/`: `sudo tar -xzvf safeeyes.tar.gz -C /`

4: Start Safe Eyes using this command:  `/opt/safeeyes/safeeyes`

Once started, Safe Eyes will copy the desktop file to `~/.config/autostart` and the configurations to `~/.config/safeeyes`. Therefore, from next time onwards, it should start with the system.

## UNINSTALLING SAFE EYES
Use the following commands to uninstall SafeEyes from your system.
```
sudo apt remove safeeyes
rm -r ~/.config/safeeyes
rm ~/.config/autostart/safeeyes.desktop
```

## FEATURES

General Features:

- Short breaks with eye exercises
- Long breaks to change physical position and to warm up
- Disable the keyboard during break
- Notifications before every break
- Do not disturb when working with fullscreen applications( Eg: Watching movies)
- Smart pause and resume based on system idle time
- Multi-monitor support
- Elegant and customizable design
- Multi-language support
- Highly customizable

Optional Features:

- Strict break for those who are addicted to computer
- Skip or take break based on active windows (Regardless of fullscreen-mode)
- Customize individual break time
- Audible alert at the end of break
- Turn on/off audible alert for individual breaks
- Customize disable time period

## CONFIGURING SAFE EYES
Just install and forget; Safe Eyes will take care of your eyes. To customize the basic preferences, go to Settings from Safe Eyes tray icon. If you need advanced features, you can manually edit the `~/.config/safeeyes/safeeyes.json` for the following requirements:

**NOTE:** Still the advanced customization is not available in any released versions. Please wait until the next version :-)

### Override individual break time

Add the optional `time` property to the desired break with the required time parameter. The `short_breaks` temporal unit is measured in seconds and the `long_breaks` temporal unit is measured in minutes.
For example, to extend the break time of `short_break_close_eyes` to 30 seconds and the `long_break_walk` to 5 minutes, modify the configuration file as given below.

```
...
"short_breaks": [
    {
        "name": "short_break_close_eyes",
        "time": 30
    },
    {
        "name": "short_break_roll_eyes"
    },
    ...
],
...
"long_breaks": [
    {
        "name": "long_break_walk",
        "time": 5
    },
    {
        "name": "long_break_lean_back"
    }
]
...
```

### Override audible alert after each break

Add the optional `audible_alert` property to the desired break with the required true/false parameter.
For example, to disable audible alert for all breaks except the `short_break_close_eyes`, modify the configuration file as given below.

```
...
"audible_alert": false,
...
"short_breaks": [
    {
        "name": "short_break_close_eyes",
        "audible_alert": true
    },
    {
        "name": "short_break_roll_eyes"
    },
    ...
]
...
```

### Customize disable time period

The default disable dor a given time options provide 30 minutes, 1 hour, 2 hours and 3 hours only. If you want to customize them or if you want to add/remove time based disable option, you can configure them in the `safeeyes.json` file.
To add an additional `Disable for 45 minutes`, modify the configuration as shown below.

```
...
"disable_options": [
    {
        "label": "for_x_minutes",
        "time": 30,
        "unit": "minute"
    },
    {
        "label": "for_x_minutes",
        "time": 45,
        "unit": "minute"
    },
    {
        "label": "for_x_hour",
        "time": 1,
        "unit": "hour"
    }
    ...
]
...
```

**NOTE:** The `unit` can be one of these case-insensitive constants: `second`, `seconds`, `minute`, `minutes`, `hour`, `hours`

### Skip or Take breaks based on the active window regardless of the full-screen mode

By default, Safe Eyes does not show the break screen if the current window is in fullscreen mode. However, you can override this feature by specifying the window-class of your interested applications.

For example, to take the break if your current window is Google Chrome regardless of the fullscreen mode, add `google-chrome` to `take_break` as given below:

```
...
"active_window_class": {
    "skip_break": [],
    "take_break": [`google-chrome`]
},
...
```

Similarly, you can skip the break even if your current application is in normal window state. For example, if you do not want to take a break while VLC player is in focus, add `vlc` to `skip_break` as shown here:
```
...
"active_window_class": {
    "skip_break": [`vlc`],
    "take_break": [`google-chrome`]
},
...
```

**NOTE:** The names `vlc` and `google-chrome` are not the application names but their window classes. Inorder to get the window class of an application, enter the following command in your terminal and click on the desired application. In the printed `WM_CLASS`, choose the second one.
```
xprop WM_CLASS
```
Some more sample window class names:
- Mozilla Firefox: `firefox`
- Sublime Text: `sublime_text`
- Gnome Terminal: `gnome-terminal`
- LibreOffice Writer: `libreoffice-writer`

### Change the look and feel of the break screen

You can change the look and feel of the break screen in `~/.config/safeeyes/style/safeeyes_style.css`.


## CONTRIBUTING

**Are you a developer?**

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request

**Are you using a different Linux system?**

Please test Safe Eyes and create installers for your operating system

**Found a bug?**

Please report them [here](https://github.com/slgobinath/SafeEyes/issues)

**Can you translate English to your mother tongue (or whatever the language)?**

Show your support by translating Safe Eyes to a new language or by improving the existing translations.

**How else can you show your support?**

 - Vote for Safe Eyes in [alternativeto.net](http://alternativeto.net/software/eyeleo/?platform=linux).
 - Suggest any improvements.
 - Share with your friends.

## TRANSLATING SAFE EYES
From version 1.1.0, Safe Eyes supports translation. Translation files for each langauges must be placed in `/opt/safeeyes/config/lang` directory. The language file name must follow [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) language code standard. For example, the language file of English must be `en.json`. Follow these steps to translate Safe Eyes to your language.

1. Copy `/opt/safeeyes/config/lang/en.json` to `/opt/safeeyes/config/lang/<iso-639-1-language-code>.json` (Please compare the `en.json` with the [online version](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/en.json) before sending PR, because there can be new changes made to the language files)

2. Provide `language_name` in the language itself and `language_name_en` in English.

3. Translate other property values to the selected language.

4. Translate the comment in [safeeyes.desktop](https://github.com/slgobinath/SafeEyes/blob/master/safeeyes/share/applications/safeeyes.desktop) file.

**Note 1:** The `{}` used in property values will be replaced by runtime variables related to those commands. For example the `{}` in `Next break at {}` will be replaced by time at the runtime.

**Note 2:** Use Unicode when translating Safe Eyes.

**Note 3:** To change the language of Safe Eyes, select the language name from the combo-box in the Settings dialog.

For more details, have a look at existing language files: [lang](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang)

### Currently available translations
 * [Čeština](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/cz.json)
 * [Deutsch](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/de.json)
 * [English](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/en.json)
 * [Español](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/es.json)
 * [Français](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/fr.json)
 * [Magyar](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/hu.json)
 * [Português](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/pt.json)
 * [Русский](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/ru.json)
 * [Slovenský](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/sk.json)
 * [தமிழ்](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/ta.json)
 * [Türkçe](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/tr.json)


## TESTED ENVIRONMENTS

Core functionalities of Safe Eyes are tested by the developer in the follwing environments:

 * Ubuntu 14.04
 * Ubuntu 16.04
 * Ubuntu 16.10
 * Linux Mint 18
 * Ubuntu Mate 16.04
 * Kubuntu 16.10

## LICENSE

GNU General Public License v3
