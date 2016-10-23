# Safe Eyes
Protect your eyes from eye strain using this continuous breaks reminder. A Free and Open Source Linux alternative for EyeLeo.

## Installation

### Ubuntu:
1: Add the PPA: `sudo add-apt-repository ppa:slgobinath/safeeyes`

2: Download the package list: `sudo apt update`

3: Install uget-chrome-wrapper: `sudo apt install safeeyes`

4: Start Safe Eyes from start menu.

### Other Linux:

Manual installation is not tested in any systems. I will update this page as soon as I have tested in any other Linux distributions.

1: Download and extract [safeeyes.tar.gz](https://github.com/slgobinath/SafeEyes/releases/download/v1.0.6/hicolor.tar.gz) into `/opt`

2: Download and extract [hicolor.tar.gz](https://github.com/slgobinath/SafeEyes/releases/download/v1.0.6/hicolor.tar.gz) into `~/.icons` or `/usr/share/icons`

3: Install the dependencies: `gir1.2-appindicator3-0.1`, `python-xlib`, `python-apscheduler`, `python-gobject`

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