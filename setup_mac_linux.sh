#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10+ is required. Install it from https://www.python.org/downloads/ and try again."
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate

echo
echo "Setup complete. Optional sample content: python manage.py seed_demo_data"
echo "Start the website with: source .venv/bin/activate && python manage.py runserver"
