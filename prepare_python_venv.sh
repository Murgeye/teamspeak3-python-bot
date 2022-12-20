#!/usr/bin/env bash

echo "Setting up Python virtual env. This takes a moment, please wait..."

VENV_DIR="${1}"

if [[ -d "${VENV_DIR}" ]]; then
    rm -rf "${VENV_DIR}"
fi

python3 -m venv "${VENV_DIR}"

if [[ $? -eq 0 ]]; then
    source "${VENV_DIR}/bin/activate"
else
    echo "Failed to set up the Python virtual env directory."
    exit 1
fi

pip install --quiet -r requirements.txt

if [[ $? -ne 0 ]]; then
    echo "Failed to install the Python requirements in the virtual env."
    exit 1
fi

echo "Python virtual env has been successfully set up."

echo "You will find the application logs within the installation directory."
