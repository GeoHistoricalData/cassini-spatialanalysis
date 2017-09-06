#! /usr/bin/env bash

BASEDIR=$(dirname "$0")
sudo apt-get install virtualenv
virtualenv $HOME/.venv
. $HOME/.venv/bin/activate
$HOME/.venv/bin/pip install ${BASEDIR}/.

