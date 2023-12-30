#!/bin/bash

rm -rf build/ dist/ safeeyes.egg-info/ .eggs/

pip3 install build
python3 -m build
twine upload --repository pypitest dist/safeeyes*.tar.gz
clear >$(tty)
twine upload --repository pypitest dist/safeeyes*.whl
