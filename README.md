# Safe Eyes
Protect your eyes from eye strain using this continuous breaks reminder. A Free and Open Source Linux alternative for EyeLeo.

Read more about Safe Eyes on [WEB UPD8](http://www.webupd8.org/):

1. [SafeEyes Protects You From Eye Strain When Working On The Computer](http://www.webupd8.org/2016/10/safeeyes-protects-you-from-eye-strain.html)
2. [Computer Eye Strain Prevention App 'Safe Eyes' Sees New Release](http://www.webupd8.org/2017/02/computer-eye-strain-prevention-app.html)

## INSTALLATION

### Ubuntu:
1: Add the PPA: `sudo add-apt-repository ppa:slgobinath/safeeyes`

2: Download the package list: `sudo apt update`

3: Install Safe Eyes: `sudo apt install safeeyes`

4: Start Safe Eyes from start menu.

### Arch:
Install SafeEyes via [AUR](https://aur.archlinux.org/packages/safeeyes/). Credits to [Yamakaky](https://github.com/Yamakaky)

You can use either of these AUR helpers:
```
packer -S safeeyes
```
OR
```
yaourt -S safeeyes
```

### Other Linux:
1: Install the dependencies:

   * Arch: `hicolor-icon-theme`, `libappindicator-gtk3`, `xorg-xprop`, `python2-xlib`, `python2-gobject`, `python2-dbus`, `python2-babel`, `xprintidle`, `mpg123` (From next version onwards: `python2-psutil` and `python2-pyaudio`)

   * Debian: `gir1.2-appindicator3-0.1`, `python-xlib`, `python-gobject`, `python-gi`, `python-dbus`, `gir1.2-notify-0.7`, `python-gtk2`, `python-babel`, `xprintidle`, `mpg123`, (From next version onwards: `python-psutil`  and `python-pyaudio`)

   * Fedora 24: `libappindicator-gtk3`, `python-xlib`, `python-gobject`, `xorg-x11-utils`, `python-dbus`, `python-babel`, `xprintidle`, `mpg123`, (From next version onwards: `python-psutil`  and `python-pyaudio`)

2: Download and extract [safeeyes.tar.gz](https://github.com/slgobinath/SafeEyes/releases/download/v1.1.8/safeeyes.tar.gz) into `/`: `sudo tar -xzvf safeeyes.tar.gz -C /`

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

### Adding custom exercises

We're not going to pretend that the built-in list of exercises will be enough for everybody.  So you can add your own!  First, modify the `custom_exercises` property (which is an empty object by default) like so:

```
...
"custom_exercises": {
    "deep_breath": "Take a deep breath",
    "pushups": "Do ten push-ups",
    "other": "Other small things you should do on a regular basis"
}
...
```

Then add them to the `short_breaks` or `long_breaks` property as you see fit:

```
...
"short_breaks": [
    ...
    {
        "name": "deep_breath"
    },
    ...
],
...
"long_breaks": [
    ...
    {
        "name": "pushups"
    },
    ...
],
...
```

### Override individual break time

Add the optional `time` property to the desired break with the required time parameter. The time unit is seconds.
For example, to extend the break time of `short_break_close_eyes` to 30 seconds and the `long_break_walk` to 5 minutes (300 seconds), modify the configuration file as given below.

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
        "time": 300
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
    "take_break": ["google-chrome"]
},
...
```

Similarly, you can skip the break even if your current application is in normal window state. For example, if you do not want to take a break while VLC player is in focus, add `vlc` to `skip_break` as shown here:
```
...
"active_window_class": {
    "skip_break": ["vlc"],
    "take_break": ["google-chrome"]
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

### Change the break image
Create a new directory resource in `~/.config/safeeyes`
```
mkdir ~/.config/safeeyes/resource
```
Place your desired image in the resource folder. (Recommended size: `128x128 px`).
If the file name is same as the image name defined in `~/.config/safeeyes/safeeyes.json`, that is it. Safe Eyes will load the image from `~/.config/safeeyes/resource` directory.
If the file name is different, edit the image name in `~/.config/safeeyes/safeeyes.json`:

```
...
"short_breaks": [
    {
        "name": "short_break_close_eyes",
        "image": "image_file_name.png"
    }
    ...
]
...
```

### Change the audible alert sound
Create a new directory resource in `~/.config/safeeyes`
```
mkdir ~/.config/safeeyes/resource
```
Place the new `alert.wav` file in the `~/.config/safeeyes/resource` directory.

### Write Safe Eyes plugins
This section uses a simple todo list plugin as an example.

Create a new directory plugins in `~/.config/safeeyes`
```
mkdir ~/.config/safeeyes/plugins
```
Create a new file todo.py in `~/.config/safeeyes/plugins` with the following content

```
"""
Safe Eyes todo plugin
"""

def start(context):
	"""
	Do not return anything here.
	Use this function if you want to do anything on startup.
	"""
	pass

def pre_notification(context):
	"""
	Do not return anything here.
	Use this function if you want to do anything before ntification.
	"""
	pass

def pre_break(context):
	"""
	Use this function if you want to do anything on before the break.
	Optionally you can return a Pango markup content to be displayed on the break screen.
	For more details about Pango: https://developer.gnome.org/pygtk/stable/pango-markup-language.html
	NOTE: This function should return the result within a second
	"""
	todo_list = """★ Call alice
★ Upvote Safe Eyes in alternative.to"""
	return "<span color='white'>" + todo_list + "</span>"

def post_break(context):
	# Do nothing after the notification
	pass

def exit(context):
	"""
	Do not return anything here.
	Use this function if you want to do anything on exit.
	"""
	pass
```

Add the plugin in `~/.config/safeeyes/safeeyes.json`
```
    ...
    "plugins": [
        {
            "name": "todo",
            "location": "right"
        }
    ]
    ...
```
Here the location can be either `left` or `right` which defines the location on the break screen.


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

1. Copy `/opt/safeeyes/config/lang/en.json` to `/opt/safeeyes/config/lang/<iso-639-1-language-code>.json` (Please compare the `en.json` with the [online version](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/en.json) before sending PR, because there can be new changes made to the language files)

2. Provide `language_name` in the language itself and `language_name_en` in English.

3. Translate other property values to the selected language.

4. Translate the comment in [safeeyes.desktop](https://github.com/slgobinath/SafeEyes/blob/master/share/applications/safeeyes.desktop) file.

**Note 1:** The `{}` used in property values will be replaced by runtime variables related to those commands. For example the `{}` in `Next break at {}` will be replaced by time at the runtime.

**Note 2:** Use Unicode when translating Safe Eyes.

**Note 3:** To change the language of Safe Eyes, select the language name from the combo-box in the Settings dialog.

For more details, have a look at existing language files: [lang](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang)

### Currently available translations
 * [Čeština](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/cs.json)
 * [Deutsch](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/de.json)
 * [English](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/en.json)
 * [Español](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/es.json)
 * [Français](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/fr.json)
 * [ქართული](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/ge.json)
 * [हिंदी](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/hi.json)
 * [Magyar](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/hu.json)
 * [Bahasa Indonesia](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/id.json)
 * [Português](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/pt.json)
 * [Русский](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/ru.json)
 * [Slovenský](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/sk.json)
 * [தமிழ்](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/ta.json)
 * [Türkçe](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/config/lang/tr.json)


## TESTED ENVIRONMENTS

Core functionalities of Safe Eyes are tested by the developer in the follwing environments:

 * Ubuntu 14.04
 * Ubuntu 16.04
 * Ubuntu 16.10
 * Linux Mint 18
 * Ubuntu Mate 16.04
 * Kubuntu 16.10
 * Antergos 2017

## LICENSE

GNU General Public License v3
