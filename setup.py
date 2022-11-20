import os, sys, site
import subprocess
import setuptools


requires = [
    'babel',
    'psutil',
    'croniter',
    'PyGObject',
    'python-xlib'
]

_ROOT = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(_ROOT, 'README.md')) as f:
    long_description = f.read()


def __compile_po_files():
    """
    Compile the *.po trainslation files.
    """
    localedir = 'safeeyes/config/locale'
    po_dirs = [localedir + '/' + l + '/LC_MESSAGES/'
               for l in next(os.walk(localedir))[1]]
    for po_dir in po_dirs:
        po_files = [f
                    for f in next(os.walk(po_dir))[2]
                    if os.path.splitext(f)[1] == '.po']
        for po_file in po_files:
            filename, _ = os.path.splitext(po_file)
            mo_file = filename + '.mo'
            msgfmt_cmd = 'msgfmt {} -o {}'.format(
                po_dir + po_file, po_dir + mo_file)
            subprocess.call(msgfmt_cmd, shell=True)


def __data_files():
    """
    Collect the data files.
    """
    root_dir = sys.prefix
    return [(os.path.join(root_dir, "share/applications"), ["safeeyes/platform/safeeyes.desktop"]),
    (os.path.join(root_dir, "share/icons/hicolor/24x24/status"), ["safeeyes/platform/icons/hicolor/24x24/status/safeeyes_disabled.png", "safeeyes/platform/icons/hicolor/24x24/status/safeeyes_enabled.png", "safeeyes/platform/icons/hicolor/24x24/status/safeeyes_timer.png"]),
    (os.path.join(root_dir, "share/icons/hicolor/24x24/apps"), ["safeeyes/platform/icons/hicolor/24x24/apps/safeeyes.png"]),
    (os.path.join(root_dir, "share/icons/hicolor/16x16/status"), ["safeeyes/platform/icons/hicolor/16x16/status/safeeyes_disabled.png", "safeeyes/platform/icons/hicolor/16x16/status/safeeyes_enabled.png", "safeeyes/platform/icons/hicolor/16x16/status/safeeyes_timer.png"]),
    (os.path.join(root_dir, "share/icons/hicolor/16x16/apps"), ["safeeyes/platform/icons/hicolor/16x16/apps/safeeyes.png"]),
    (os.path.join(root_dir, "share/icons/hicolor/32x32/status"), ["safeeyes/platform/icons/hicolor/32x32/status/safeeyes_disabled.png", "safeeyes/platform/icons/hicolor/32x32/status/safeeyes_enabled.png"]),
    (os.path.join(root_dir, "share/icons/hicolor/32x32/apps"), ["safeeyes/platform/icons/hicolor/32x32/apps/safeeyes.png"]),
    (os.path.join(root_dir, "share/icons/hicolor/64x64/apps"), ["safeeyes/platform/icons/hicolor/64x64/apps/safeeyes.png"]),
    (os.path.join(root_dir, "share/icons/hicolor/128x128/apps"), ["safeeyes/platform/icons/hicolor/128x128/apps/safeeyes.png"]),
    (os.path.join(root_dir, "share/icons/hicolor/48x48/status"), ["safeeyes/platform/icons/hicolor/48x48/status/safeeyes_disabled.png", "safeeyes/platform/icons/hicolor/48x48/status/safeeyes_enabled.png"]),
    (os.path.join(root_dir, "share/icons/hicolor/48x48/apps"), ["safeeyes/platform/icons/hicolor/48x48/apps/safeeyes.png"]),]


def __package_files(directory):
    """
    Collect the package files.
    """
    paths = []
    for (path, _, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths


def __package_data():
    """
    Return a list of package data.
    """
    __compile_po_files()
    data = ['glade/*.glade', 'resource/*']
    data.extend(__package_files('safeeyes/config'))
    data.extend(__package_files('safeeyes/plugins'))
    data.extend(__package_files('safeeyes/platform'))
    return data

setuptools.setup(
    name="safeeyes",
    version="2.1.4",
    description="Protect your eyes from eye strain using this continuous breaks reminder.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Gobinath Loganathan",
    author_email="slgobinath@gmail.com",
    url="https://github.com/slgobinath/SafeEyes",
    download_url="https://github.com/slgobinath/SafeEyes/archive/v2.1.4.tar.gz",
    packages=setuptools.find_packages(),
    package_data={'safeeyes': __package_data()},
    data_files=__data_files(),
    install_requires=requires,
    entry_points={'console_scripts': ['safeeyes = safeeyes.__main__:main']},
    keywords='linux utility health eye-strain safe-eyes',
    classifiers=[
        "Operating System :: POSIX :: Linux",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Development Status :: 5 - Production/Stable",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Utilities"] + [('Programming Language :: Python :: %s' % x) for x in '3 3.5 3.6 3.7 3.8 3.9'.split()]
)
