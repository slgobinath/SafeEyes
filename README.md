# Safe Eyes
Protect your eyes from eye strain using this continuous breaks reminder. A Free and Open Source Linux alternative for EyeLeo.

## Installation

### Ubuntu:
1: Add the PPA: `sudo add-apt-repository ppa:slgobinath/safeeyes`

2: Download the package list: `sudo apt update`

3: Install uget-chrome-wrapper: `sudo apt install safeeyes`

4: Start Safe Eyes from start menu.

### Arch:
1: Download the [safeeyes.tar.gz](https://github.com/slgobinath/SafeEyes/releases/download/v1.0.6/safeeyes.tar.gz)

2: Install Safe Eyes: `sudo pacman -U safeeyes.tar.gz`

If you have any issues in installing Safe Eyes, please report them [here](https://github.com/slgobinath/SafeEyes/issues)

### Other Linux:

Manual installation is not tested in any systems. I will update this page as soon as I have tested in any other Linux distributions.

1: Install the dependencies: `gir1.2-appindicator3-0.1` (`libappindicator3` in Arch), `python-xlib` (`python2-xlib` in Arch), `python-gobject` (`python2-gobject` in Arch), `xorg-xprop` in Arch

2: Download and extract [safeeyes.tar.gz](https://github.com/slgobinath/SafeEyes/releases/download/v1.0.6/safeeyes.tar.gz) into `/`: `sudo tar -xzvf safeeyes.tar.gz -C /`

The following files are deployed by SafeEyes
```
/usr/share/icons/hicolor/128x128/apps/
/usr/share/icons/hicolor/16x16/status/safeeyes_enabled.png
/usr/share/applications/safeeyes.desktop
/usr/share/icons/hicolor/32x32/
/usr/share/icons/hicolor/64x64/apps/safeeyes.png
/usr/share/icons/hicolor/24x24/status/
/usr/share/applications/
/usr/share/icons/hicolor/64x64/
/usr/share/icons/hicolor/
/usr/share/icons/hicolor/128x128/
/opt/
/usr/share/icons/hicolor/16x16/
/opt/safeeyes/safeeyes/glade/break_screen.glade
/usr/share/icons/hicolor/24x24/status/safeeyes_disabled.png
/opt/safeeyes/safeeyes/BreakScreen.py
/opt/safeeyes/safeeyes/safeeyes
/usr/share/icons/hicolor/48x48/
/usr/share/icons/hicolor/32x32/status/
/usr/share/icons/hicolor/48x48/status/safeeyes_disabled.png
/usr/share/icons/hicolor/48x48/status/
/usr/share/icons/hicolor/128x128/apps/safeeyes.png
/opt/safeeyes/safeeyes/SafeEyesCore.py
/usr/share/icons/hicolor/24x24/status/safeeyes_enabled.png
/usr/
/opt/safeeyes/safeeyes/config/
/opt/safeeyes/safeeyes/Notification.py
/usr/share/icons/hicolor/16x16/status/safeeyes_disabled.png
/usr/share/icons/hicolor/48x48/apps/
/opt/safeeyes/safeeyes/SettingsDialog.py
/opt/safeeyes/safeeyes/glade/
/usr/share/icons/hicolor/24x24/
/usr/share/icons/
/usr/share/icons/hicolor/32x32/apps/
/opt/safeeyes/safeeyes/glade/settings_dialog.glade
/opt/safeeyes/safeeyes/config/style/
/opt/safeeyes/safeeyes/TrayIcon.py
/usr/share/icons/hicolor/48x48/apps/safeeyes.png
/opt/safeeyes/
/opt/safeeyes/safeeyes.desktop
/opt/safeeyes/safeeyes/
/usr/share/icons/hicolor/64x64/apps/
/usr/share/icons/hicolor/16x16/status/
/usr/share/icons/hicolor/32x32/status/safeeyes_enabled.png
/opt/safeeyes/safeeyes/config/safeeyes.json
/usr/share/
/opt/safeeyes/safeeyes/config/style/safeeyes_style.css
/usr/share/icons/hicolor/48x48/status/safeeyes_enabled.png
/usr/share/icons/hicolor/32x32/status/safeeyes_disabled.png
/usr/share/icons/hicolor/32x32/apps/safeeyes.png
```
If you have any issues in installing Safe Eyes, please report them [here](https://github.com/slgobinath/SafeEyes/issues)

4: Start Safe Eyes using this command:  `/opt/safeeyes/safeeyes/safeeyes`

Once started, Safe Eyes will copy the desktop file to `~/.config/autostart` and the configurations to `~/.config/safeeyes`. Therefore, from next time onwards, it should start with the system.

## Usage
Just install and forget; Safe Eyes will take care of your eyes. To customize the preferences, go to Settings from Safe Eyes tray icon.
For advanced configuration, go to `~/.config/safeeyes folder`. There you can change the Skip button text in `safeeyes.json` and the look and feel of the break screen in `style/safeeyes_style.css`.

## Features
- Short breaks with eye exercises
- Long breaks to change physical position and to warm up
- Strict break for those who are addicted to computer
- Highly customizable
- Do not disturb when working with fullscreen applications( Eg: Watching movies)
- Disable the keyboard during break
- Notifications before every break
- Multi-workspace support
- Elegant and customizable design

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


## History

Version 1.0.6:
* Latest stable release


## License

GNU General Public License v3