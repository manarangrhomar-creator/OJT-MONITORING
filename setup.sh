#!/bin/bash
# setup.sh - Setup script for OJT Monitoring System

echo "==========================================="
echo "OJT Monitoring System - Setup Script"
echo "==========================================="

# Create virtual environment
echo "Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate  # For Linux/Mac
# venv\Scripts\activate  # For Windows

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please update .env with your PostgreSQL credentials"
fi

# Run migrations
echo "Running database migrations..."
python manage.py migrate

# Create superuser prompt
echo "Creating superuser..."
python manage.py createsuperuser

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "==========================================="
echo "✓ Setup complete!"
echo "==========================================="
echo ""
echo "To start the development server, run:"
echo "  python manage.py runserver"
echo ""
echo "To access the application:"
echo "  Admin Panel: http://localhost:8000/admin/"
echo "  API Docs: http://localhost:8000/api/docs/"
