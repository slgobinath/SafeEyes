# Safe Eyes
Protect your eyes from eye strain using this continuous breaks reminder. A Free and Open Source Linux alternative for EyeLeo.

For more details: [SafeEyes Protects You From Eye Strain When Working On The Computer](http://www.webupd8.org/2016/10/safeeyes-protects-you-from-eye-strain.html)

## Installation

### Ubuntu:
1: Add the PPA: `sudo add-apt-repository ppa:slgobinath/safeeyes`

2: Download the package list: `sudo apt update`

3: Install Safe Eyes: `sudo apt install safeeyes`

4: Start Safe Eyes from start menu.

### Arch:
Install SafeEyes via [AUR](https://aur.archlinux.org/packages/safeeyes/). Credits to [Yamakaky](https://github.com/Yamakaky)

### Other Linux:

Manual installation is not tested in any systems. I will update this page as soon as I have tested in any other Linux distributions.

1: Install the dependencies:

   * Arch: `hicolor-icon-theme`, `libappindicator-gtk3`, `xorg-xprop`, `python2-xlib`, `python2-gobject`, `python2-dbus` and `mpg123`

   * Debian: `gir1.2-appindicator3-0.1`, `python-xlib`, `python-gobject`, `python-gi`, `python-dbus` and `mpg123`

   * Fedora 24: `libappindicator-gtk3`, `python-xlib`, `python-gobject`, `xorg-x11-utils`, `python-dbus` and `mpg123`

2: Download and extract [safeeyes.tar.gz](https://github.com/slgobinath/SafeEyes/releases/download/v1.1.0/safeeyes.tar.gz) into `/`: `sudo tar -xzvf safeeyes.tar.gz -C /`

If you have any issues in installing Safe Eyes, please report them [here](https://github.com/slgobinath/SafeEyes/issues)

4: Start Safe Eyes using this command:  `/opt/safeeyes/safeeyes`

Once started, Safe Eyes will copy the desktop file to `~/.config/autostart` and the configurations to `~/.config/safeeyes`. Therefore, from next time onwards, it should start with the system.

## Configuring Safe Eyes
Just install and forget; Safe Eyes will take care of your eyes. To customize the preferences, go to Settings from Safe Eyes tray icon.
You can change the look and feel of the break screen in `~/.config/safeeyes/style/safeeyes_style.css`.

## Uninstalling Safe Eyes
Use the following commands to uninstall SafeEyes from your system.
```
sudo apt remove safeeyes
rm -r ~/.config/safeeyes
rm ~/.config/autostart/safeeyes.desktop
```

## Features
- Short breaks with eye exercises
- Long breaks to change physical position and to warm up
- Strict break for those who are addicted to computer
- Highly customizable
- Do not disturb when working with fullscreen applications( Eg: Watching movies)
- Disable the keyboard during break
- Notifications before every break
- Multi-workspace support
- Multi-monitor support
- Elegant and customizable design
- Multi-language support

## Contributing
**Are you a user?**

Please test Safe Eyes on your system and report any issues [here](https://github.com/slgobinath/SafeEyes/issues)

**Are you a developer?**

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request

**Are you using a different Linux system?**

Please test Safe Eyes and create installers for your operating system

**Can you translate English to your mother tongue (or whatever the language)?**

Show your support by translating Safe Eyes to a new language or by improving the existing translations.

## Translating Safe Eyes
From version 1.1.0, Safe Eyes supports translation. Translation files for each langauges must be placed in `/opt/safeeyes/config/lang` directory. The language file name must follow [ISO 639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) language code standard. For example, the language file of English must be `en.json`. Follow these steps to translate Safe Eyes to your language.

1. Copy `/opt/safeeyes/config/lang/en.json` to `/opt/safeeyes/config/lang/<iso-639-1-language-code>.json`

2. Provide `language_name` in the language itself and `language_name_en` in English.

3. Translate other property values to the selected language.

4. Translate the comment in [safeeyes.desktop](https://github.com/slgobinath/SafeEyes/blob/master/safeeyes/share/applications/safeeyes.desktop) file.

**Note 1:** The `{}` used in property values will be replaced by runtime variables related to those commands. For example the `{}` in `Next break at {}` will be replaced by time at the runtime.

**Note 2:** Use Unicode when translating Safe Eyes.

**Note 3:** To change the language of Safe Eyes, change the `language` property in `~/.config/safeeyes/safeeyes.json` to the ISO 639-1 code of your language and restart the Safe Eyes.

For more details, have a look at existing language files: [lang](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang)

### Currently available translations
 * [Čeština](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/cz.json)
 * [English](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/en.json)
 * [Español](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/es.json)
 * [Français](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/fr.json)
 * [Magyar](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/hu.json)
 * [Português](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/pt.json)
 * [Slovenský](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/sk.json)
 * [தமிழ்](https://github.com/slgobinath/SafeEyes/tree/master/safeeyes/safeeyes/config/lang/ta.json)




## History
Version 1.1.1:
 * About dialog
 * UI control to select the language
 * Fixed bug in disable option after suspend

Version 1.1.0:
 * Multi-language support
 * Fixed bug in multi-screen support
 * Fixed bug in break screen transparency
 * Next break information in tray menu

Version 1.0.9:
 * Multi-screen support
 * Handling system suspend (Stop and restart during system suspend)

Version 1.0.8:
 * Bug fix for Ubuntu Mate

Version 1.0.7:
 * Removed python-apscheduler dependency
 * Installation directory is restructured
 * Bug fixes:
   * Supporting Ubuntu 16.10
   * Symlink for autostart instead of copying the desktop file

Version 1.0.6:
* Latest stable release

## Tested Environments
 * Ubuntu 14.04
 * Ubuntu 16.04
 * Ubuntu 16.10
 * Linux Mint 18
 * Ubuntu Mate 16.04

## License

GNU General Public License v3
