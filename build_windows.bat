@echo off
echo ========================================
echo Building Study Tracker for Windows
echo ========================================
echo.

echo Installing required packages...
pip install pyinstaller flask pynput

echo.
echo Building executable...
pyinstaller --onefile --windowed --name "StudyTracker" --icon=app.ico study_tracker_server.py

echo.
echo ========================================
echo Build complete!
echo Executable location: dist\StudyTracker.exe
echo ========================================
pause
