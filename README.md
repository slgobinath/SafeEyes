# Safe Eyes

[![GitHub version](https://badge.fury.io/gh/slgobinath%2FSafeEyes.svg)](https://badge.fury.io/gh/slgobinath%2FSafeEyes)
[![PyPI version](https://badge.fury.io/py/safeeyes.svg)](https://badge.fury.io/py/safeeyes)
[![Translation status](https://hosted.weblate.org/widgets/safe-eyes/-/translations/svg-badge.svg)](https://hosted.weblate.org/engage/safe-eyes/?utm_source=widget)
[![Badge](https://badges.debian.net/badges/debian/unstable/safeeyes/version.svg)](https://packages.debian.org/unstable/safeeyes)


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
  --status          print the status of running safeeyes instance and exit
  --version         show program's version number and exit
```

## Installation guide
Safe Eyes is available in Ubuntu PPA, Arch AUR, Gentoo and Python PyPI. You can choose any installation source and install on any Linux system with Python 3.

### Ubuntu, Linux Mint and other Ubuntu Derivatives
```
sudo add-apt-repository ppa:slgobinath/safeeyes
sudo apt update
sudo apt install safeeyes
```

### Arch
```
yaourt -S safeeyes
```

### Gentoo
```
sudo emerge -av x11-misc/safeeyes
```

### Debian
```
sudo apt-get install gir1.2-appindicator3-0.1 gir1.2-notify-0.7 python3-psutil python3-xlib xprintidle
sudo pip3 install safeeyes
sudo update-icon-caches /usr/share/icons/hicolor
```
People using unstable/testing Debian can install Safe Eyes froms the official repository using the following command:
```
sudo apt-get install safeeyes
```

### Fedora
```
sudo dnf install libappindicator-gtk3 python3-psutil
sudo pip3 install safeeyes
sudo gtk-update-icon-cache /usr/share/icons/hicolor
```

### Other Linux & Run from source
Ensure to meet the following dependencies:

- gir1.2-appindicator3-0.1
- gir1.2-notify-0.7
- libappindicator-gtk3
- python3-psutil
- xprintidle (optional)

**To install Safe Eyes:**
```
sudo pip3 install safeeyes
```
After installation, restart your system to update the icons,

**To run from source:**
```
git clone https://github.com/slgobinath/SafeEyes.git
cd SafeEyes
python3 -m safeeyes
```
Safe Eyes installers install the required icons to `/usr/share/icons/hicolor`. When you run Safe Eyes from source without, some icons may not appear.

## Features
 - Remind you to take breaks with exercises to reduce RSI
 - Disable keyboard during breaks
 - Notification before and after breaks
 - Smart pause if system is idle
 - Multi-screen support
 - Customizable user interface
 - RPC API to control externally
 - Command-line arguments to control the running instance
 - Customizable using plug-ins

## Third-party Plugins
Thirdparty plugins are available at another GitHub repository: [safeeyes-plugins](https://github.com/slgobinath/safeeyes-plugins). More details about how to write your own plugin and how to install third-party plugin are available there.

## License

GNU General Public License v3
