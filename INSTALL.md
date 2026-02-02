# 📚 Installation Guide

## 🚀 Quick Start (5 Minutes)

### Step 1: Clone Repository
```bash
git clone https://github.com/Afeez-Ola/study-tracker.git
cd study-tracker
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Set Permissions (macOS Only)
```bash
# Test if permissions work
python -c "from pynput.keyboard import Controller; Controller().press('shift'); print('✅ Permissions OK!')"

# If it fails, enable accessibility permissions:
# 1. System Preferences → Security & Privacy → Privacy
# 2. Click "Accessibility" 
# 3. Click the lock to unlock
# 4. Add "Terminal" to the list
# 5. Restart and test again
```

### Step 4: Start Application
```bash
# Development mode (for testing)
python app.py

# Production mode (for daily use)  
python run.py
```

### Step 5: Open Browser
Navigate to: http://localhost:5000

---

## 🛠️ Detailed Setup Instructions

### Windows Setup

#### Prerequisites
- Windows 10 or later
- Python 3.8+ installed from python.org
- Git for Windows

#### Installation Steps
```cmd
# 1. Clone repository
git clone https://github.com/Afeez-Ola/study-tracker.git
cd study-tracker

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create environment file
copy .env.example .env

# 4. Run the application
python run.py

# 5. Open browser
start http://localhost:5000
```

#### Windows-Specific Notes
- ✅ **No special permissions required**
- ✅ **Firewall exception may be needed** for first run
- ✅ **Antivirus may flag pynput** - allow exception
- ✅ **Run as Administrator** if keyboard access issues

### macOS Setup

#### Prerequisites
- macOS 10.14 (Mojave) or later
- Python 3.8+ from python.org or Homebrew
- Xcode Command Line Tools (for some packages)
- Git (from Xcode or Homebrew)

#### Installation Steps
```bash
# 1. Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Python (if needed)
brew install python@3.9

# 3. Clone repository
git clone https://github.com/Afeez-Ola/study-tracker.git
cd study-tracker

# 4. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 5. Install dependencies
pip install -r requirements.txt

# 6. Setup permissions (critical step)
# Open System Preferences → Security & Privacy → Privacy → Accessibility
# Click the lock icon and add "Terminal" or Python
```

#### macOS Permission Setup (Visual Guide)

1. **Open System Preferences**
   ```
   Apple menu → System Preferences
   ```

2. **Navigate to Privacy**
   ```
   Security & Privacy → Privacy (tab)
   ```

3. **Find Accessibility**
   ```
   Scroll down to "Accessibility" in left menu
   ```

4. **Enable Terminal Access**
   ```
   Click the lock icon (bottom left)
   Enter your password
   Check "Terminal" in the right list
   Or check "Python" if you use a specific Python installation
   ```

5. **Restart Terminal**
   ```bash
   # Close and reopen Terminal
   source venv/bin/activate
   cd study-tracker
   ```

6. **Test Permissions**
   ```bash
   python -c "
from pynput.keyboard import Controller
from pynput.mouse import Controller
try:
    keyboard = Controller()
    mouse = Controller()
    keyboard.press('shift')
    keyboard.release('shift')
    print('✅ macOS accessibility permissions: WORKING')
except Exception as e:
    print('❌ Permission error:', str(e))
    print('Please check System Preferences → Security & Privacy → Privacy → Accessibility')
"
```

#### macOS Troubleshooting
```bash
# If pynput installation fails:
brew install --cask xquartz
export DISPLAY=:0
pip install pynput

# If accessibility keeps failing:
sudo tccutil reset Accessibility
# Then re-enable through System Preferences

# Check current accessibility permissions:
tccutil list Accessibility
```

### Linux Setup

#### Prerequisites
- Ubuntu 18.04+ / CentOS 8+ / Debian 10+
- Python 3.8+ (system or pyenv)
- Development tools (build-essential)
- Git

#### Installation Steps
```bash
# 1. Install system dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install python3 python3-pip python3-venv git

# 2. Install X11 libraries (required for pynput)
sudo apt install python3-tk python3-dev
sudo apt install libx11-dev libxtst-dev libxi-dev

# 3. Clone repository
git clone https://github.com/Afeez-Ola/study-tracker.git
cd study-tracker

# 4. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 5. Install Python dependencies
pip install -r requirements.txt

# 6. Install system packages for pynput
sudo pip install pynput

# 7. Run the application
python run.py
```

#### Linux Desktop Environment Specific

**For GNOME (Ubuntu default):**
```bash
# May need to disable Wayland for pynput
export XDG_SESSION_TYPE=x11
python run.py
```

**For KDE:**
```bash
# Install KDE-specific dependencies
sudo apt install kde-config-x11-xserver
python run.py
```

**For XWayland:**
```bash
# Install additional packages
sudo apt install libxkbcommon-x11-0
python run.py  # May have limited functionality
```

---

## 🔧 Configuration

### Environment Variables
```bash
# Copy and customize environment file
cp .env.example .env
nano .env
```

**Customize these settings:**
```env
# Server Configuration
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_ENV=production

# Database Configuration
DB_PATH=~/study_tracker.db
DB_BACKUP_ENABLED=true
DB_BACKUP_INTERVAL=24

# Monitoring Configuration
IDLE_THRESHOLD_SECONDS=3
ACTIVITY_CHECK_INTERVAL_MS=100
WEBSOCKET_ENABLED=true

# Security Configuration
SECRET_KEY=your-custom-secret-key-here
CORS_ORIGINS=http://localhost:3000
RATE_LIMIT_ENABLED=true
```

### Production Server Setup
```bash
# Create systemd service (Linux)
sudo nano /etc/systemd/system/study-tracker.service
```

**Service file content:**
```ini
[Unit]
Description=Study Tracker Service
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/study-tracker
ExecStart=/home/your-username/study-tracker/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable study-tracker
sudo systemctl start study-tracker

# Check status
sudo systemctl status study-tracker
```

---

## 🐛 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find what's using port 5000
lsof -ti:5000

# Kill the process
sudo kill -9 $(lsof -ti:5000)

# Or use different port
echo "FLASK_PORT=5001" >> .env
python run.py
```

#### Permission Denied (macOS)
```bash
# Reset accessibility permissions
sudo tccutil reset Accessibility

# Re-enable via System Preferences
# System Preferences → Security & Privacy → Privacy → Accessibility
# Check "Terminal" and restart

# Alternative: Add Python specifically
# Find your Python path:
which python
# Add that path to accessibility list
```

#### Import Errors
```bash
# Virtual environment issues
python -m venv clean venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Permission issues (Linux)
sudo usermod -a -G input $USER
# Re-login or restart
```

#### Database Issues
```bash
# Check database file permissions
ls -la ~/study_tracker.db

# Reset database if corrupted
rm ~/study_tracker.db
python -c "from database import DatabaseManager; db = DatabaseManager()"
```

### Log Files
```bash
# Check application logs
tail -f ~/study_tracker_logs/study_tracker.log

# Database logs
sqlite3 ~/study_tracker.db ".schema"

# Health check
curl http://localhost:5000/health
```

---

## 🚀 Verification

### Test Your Installation

```bash
# 1. Server is running
curl http://localhost:5000/health
# Should return: {"status": "healthy", "success": true}

# 2. Activity monitoring works
python -c "
from activity_monitor import ActivityMonitor
monitor = ActivityMonitor()
print('Activity monitor health:', monitor.get_health_status())
"

# 3. Web interface loads
curl -s http://localhost:5000/ | grep -i "Study Tracker"
# Should show the page title

# 4. Database functions
python -c "
from database import DatabaseManager
db = DatabaseManager()
stats = db.get_statistics()
print('Database stats:', stats['total_sessions'], 'sessions')
"
```

### Success Indicators
✅ **Server starts without errors**  
✅ **Health endpoint returns "healthy"**  
✅ **Web interface loads in browser**  
✅ **Activity monitoring has no permission errors**  
✅ **Database operations work**  
✅ **Can start/pause/stop sessions**  

---

## 📱 Mobile App Integration

The repository also includes a React Native mobile app for manual tracking.

### Mobile Setup
```bash
# Install Node.js dependencies
cd ..  # Navigate to parent directory
cd study_tracker-mobile/App.js
npm install
npm start

# For Android
npx react-native run-android

# For iOS  
npx react-native run-ios
```

### Sync Mobile and Desktop
- Export from desktop: CSV format
- Import to mobile: CSV import feature
- Or use shared database file (future feature)

---

## 🔒 Security Best Practices

### Local Network Access
```bash
# Restrict to localhost only (default)
FLASK_HOST=127.0.0.1

# For network access (advanced users only)
FLASK_HOST=0.0.0.0
# Then configure firewall accordingly
```

### Database Security
```bash
# Set proper file permissions
chmod 600 ~/.env
chmod 644 ~/study_tracker.db

# Enable SQLite WAL mode (better performance)
echo "PRAGMA journal_mode=WAL;" | sqlite3 ~/study_tracker.db

# Regular backups
cp ~/study_tracker.db ~/backups/study_tracker_$(date +%Y%m%d).db
```

---

## 🎯 Need Help?

### Check These First
1. **📖 README.md** - Comprehensive documentation
2. **🔧 Configuration** - Check `.env.example` for options  
3. **🐛 Troubleshooting** - Review this guide
4. **📝 Logs** - Check `~/study_tracker_logs/`

### Get Support
- **GitHub Issues**: Report bugs at repository
- **GitHub Discussions**: Ask questions and share tips
- **Documentation**: Check code comments and docstrings

---

## 🎉 Installation Complete!

Once you've completed these steps, you should have:

🖥 **System-wide activity monitoring**  
📊 **Real-time productivity tracking**  
💾 **Local database storage**  
🌐 **Modern web interface**  
📤 **Data import/export**  
🔒 **Privacy-first design**  

**Open your browser to `http://localhost:5000` and start tracking your study sessions!** 🚀

---

*Having trouble? Check the main README.md for additional help and troubleshooting tips.*