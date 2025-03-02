#!/usr/bin/python3


from pathlib import Path
from setuptools import Command, setup
from setuptools.command.build import build as OriginalBuildCommand


class BuildCommand(OriginalBuildCommand):
    sub_commands = [("build_mo", None), *OriginalBuildCommand.sub_commands]


class BuildMoSubCommand(Command):
    description = "Compile .po files into .mo files"

    files = None

    def initialize_options(self):
        self.files = None
        self.editable_mode = False
        self.build_lib = None

    def finalize_options(self):
        self.set_undefined_options("build_py", ("build_lib", "build_lib"))

    def run(self):
        files = self._get_files()

        for build_file, source_file in files.items():
            if not self.editable_mode:
                # Parent directory required for msgfmt to work correctly
                Path(build_file).parent.mkdir(parents=True, exist_ok=True)
            self.spawn(["msgfmt", source_file, "-o", build_file])

    def _get_files(self):
        if self.files is not None:
            return self.files

        files = {}

        localedir = Path("safeeyes/config/locale")
        po_dirs = [d.joinpath("LC_MESSAGES") for d in localedir.iterdir() if d.is_dir()]
        for po_dir in po_dirs:
            po_files = [
                f for f in po_dir.iterdir() if f.is_file() and f.suffix == ".po"
            ]
            for po_file in po_files:
                mo_file = po_file.with_suffix(".mo")

                source_file = po_file
                build_file = mo_file

                if not self.editable_mode:
                    build_file = Path(self.build_lib).joinpath(build_file)

                files[str(build_file)] = str(source_file)

        self.files = files
        return files

    def get_output_mapping(self):
        return self._get_files()

    def get_outputs(self):
        return self._get_files().keys()

    def get_source_files(self):
        return self._get_files().values()


setup(cmdclass={"build": BuildCommand, "build_mo": BuildMoSubCommand})
