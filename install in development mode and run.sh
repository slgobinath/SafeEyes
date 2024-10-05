#!/bin/bash


python3 -m pip install -e '/home/xy/workspace/Safeeyes fixálása/SafeEyes 2.1.6, fixálva 3 dologgal, lásd a git logot/'
# sleep 3
# read x;
safeeyes &


# How to: https://packaging.python.org/en/latest/tutorials/installing-packages/

# Installing from a local src tree

# Installing from local src in Development Mode, i.e. in such a way that the project appears to be installed, but yet is still editable from the src tree.
# Unix/macOS

# python3 -m pip install -e <path>

# Windows

# You can also install normally from src
# Unix/macOS

# python3 -m pip install <path>



# Installing from VCS

# Install a project from VCS in “editable” mode. For a full breakdown of the syntax, see pip’s section on VCS Support.
# Unix/macOS

# python3 -m pip install -e SomeProject @ git+https://git.repo/some_pkg.git          # from git
# python3 -m pip install -e SomeProject @ hg+https://hg.repo/some_pkg                # from mercurial
# python3 -m pip install -e SomeProject @ svn+svn://svn.repo/some_pkg/trunk/         # from svn
# python3 -m pip install -e SomeProject @ git+https://git.repo/some_pkg.git@feature  # from a branch
