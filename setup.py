#!/usr/bin/python3

import os

from pathlib import Path
from setuptools import Command, setup
from setuptools.command.build import build as orig_build

class build(orig_build):
    sub_commands = [('build_mo', None), *orig_build.sub_commands]


class build_mo(Command):
    description = 'Compile .po files into .mo files'

    files = None

    def initialize_options(self):
        self.files = None
        self.editable_mode = False
        self.build_lib = None

    def finalize_options(self):
        self.set_undefined_options("build_py", ("build_lib", "build_lib"))
        pass

    def run(self):
        files = self._get_files()

        for build_file, source_file in files.items():
            if not self.editable_mode:
                # Parent directory required for msgfmt to work correctly
                Path(build_file).parent.mkdir(parents=True, exist_ok=True)
            self.spawn(['msgfmt', source_file, '-o', build_file])

    def _get_files(self):
        if self.files is not None:
            return self.files

        files = {}

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

                source_file = po_dir + po_file

                build_file = po_dir + mo_file
                if not self.editable_mode:
                    build_file = os.path.join(self.build_lib, build_file)

                files[build_file] = source_file

        self.files = files
        return files

    def get_output_mapping(self):
        return self._get_files()

    def get_outputs(self):
        return self._get_files().keys()

    def get_source_files(self):
        return  self._get_files().values()


setup(
    cmdclass={'build': build, 'build_mo': build_mo}
)
