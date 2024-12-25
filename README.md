<img src="https://raw.githubusercontent.com/slgobinath/SafeEyes/master/safeeyes/platform/icons/hicolor/64x64/apps/io.github.slgobinath.SafeEyes.png" align="left">

# Safe Eyes

[![Release](https://img.shields.io/github/v/release/slgobinath/SafeEyes)](https://github.com/slgobinath/SafeEyes/releases)
[![PyPI version](https://badge.fury.io/py/safeeyes.svg)](https://badge.fury.io/py/safeeyes)
[![Debian](https://badges.debian.net/badges/debian/unstable/safeeyes/version.svg)](https://packages.debian.org/unstable/safeeyes)
[![AUR](https://img.shields.io/aur/version/safeeyes)](https://aur.archlinux.org/packages/safeeyes)
[![Flathub](https://img.shields.io/flathub/v/io.github.slgobinath.SafeEyes)](https://flathub.org/apps/details/io.github.slgobinath.SafeEyes)
[![Translation status](https://hosted.weblate.org/widgets/safe-eyes/-/translations/svg-badge.svg)](https://hosted.weblate.org/engage/safe-eyes/?utm_source=widget)
[![Awesome Humane Tech](https://raw.githubusercontent.com/humanetech-community/awesome-humane-tech/main/humane-tech-badge.svg?sanitize=true)](https://github.com/humanetech-community/awesome-humane-tech)

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

Safe Eyes is available on the official repositories of many popular the distributions.

<a href="https://repology.org/project/safeeyes/versions">
    <img src="https://repology.org/badge/vertical-allrepos/safeeyes.svg" alt="Packaging status" align="right">
</a>

It is also available in Ubuntu PPA, Arch AUR and Python PyPI. You can choose any installation source and install on any Linux system with Python 3.


### Ubuntu, Linux Mint and other Ubuntu Derivatives

The [Official PPA for Safe Eyes](https://launchpad.net/~safeeyes-team/+archive/ubuntu/safeeyes) hosts the latest version of safeeyes **for Ubuntu 22.04 and above**. 
```bash
sudo add-apt-repository ppa:safeeyes-team/safeeyes
sudo apt update
sudo apt install safeeyes
```

On older versions of Ubuntu, an older version of Safe Eyes is available on the official repositories.
```bash
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
 If you want to use Smart Pause plugin, install the latest xprintidle from: [alonid/xprintidle](https://copr.fedorainfracloud.org/coprs/alonid/xprintidle/)
```bash
sudo dnf install python3-psutil python3-packaging cairo-devel python3-devel gobject-introspection-devel cairo-gobject-devel
sudo pip3 install safeeyes
sudo gtk-update-icon-cache /usr/share/icons/hicolor
```

We are looking for an official package maintainer for Fedora. Please [contact us](https://github.com/slgobinath/SafeEyes/issues/611) if you are interested.

### OpenSUSE Tumbleweed

```bash
sudo zypper refresh
sudo zypper install safeeyes
```

### Alpine Linux

```bash
sudo apk add safeeyes
```

### Flatpak
**Warning**: Many plugins and features don't work well in the flatpak. We recommend that you use one of the native packages listed above. Flatpak-only bugs should be reported at https://github.com/flathub/io.github.slgobinath.SafeEyes.
```bash
flatpak install flathub io.github.slgobinath.SafeEyes
```

### Other Linux & Run from source

Ensure to meet the following dependencies:

- gir1.2-notify-0.7
- python3-babel
- python3-croniter
- python3-psutil
- python3-packaging
- python3-xlib
- xprintidle (optional)
- wlrctl (wayland optional)
- Python 3.10+

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


### Install in a virtual environment

Some Linux systems like CentOS do not have matching dependencies available in their repository. In such systems, you can install and use Safe Eyes in a Python virtual environment.

1. Install the necessary dependencies for CentOS 7

    ```bash
    sudo yum install python3-devel dbus dbus-devel cairo cairo-devel cairomm-devel libjpeg-turbo-devel pango pango-devel pangomm pangomm-devel gobject-introspection-devel cairo-gobject-devel
    ```

2. Create a virtual environment in your home folder

    ```bash
    mkdir ~/safeeyes
    cd ~/safeeyes/

    python3 -m venv venv
    source venv/bin/activate
    pip3 install safeeyes
    ```

3. Start Safe Eyes from the terminal

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

## Local development

When adding new translatable strings in the source code, make sure to run `python validate_po.py --extract` to add them to the translation template. You will need to install `python3-polib` for this.

Examples for translatable strings are `_("This is a string")` in Python code, or `<property name="label" translatable="yes">This is a label</property>` in Glade/xml files.

To ensure the new strings are well-formed, you can use `python validate_po.py --validate`.

## How to Release?

0. Run `update-po.sh` to generate new translation files (which will be eventually updated by translators). Commit and push the changes to the master branch.
1. Checkout the latest commits from the `master` branch
2. Run `python3 -m safeeyes` to make sure nothing is broken
3. Update the Safe Eyes version in the following places (Open the project in VSCode and search for the current version):
    - [setup.py](https://github.com/slgobinath/SafeEyes/blob/master/setup.py#L82)
    - [setup.py](https://github.com/slgobinath/SafeEyes/blob/master/setup.py#L89)
    - [safeeyes.py](https://github.com/slgobinath/SafeEyes/blob/master/safeeyes/safeeyes.py#L42)
    - [io.github.slgobinath.SafeEyes.metainfo.xml](https://github.com/slgobinath/SafeEyes/blob/master/safeeyes/platform/io.github.slgobinath.SafeEyes.metainfo.xml#L56)
    - [about_dialog.glade](https://github.com/slgobinath/SafeEyes/blob/master/safeeyes/glade/about_dialog.glade#L74)
4. Update the [changelog](https://github.com/slgobinath/SafeEyes/blob/master/debian/changelog) (for Ubuntu PPA release)
5. Commit the changes to `master`
6. Create a pull-request from `master` to `release`
7. Merge the PR to release **with merge commit** (Important to merge with merge commit)

## How you can help improving translation of Safe Eyes

First check if translations for your language are already available on [Weblate](https://hosted.weblate.org/engage/safe-eyes/), which is the cloud based translation platform we use. 

- If the language is already there, feel free to add new translations or improve the existing ones.
- If it is not there, please [open an issue](https://github.com/slgobinath/SafeEyes/issues) in Github so that we can add your language to Weblate.

## License

GNU General Public License v3
