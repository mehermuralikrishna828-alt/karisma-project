# Karisma — Community Crowdfunding, Donations & Philanthropy Platform

Karisma is a Django web application for community fundraising, donations, philanthropy causes, and user dashboards.

> **Demo-only payments:** No real payment gateway is connected. Donation/payment flows simulate a demo transaction and must not be used to collect real money.

## Technology

- Python 3.10 or newer (Python 3.11 or 3.12 recommended)
- Django 4.2–5.x (installed from `requirements.txt`)
- SQLite for local development
- Django templates, HTML/CSS/JavaScript
- Bootstrap 5.3, Bootstrap Icons, and Chart.js loaded from CDNs (an internet connection is needed in the browser)
- Pillow for image uploads

## Run on another computer

### 1. Install Python

Install Python 3.10+ from [python.org](https://www.python.org/downloads/). On Windows, select **Add Python to PATH** during installation. Open a new terminal after installing it.

### 2. Extract the project

Extract this ZIP. Open a terminal in the `karisma` project folder — the folder containing `manage.py` and `requirements.txt`.

### 3. Create a virtual environment and install packages

**Windows PowerShell:**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use Command Prompt and run `.venv\Scripts\activate.bat` after creating the environment.

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Create the database tables

The source ZIP supplied for this project did not contain Django migration files. For the first setup, generate them and create the local SQLite database:

```bash
python manage.py makemigrations
python manage.py migrate
```

When you first set up the repository, commit the generated migration files (`*/migrations/0001_*.py`) to GitHub. After those files have been committed, future computers only need `python manage.py migrate`; do not generate new migrations unless you have changed the models.

### 5. (Optional) Load sample/demo content

To populate the app with example campaigns, causes, and donations, run:

```bash
python manage.py seed_demo_data
```

The seed command creates demo accounts that share the password `Karisma@123`. Use this password only for the local demonstration. **Never use the seeded accounts or this shared password on a public/production deployment.** If you need an administrator login, create one with `python manage.py createsuperuser`.

### 6. Start the website

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/** in your browser. The admin area is at **http://127.0.0.1:8000/admin/**. To stop the local server, press `Ctrl+C` in the terminal.

The virtual environment must be activated whenever you run project commands. If you close the terminal, open a new one in the project folder and activate `.venv` again.

## Windows setup helper

You can run `setup_windows.bat` from the project folder to create `.venv`, install the dependencies, generate the initial migrations, and migrate the database. Then run `run_windows.bat` to start the server. The optional sample-data command is still run separately using `python manage.py seed_demo_data`.

## Upload to GitHub

1. **Run the setup steps above once before your first push.** The original ZIP did not include Django migration files; running the setup creates them. Keep the generated `*/migrations/0001_*.py` files in the project and commit them so GitHub and other computers get the same database schema.
2. Sign in to [GitHub](https://github.com/) and create a **new empty repository**. Do not add a README or other starter files there, because this project already has its own README.
3. Open a terminal in the `karisma` project folder (the folder containing `manage.py`). Run the following commands, replacing the URL with your repository's URL:

   ```bash
   git init
   git add .
   git commit -m "Prepare Karisma project for GitHub"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
   git push -u origin main
   ```

4. If Git says `git` is not recognized, install [Git](https://git-scm.com/downloads) and reopen the terminal. Make sure `.gitignore` remains in the project root.

If you use GitHub's website instead of Git, first run setup so the migration files are generated, then upload the **contents** of the `karisma` folder, including `README.md`, `requirements.txt`, `manage.py`, the Python app folders, their generated migration files, `templates`, and `static`.

## Important: GitHub Pages vs hosting the app

GitHub can host this project's **source code**, but **GitHub Pages cannot run this Django/Python backend**, authentication, admin interface, or SQLite database. To make the working application publicly accessible, deploy it to a Python-capable hosting service and configure its environment variables and database. The current project is set up for local development, not production deployment.

## Project structure

| Folder/app | Purpose |
|---|---|
| `core` | Home page, shared model, template tags and navigation context |
| `accounts` | Registration, login, profiles and notifications |
| `crowdfunding` | Campaign listing, details, creation, updates and saved campaigns |
| `donations` | Donation categories, drives, demo donation flow and donation services |
| `philanthropy` | Philanthropy causes and following/supporting causes |
| `dashboard` | User summary, campaigns, history, saved items and notifications |
| `templates/` | Django HTML templates |
| `static/` | CSS, JavaScript and logo assets |

## Common commands

```bash
python manage.py check                  # check Django configuration
python manage.py migrate                # apply database migrations
python manage.py seed_demo_data          # load sample content
python manage.py seed_demo_data --reset  # reset/rebuild sample content (destructive to seeded demo data)
python manage.py createsuperuser         # create an admin login
python manage.py runserver               # start local server
```

## Configuration and safety

The application uses SQLite by default and stores uploaded media in `media/`, which is intentionally excluded from Git. Local database files, virtual environments, environment files, and Python cache files are also excluded.

Before any public deployment, set a strong, private `DJANGO_SECRET_KEY`, set `DJANGO_DEBUG=0`, configure `DJANGO_ALLOWED_HOSTS` with the exact host names, and review HTTPS/database/media settings for the chosen host. Do not commit passwords, private keys, `.env` files, real user data, or a production database. The seeded content and simulated payments are for demonstration only.
