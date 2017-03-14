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
        yield (root, [os.path.join(root, f) for f in files])

setuptools.setup(
    name="safeeyes",
    version="1.1.9",
    description="Protect your eyes from eye strain using this continuous breaks reminder.",
    long_description=long_description,
    author="Gobinath Loganathan",
    author_email="slgobinath@gmail.com",
    url="https://github.com/slgobinath/SafeEyes",
    download_url="https://github.com/slgobinath/SafeEyes/archive/master.zip",
    packages=setuptools.find_packages(),
    package_data={'safeeyes': ['config/*.json',
                               'config/style/*.css',
                               'config/lang/*.json',
                               'glade/*.glade',
                               'resource/*']},
    data_files=list(_data_files(
            os.path.join(os.path.dirname(__file__), 'share'))),
    install_requires=requires,
    entry_points={'console_scripts': ['safeeyes = safeeyes.safeeyes:main']},
    keywords='linux utility health eye-strain safe-eyes',
    classifiers=[
        "Operating System :: POSIX :: Linux",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Development Status :: 5 - Production/Stable",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Utilities"] + [
        ('Programming Language :: Python :: %s' % x) for x in
        '2 2.7'.split()
    ]
)
