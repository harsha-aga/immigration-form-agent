#!/bin/zsh
# Launch the app from anywhere. PYTHONPATH makes the source importable even if the venv's
# editable-install file is not picked up.
cd "$(dirname "$0")" || exit 1
PYTHONPATH="$PWD/src" exec "$PWD/.venv/bin/python" -m uscis_autofill "$@"
