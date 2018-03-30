#!/bin/bash

rm -rf build/ dist/ safeeyes.egg-info/ .eggs/

python3 setup.py sdist bdist_wheel
twine upload --repository pypitest dist/safeeyes*.tar.gz
clear >$(tty)
twine upload --repository pypitest dist/safeeyes*.whl