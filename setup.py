import os

import setuptools


requires = [
            'python-xlib',
            'pyaudio',
            'psutil',
            'babel']


here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md')) as f:
    long_description = '\n' + f.read()

def _data_files(path):
    for root, dirs, files in os.walk(path):
        if not files:
            continue
        yield (os.path.join('/usr', root), [os.path.join(root, f) for f in files])

setuptools.setup(
    name="safeeyes",
    version="1.2.0",
    description="Protect your eyes from eye strain using this continuous breaks reminder.",
    long_description=long_description,
    author="Gobinath Loganathan",
    author_email="slgobinath@gmail.com",
    url="https://github.com/slgobinath/SafeEyes",
    download_url="https://github.com/slgobinath/SafeEyes/archive/v1.2.0.tar.gz",
    packages=setuptools.find_packages(),
    package_data={'safeeyes': ['config/*.json',
                               'config/style/*.css',
                               'config/lang/*.json',
                               'glade/*.glade',
                               'resource/*']},
    data_files=[('/usr/share/applications', ['share/applications/safeeyes.desktop']),
                ('/usr/share/icons/hicolor/16x16/apps', ['share/icons/hicolor/16x16/apps/safeeyes.png']),
                ('/usr/share/icons/hicolor/24x24/apps', ['share/icons/hicolor/24x24/apps/safeeyes.png']),
                ('/usr/share/icons/hicolor/48x48/apps', ['share/icons/hicolor/48x48/apps/safeeyes.png']),
                ('/usr/share/icons/hicolor/32x32/apps', ['share/icons/hicolor/32x32/apps/safeeyes.png']),
                ('/usr/share/icons/hicolor/64x64/apps', ['share/icons/hicolor/64x64/apps/safeeyes.png']),
                ('/usr/share/icons/hicolor/128x128/apps', ['share/icons/hicolor/128x128/apps/safeeyes.png']),
                ('/usr/share/icons/hicolor/48x48/status', ['share/icons/hicolor/48x48/status/safeeyes_enabled.png', 'share/icons/hicolor/48x48/status/safeeyes_disabled.png']),
                ('/usr/share/icons/hicolor/32x32/status', ['share/icons/hicolor/32x32/status/safeeyes_enabled.png', 'share/icons/hicolor/32x32/status/safeeyes_disabled.png']),
                ('/usr/share/icons/hicolor/24x24/status', ['share/icons/hicolor/24x24/status/safeeyes_enabled.png', 'share/icons/hicolor/24x24/status/safeeyes_disabled.png', 'share/icons/hicolor/24x24/status/safeeyes_timer.png']),
                ('/usr/share/icons/hicolor/16x16/status', ['share/icons/hicolor/16x16/status/safeeyes_enabled.png', 'share/icons/hicolor/16x16/status/safeeyes_disabled.png', 'share/icons/hicolor/16x16/status/safeeyes_timer.png'])
                ],
    install_requires=requires,
    entry_points={'console_scripts': ['safeeyes = safeeyes.__main__:main']},
    keywords='linux utility health eye-strain safe-eyes',
    classifiers=[
        "Operating System :: POSIX :: Linux",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Development Status :: 3 - Alpha",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Utilities"] + [
        ('Programming Language :: Python :: %s' % x) for x in
        '3 3.4 3.5 3.6'.split()]
)
