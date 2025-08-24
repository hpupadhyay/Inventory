@echo off
:: Sets the title of the command prompt window
TITLE Django ERP Server

:: Navigate to your project's root directory
ECHO Navigating to project directory...
cd "D:"
cd "D:\Inventory Management\inventory_project"

:: --- IMPORTANT ---
:: If your virtual environment folder is named something other than 'venv',
:: change the word 'venv' in the line below to match your folder's name.
ECHO Activating virtual environment...
CALL python -m venv venv
CALL .\venv\Scripts\Activate
CALL pip install -r requirements.txt

:: Run the Django development server
ECHO Starting Django server...
python manage.py runserver

:: This will keep the window open after the server is stopped (or if it crashes on startup)
