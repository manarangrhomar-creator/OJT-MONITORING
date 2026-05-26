@echo off
REM setup.bat - Setup script for OJT Monitoring System (Windows)

echo =========================================
echo OJT Monitoring System - Setup Script
echo =========================================

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Create environment file if it doesn't exist
if not exist .env (
    echo Creating .env file...
    copy .env.example .env
    echo WARNING: Please update .env with your PostgreSQL credentials
)

REM Run migrations
echo Running database migrations...
python manage.py migrate

REM Create superuser prompt
echo Creating superuser...
python manage.py createsuperuser

REM Collect static files
echo Collecting static files...
python manage.py collectstatic --noinput

echo =========================================
echo Setup complete!
echo =========================================
echo.
echo To start the development server, run:
echo   python manage.py runserver
echo.
echo To access the application:
echo   Admin Panel: http://localhost:8000/admin/
echo   API Docs: http://localhost:8000/api/docs/
pause
