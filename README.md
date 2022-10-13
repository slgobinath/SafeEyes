# Safe Eyes

[![Release](https://img.shields.io/github/v/release/slgobinath/SafeEyes)](https://github.com/slgobinath/SafeEyes/releases)
[![PyPI version](https://badge.fury.io/py/safeeyes.svg)](https://badge.fury.io/py/safeeyes)
[![Debian](https://badges.debian.net/badges/debian/unstable/safeeyes/version.svg)](https://packages.debian.org/unstable/safeeyes)
[![AUR](https://img.shields.io/aur/version/safeeyes)](https://aur.archlinux.org/packages/safeeyes)
[![Translation status](https://hosted.weblate.org/widgets/safe-eyes/-/translations/svg-badge.svg)](https://hosted.weblate.org/engage/safe-eyes/?utm_source=widget)
[![Awesome Humane Tech](https://raw.githubusercontent.com/humanetech-community/awesome-humane-tech/main/humane-tech-badge.svg?sanitize=true)](https://github.com/humanetech-community/awesome-humane-tech)
[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://paypal.me/slgobinath)

Protect your eyes from eye strain using this simple and beautiful, yet extensible break reminder.

Visit the official site: https://slgobinath.github.io/SafeEyes/ for more details.

## Safe Eyes command-line arguments

```text
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

```bash
sudo add-apt-repository ppa:slgobinath/safeeyes
sudo apt update
sudo apt install safeeyes
```

### Arch

```bash
yay -S safeeyes
```

### Gentoo

```bash
sudo emerge -av x11-misc/safeeyes
```

### Debian

```bash
sudo apt-get install safeeyes
```

### Fedora

```bash
sudo dnf install libappindicator-gtk3 python3-psutil cairo-devel python3-devel gobject-introspection-devel cairo-gobject-devel
sudo pip3 install safeeyes
sudo gtk-update-icon-cache /usr/share/icons/hicolor
```

### OpenSUSE Tumbleweed

```bash
sudo zypper refresh
sudo zypper install safeeyes
```

### Alpine Linux

```bash
sudo apk add safeeyes
```

### Other Linux & Run from source

Ensure to meet the following dependencies:

- gir1.2-appindicator3-0.1 or gir1.2-ayatanaappindicator3-0.1
- gir1.2-notify-0.7
- libappindicator-gtk3
- python3-psutil
- xprintidle (optional)
- wlrctl (wayland optional)

**To install Safe Eyes:**

```bash
sudo pip3 install safeeyes
```

After installation, restart your system to update the icons,

**To run from source:**

```bash
git clone https://github.com/slgobinath/SafeEyes.git
cd SafeEyes
python3 -m safeeyes
```

Safe Eyes installers install the required icons to `/usr/share/icons/hicolor`. When you run Safe Eyes from source without, some icons may not appear.


### Install in Virtual Environment

Some Linux systems like Cent OS do not have matching dependencies available in their repository. In such systems, you can install and use Safe Eyes in a Python Virtual Environment. The following instruction was tested on Cent OS 7.

1. Install the necessary dependencies

    ```bash
    sudo yum install python3-devel dbus dbus-devel cairo cairo-devel cairomm-devel libjpeg-turbo-devel pango pango-devel pangomm pangomm-devel gobject-introspection-devel cairo-gobject-devel
    ```

2. Create a virtual environment in your home folder

    ```bash
    mkdir ~/safeeyes
    cd ~/safeeyes/

    pip3 install virtualenv --user
    virtualenv --no-site-packages venv
    source venv/bin/activate
    pip3 install dbus-python safeeyes
    ```

3. Start Safe Eyes from terminal

    ```bash
    cd ~/safeeyes & source venv/bin/activate
    python3 -m safeeyes
    ```

For more details, please check the issue: [#329](https://github.com/slgobinath/SafeEyes/issues/329)

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

## IDE Support

<p align="center">Thanks to JetBrains for offering IDE support to develop this Open Source project.</p>

<p align="center"><a href="https://www.jetbrains.com/?from=SafeEyes"><img src="https://raw.githubusercontent.com/JetBrains/logos/master/web/jetbrains/jetbrains.svg?sanitize=true" width="64" align="center"></a></p>
