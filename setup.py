import os
import subprocess
import setuptools


requires = [
    'babel',
    'psutil',
    'PyGObject',
    'python-xlib'
]

_ROOT = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(_ROOT, 'README.md')) as f:
    long_description = '\n' + f.read()


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
            filename, ext = os.path.splitext(po_file)
            mo_file = filename + '.mo'
            msgfmt_cmd = 'msgfmt {} -o {}'.format(po_dir + po_file, po_dir + mo_file)
            subprocess.call(msgfmt_cmd, shell=True)


def _data_files(path):
    """
    Collect the data files.
    """
    for root, dirs, files in os.walk(path):
        if not files:
            continue
        yield (os.path.join('/usr', root), [os.path.join(root, f) for f in files])


def __package_files(directory):
    """
    Collect the package files.
    """
    paths = []
    for (path, dirs, filenames) in os.walk(directory):
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
    return data


__data_files = list(_data_files('share'))

setuptools.setup(
    name="safeeyes",
    version="2.0.4",
    description="Protect your eyes from eye strain using this continuous breaks reminder.",
    long_description=long_description,
    author="Gobinath Loganathan",
    author_email="slgobinath@gmail.com",
    url="https://github.com/slgobinath/SafeEyes",
    download_url="https://github.com/slgobinath/SafeEyes/archive/v2.0.3.tar.gz",
    packages=setuptools.find_packages(),
    package_data={'safeeyes': __package_data()},
    data_files=__data_files,
    install_requires=requires,
    entry_points={'console_scripts': ['safeeyes = safeeyes.__main__:main']},
    keywords='linux utility health eye-strain safe-eyes',
    classifiers=[
        "Operating System :: POSIX :: Linux",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Development Status :: 5 - Production/Stable",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Utilities"] + [
        ('Programming Language :: Python :: %s' % x) for x in
        '3 3.4 3.5 3.6'.split()]
)
