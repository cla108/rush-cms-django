#!/usr/bin/env bash
set -euo pipefail

cd /srv/rush-cms-django
echo "Pulling repository to $(pwd)..."
sudo git pull origin main

# Source the project venv
VENV="/srv/rush-cms-django/.venv"
if [ ! -f "$VENV/bin/activate" ]; then
    echo "ERROR: Venv not found at $VENV"
    exit 1
fi
source "$VENV/bin/activate"
echo "Using Python: $(which python)"

# Make sure poetry uses this Python
POETRY="/home/deploy/.local/bin/poetry"
echo "Using Poetry env: $($POETRY env info --path)..."
$POETRY lock --no-interaction
$POETRY install --no-interaction --no-root

# Migrate Django and collect static
$(which python) manage.py migrate
$(which python) manage.py collectstatic --noinput

# Restart Gunicorn
sudo systemctl restart gunicorn.service
echo "Successfully deployed!"
