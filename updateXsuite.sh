#!/bin/bash
cd xsuite
git pull
cd ../xobjects
git pull
cd cd ../xdeps
git pull
cd ../xpart
git pull
cd ../xtrack
git pull
cd ../xfields
git pull
cd ../xcoll
git fetch upstream
# git reset --hard upstream/main
git merge upstream/main
git push origin main
git pull
cd ..

pip install -e xobjects
pip install -e xdeps
pip install -e xtrack
pip install -e xpart
pip install -e xfields
pip install -e xcoll
pip install -e xsuite
xsuite-prebuild regenerate
# pip install -e xcoll