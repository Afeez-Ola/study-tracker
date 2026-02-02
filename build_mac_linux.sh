#!/bin/bash

echo "========================================"
echo "Building Study Tracker for macOS/Linux"
echo "========================================"
echo ""

echo "Installing required packages..."
pip3 install pyinstaller flask pynput

echo ""
echo "Building executable..."
pyinstaller --onefile --name "StudyTracker" study_tracker_server.py

echo ""
echo "========================================"
echo "Build complete!"
echo "Executable location: dist/StudyTracker"
echo "========================================"
