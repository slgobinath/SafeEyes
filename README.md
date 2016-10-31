# Safe Eyes
Protect your eyes from eye strain using this continuous breaks reminder. A Free and Open Source Linux alternative for EyeLeo.

For more details: [SafeEyes Protects You From Eye Strain When Working On The Computer](http://www.webupd8.org/2016/10/safeeyes-protects-you-from-eye-strain.html)

## Installation

### Ubuntu:
1: Add the PPA: `sudo add-apt-repository ppa:slgobinath/safeeyes`

2: Download the package list: `sudo apt update`

3: Install uget-chrome-wrapper: `sudo apt install safeeyes`

4: Start Safe Eyes from start menu.

### Arch:
Install SafeEyes via [AUR](https://aur.archlinux.org/packages/safeeyes/). Credits to [Yamakaky](https://github.com/Yamakaky)

### Other Linux:

Manual installation is not tested in any systems. I will update this page as soon as I have tested in any other Linux distributions.

1: Install the dependencies:

   * Arch: `hicolor-icon-theme`, `libappindicator-gtk3`, `xorg-xprop`, `python2-xlib`, `python2-gobject` and `python2-dbus`

   * Debian: `gir1.2-appindicator3-0.1`, `python-xlib`, `python-gobject`, `python-gi` and `python-dbus`

   * Fedora 24: `libappindicator-gtk3`, `python-xlib`, `python-gobject`, `xorg-x11-utils` and `python-dbus`

2: Download and extract [safeeyes.tar.gz](https://github.com/slgobinath/SafeEyes/releases/download/v1.0.9/safeeyes.tar.gz) into `/`: `sudo tar -xzvf safeeyes.tar.gz -C /`

The following files are deployed by SafeEyes
```
opt/
opt/safeeyes/
opt/safeeyes/BreakScreen.py
opt/safeeyes/config/
opt/safeeyes/config/safeeyes.json
opt/safeeyes/config/style/
opt/safeeyes/config/style/safeeyes_style.css
opt/safeeyes/glade/
opt/safeeyes/glade/break_screen.glade
opt/safeeyes/glade/settings_dialog.glade
opt/safeeyes/Notification.py
opt/safeeyes/safeeyes
opt/safeeyes/SafeEyesCore.py
opt/safeeyes/SettingsDialog.py
opt/safeeyes/TrayIcon.py
usr/
usr/share/
usr/share/applications/
usr/share/applications/safeeyes.desktop
usr/share/icons/
usr/share/icons/hicolor/
usr/share/icons/hicolor/128x128/
usr/share/icons/hicolor/128x128/apps/
usr/share/icons/hicolor/128x128/apps/safeeyes.png
usr/share/icons/hicolor/16x16/
usr/share/icons/hicolor/16x16/status/
usr/share/icons/hicolor/16x16/status/safeeyes_disabled.png
usr/share/icons/hicolor/16x16/status/safeeyes_enabled.png
usr/share/icons/hicolor/24x24/
usr/share/icons/hicolor/24x24/status/
usr/share/icons/hicolor/24x24/status/safeeyes_disabled.png
usr/share/icons/hicolor/24x24/status/safeeyes_enabled.png
usr/share/icons/hicolor/32x32/
usr/share/icons/hicolor/32x32/apps/
usr/share/icons/hicolor/32x32/apps/safeeyes.png
usr/share/icons/hicolor/32x32/status/
usr/share/icons/hicolor/32x32/status/safeeyes_disabled.png
usr/share/icons/hicolor/32x32/status/safeeyes_enabled.png
usr/share/icons/hicolor/48x48/
usr/share/icons/hicolor/48x48/apps/
usr/share/icons/hicolor/48x48/apps/safeeyes.png
usr/share/icons/hicolor/48x48/status/
usr/share/icons/hicolor/48x48/status/safeeyes_disabled.png
usr/share/icons/hicolor/48x48/status/safeeyes_enabled.png
usr/share/icons/hicolor/64x64/
usr/share/icons/hicolor/64x64/apps/
usr/share/icons/hicolor/64x64/apps/safeeyes.png
```
If you have any issues in installing Safe Eyes, please report them [here](https://github.com/slgobinath/SafeEyes/issues)

4: Start Safe Eyes using this command:  `/opt/safeeyes/safeeyes`

Once started, Safe Eyes will copy the desktop file to `~/.config/autostart` and the configurations to `~/.config/safeeyes`. Therefore, from next time onwards, it should start with the system.

## Configuring Safe Eyes
Just install and forget; Safe Eyes will take care of your eyes. To customize the preferences, go to Settings from Safe Eyes tray icon.
For advanced configuration, go to `~/.config/safeeyes folder`. There you can change the Skip button text in `safeeyes.json` and the look and feel of the break screen in `style/safeeyes_style.css`.
If you want to add more exercises, you can add them in the `safeeyes.json`. A sample configuration is given below for your reference:
```
{
    "break_interval": 15, 
    "long_break_duration": 60, 
    "long_break_messages": [
        "Walk for a while", 
        "Lean back at your seat and relax",
        "Long break exercise 1",
        "Long break exercise 2"
    ], 
    "no_of_short_breaks_per_long_break": 5, 
    "pre_break_warning_time": 10, 
    "short_break_duration": 15, 
    "short_break_messages": [
        "Tightly close your eyes", 
        "Roll your eyes", 
        "Rotate your eyes", 
        "Blink your eyes", 
        "Have some water",
        "Short break exercise 1",
        "Short break exercise 2"
    ], 
    "skip_button_text": "Cancel", 
    "strict_break": false
}
```

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
