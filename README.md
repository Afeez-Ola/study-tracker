# Study Tracker

🎯 **A comprehensive study tracking application with system-wide activity monitoring, productivity analysis, and cross-platform support.**

## ✨ Features

- 🖥 **System-wide activity monitoring** using pynput
- 📊 **Real-time productivity tracking** with intelligent idle detection
- 💾 **Local SQLite database** with migration support
- 📈 **Advanced analytics** including streaks, trends, and insights
- 📤 **CSV import/export** for data portability and backup
- 🌐 **Modern web interface** with dark theme and responsive design
- 🔒 **Privacy-first approach** - all data stored locally on your device
- 🔧 **Production-ready** with comprehensive configuration management
- 🛡️ **Security features** with input validation and sanitization

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    🌐 Web Interface                        │
│                 (HTML/CSS/JavaScript)                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                🖥 Flask Backend                        │
│              (REST API + Business Logic)               │
└───────┬───────────────────────────┬─────────────────┘
        │                         │
┌───────┴───────┐       ┌───────┴───────┐
│  🗄️ Database    │       │  🖱️ Activity   │
│   Management   │       │   Monitoring    │
│   (SQLite)     │       │   (pynput)      │
└─────────────────┘       └─────────────────┘
```

## 🚀 Quick Start

### 📋 Prerequisites

- **Python 3.8+** - Required for all features
- **macOS/Windows/Linux** - Cross-platform support
- **System permissions** - For activity monitoring
- **Git** - For cloning the repository

### 🔧 Installation & Setup

#### 1. Clone the Repository
```bash
# Clone from your GitHub repository
git clone https://github.com/Afeez-Ola/study-tracker.git
cd study-tracker
```

#### 2. Install Dependencies
```bash
# Install all required Python packages
pip install -r requirements.txt

# Verify installation
python -c "import flask, pynput, sqlite3; print('✅ All dependencies installed!')"
```

#### 3. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit configuration (optional)
nano .env
```

**Configuration Options:**
```env
# Server Configuration
FLASK_HOST=127.0.0.1          # Server host
FLASK_PORT=5000                  # Server port
FLASK_ENV=development             # Environment type

# Database Settings
DB_PATH=~/study_tracker.db        # Database file location
DB_BACKUP_ENABLED=true            # Enable automatic backups
IDLE_THRESHOLD_SECONDS=3          # Idle detection threshold

# Monitoring Settings
ACTIVITY_CHECK_INTERVAL_MS=100    # Activity check frequency
WEBSOCKET_ENABLED=true           # Real-time updates
```

#### 4. Set Up Permissions (macOS Only)

For **system-wide activity monitoring** on macOS:

1. **Open System Preferences**
   ```
   Apple menu → System Preferences...
   ```

2. **Navigate to Privacy & Security**
   ```
   Security & Privacy → Privacy
   ```

3. **Enable Accessibility**
   ```
   Select "Accessibility" from left menu
   Click the lock icon to unlock
   Add "Terminal" or "Python" to the list
   ```

4. **Verify Permissions**
   ```bash
   # Test if permissions work
   python -c "from pynput.keyboard import Controller; Controller().press('shift'); print('✅ Permissions OK!')"
   ```

**Windows/Linux**: No special permissions required - should work out of the box!

#### 5. Start the Application

**Development Mode** (for testing):
```bash
python app.py
# Server runs at: http://127.0.0.1:5000
# Debug mode: ON
# Auto-reload: Enabled
```

**Production Mode** (for daily use):
```bash
python run.py
# Server runs at: http://127.0.0.1:5000
# Debug mode: OFF
# Performance optimized
# Logs saved to file
```

## 🎯 How to Use

### Starting Your First Study Session

1. **Open the Web Interface**
   ```
   Navigate to: http://localhost:5000
   ```

2. **Start a Session**
   - Enter what you're studying (e.g., "Python Programming", "Biology Chapter 5")
   - Click **"Start Session"** button
   - Activity monitoring begins immediately

3. **Monitor Your Progress**
   - **Real-time timer** shows total session duration
   - **Activity indicator** shows if you're actively studying
   - **Productivity meter** displays current focus percentage
   - **Auto-pause** triggers when idle for 3+ seconds

4. **Pause/Resume as Needed**
   - Click **"Pause"** to take breaks
   - Click **"Resume"** to continue studying
   - Manual pauses don't count as productive time

5. **Complete Your Session**
   - Click **"Finish Session"** when done
   - Review your productivity score and time breakdown
   - Session is automatically saved to database

### Understanding the Interface

**📊 Timer Display**: Shows total session time (HH:MM:SS)  
**🟢 Activity Indicator**: 
   - Green = Currently active (studying detected)
   - Gray = Idle (no activity detected)
**📈 Productivity Meter**: Percentage of active vs total time
**⏱️ Active Time**: Time spent actually working
**⏸️ Idle Time**: Break/pause time
**🎯 Current Streak**: Consecutive days of studying

### Advanced Features

#### 📈 View Statistics
```bash
# Click "View Stats" button to see:
- Total sessions completed
- Total study time (hours/minutes)
- Average productivity score
- Current streak 🔥
- Top study topics
- Productivity distribution
```

#### 📤 Export Your Data
```bash
# Click "Export to CSV" to download:
- All completed sessions
- Time breakdown data
- Productivity scores
- Importable into spreadsheet software
```

#### 📥 Import Existing Data
```bash
# Click "Import from CSV" to:
- Restore previous session data
- Migrate from other tracking apps
- Combine data across devices
- Validates CSV format automatically
```

## 🔧 Advanced Configuration

### Customizing Idle Detection
```env
# Adjust sensitivity
IDLE_THRESHOLD_SECONDS=1    # Very sensitive (1-second idle)
IDLE_THRESHOLD_SECONDS=5    # Less sensitive (5-second idle)
IDLE_THRESHOLD_SECONDS=10   # Very lenient (10-second idle)
```

### Database Management
```bash
# Check database health
curl http://localhost:5000/health

# Database location
~/study_tracker.db

# Backup location
~/study_tracker_backups/ (if enabled)
```

### Performance Optimization
```env
# Reduce CPU usage
ACTIVITY_CHECK_INTERVAL_MS=500    # Check every 500ms
ACTIVITY_CHECK_INTERVAL_MS=1000   # Check every 1s

# Memory management
ACTIVITY_LOG_RETENTION_DAYS=7     # Keep 7 days of logs
ACTIVITY_LOG_RETENTION_DAYS=30    # Keep 30 days of logs (default)
```

## 🛠️ API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/start_session` | POST | Start new study session |
| `/pause_session` | POST | Pause/resume current session |
| `/stop_session` | POST | Complete and save session |
| `/get_status` | GET | Get real-time session data |
| `/get_sessions` | GET | Retrieve session history |
| `/get_stats` | GET | Get aggregated statistics |
| `/export_csv` | GET | Download CSV export |
| `/import_csv` | POST | Import CSV data |
| `/health` | GET | System health check |

### Example API Usage

```bash
# Start a session
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"topic":"React Development","description":"Learning hooks and state"}' \
  http://localhost:5000/start_session

# Check current status
curl http://localhost:5000/get_status

# Get session history
curl http://localhost:5000/get_sessions

# Export data
curl http://localhost:5000/export_csv > study_sessions.csv
```

## 🔒 Privacy & Security

### Data Protection
- ✅ **Local-only storage** - No data leaves your device
- ✅ **No cloud dependencies** - Works completely offline
- ✅ **Input sanitization** - Malicious content filtered
- ✅ **Key redaction** - Sensitive keystrokes masked
- ✅ **No analytics** - No tracking or telemetry

### Security Features
- 🔒 **Input validation** - All user inputs validated
- 🛡️ **SQL injection protection** - Parameterized queries
- 🚫 **XSS prevention** - Content properly escaped
- 📊 **Rate limiting** - Prevent abuse (configurable)
- 🔐 **CSRF protection** - Cross-site request forgery prevention

### Transparency
- 📖 **Open source** - All code visible on GitHub
- 📋 **Clear logs** - See exactly what's being tracked
- 🎛️ **Configurable** - Customize all tracking settings
- 🚫 **Opt-out possible** - Disable activity monitoring anytime

## 🚀 Deployment Options

### Option A: Local Server (Recommended)
```bash
# Best for full functionality
python run.py

# Advantages:
✅ System-wide activity monitoring
✅ Real-time productivity tracking
✅ Local data storage
✅ Complete privacy control
```

### Option B: Cloud Deployment (Limited)
```bash
# For web-only functionality
# Deploy to Railway, Render, or similar platforms
# Note: System monitoring not available in cloud

# Limitations:
❌ No keyboard/mouse tracking
❌ No real-time activity detection
❌ Manual time tracking only
```

### Option C: Hybrid Approach
```bash
# Use local server + cloud backup
# 1. Run local server for full tracking
# 2. Periodically export and upload to cloud storage
# 3. Keep local data as primary source
```

## 🔧 Troubleshooting

### Common Issues & Solutions

#### macOS Accessibility Permissions
```bash
# Problem: "Operation not permitted" error
# Solution: Enable accessibility permissions
sudo python -c "
from pynput.keyboard import Controller
try:
    Controller().press('shift')
    Controller().release('shift')
    print('✅ Permissions working!')
except:
    print('❌ Enable accessibility permissions')
    print('System Preferences → Security & Privacy → Privacy → Accessibility')
"
```

#### Port Conflicts
```bash
# Problem: Port 5000 already in use
# Solution 1: Change port
echo "FLASK_PORT=5001" >> .env
python run.py

# Solution 2: Kill existing process
lsof -ti:5000 | xargs kill
python run.py
```

#### Database Issues
```bash
# Check database health
curl http://localhost:5000/health

# Repair database if needed
python -c "
from database import DatabaseManager
db = DatabaseManager()
db.init_database()
print('✅ Database initialized/checked')
"
```

#### Performance Issues
```bash
# Reduce monitoring frequency
echo "ACTIVITY_CHECK_INTERVAL_MS=200" >> .env
python run.py

# Enable performance mode
echo "FLASK_ENV=production" >> .env
python run.py
```

## 📊 Data & Analytics

### Productivity Calculation
```
Productivity Score = (Active Time ÷ Total Time) × 100

Where:
- Active Time = Time with keyboard/mouse activity
- Total Time = Active Time + Idle Time
- Idle Threshold = 3 seconds (configurable)

Levels:
- 90%+ = Excellent (deep focus)
- 75-89% = Good (good concentration)
- 60-74% = Moderate (some distractions)
- 40-59% = Poor (many interruptions)
- <40% = Very Poor (highly distracted)
```

### Streak Calculation
```
Streak = Consecutive days with at least 1 completed session

Rules:
- Any completed session counts for that day
- Days are chronological (no gaps allowed)
- Streak resets when a day has no sessions
- Maximum streak: Calculated from all historical data
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

### Development Setup
```bash
# 1. Fork the repository
git clone https://github.com/Afeez-Ola/study-tracker.git
cd study-tracker

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run tests
python -m pytest

# 5. Start development server
python app.py
```

### Project Structure
```
study_tracker/
├── 📁 app.py                 # Main Flask application
├── 📁 run.py                 # Production runner
├── 📁 database.py            # Database operations
├── 📁 session_manager.py      # Session state management
├── 📁 activity_monitor.py    # Activity tracking
├── 📁 config.py             # Configuration management
├── 📁 utils.py              # Utility functions
├── 📁 requirements.txt       # Python dependencies
├── 📁 templates/index.html   # Web interface
├── 📁 .env.example          # Environment template
├── 📁 .gitignore           # Git ignore file
├── 📁 README.md             # This documentation
└── 📁 package.json           # Mobile app (existing)
```

### Making Changes
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make your changes
# Test thoroughly
python -m pytest

# Commit your work
git add .
git commit -m "feat: add your feature description"

# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request
# Visit GitHub and create PR against main branch
```

### Code Style
- Use clear, descriptive variable names
- Add docstrings to all functions
- Follow PEP 8 Python style guide
- Include error handling for all operations
- Add logging for debugging

## 📄 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) file for details.

### What this means:
- ✅ **Commercial use** allowed
- ✅ **Modifications** allowed  
- ✅ **Distribution** allowed
- ✅ **Private use** allowed
- ✅ **Sublicensing** allowed

### Limitations:
- ❌ **No warranty** provided
- ❌ **No liability** assumed
- ❌ **Attribution** required (keep license notice)

## 🆘 Support & Community

### Getting Help
- 📋 **GitHub Issues**: Report bugs and request features
- 📖 **Documentation**: Check this README first
- 🔍 **Troubleshooting**: Review the troubleshooting section
- 💬 **Discussions**: Ask questions and share tips

### Contributing Back
- ⭐ **Star the repository** if you find it useful
- 🐛 **Report issues** to help improve the project
- 💡 **Suggest features** to shape future development
- 📝 **Improve documentation** to help others

---

## 🎯 Ready to Transform Your Productivity?

Your **Study Tracker** is now ready to help you:

✨ **Track study sessions** with intelligent activity monitoring  
📈 **Analyze productivity patterns** with detailed insights  
🎯 **Build consistent habits** with streak tracking  
🔒 **Maintain privacy** with local-only data storage  
🚀 **Deploy anywhere** with flexible architecture  

**Start tracking your study sessions today and watch your productivity soar!** 🚀

---

*Built with ❤️ by Afeez-Ola - Transforming study habits through technology*

## Usage

1. **Start a session**: Enter what you're studying and click "Start Session"
2. **Track activity**: Monitor real-time productivity and active/idle time
3. **Pause/Resume**: Click pause to temporarily stop tracking
4. **Complete session**: Click finish to save with productivity metrics
5. **View history**: See all completed sessions with analytics
6. **Export data**: Download CSV files for backup or analysis

## API Endpoints

- `POST /start_session` - Start new study session
- `POST /pause_session` - Pause/resume current session
- `POST /stop_session` - Complete and save session
- `GET /get_status` - Get real-time session status
- `GET /get_sessions` - Retrieve session history
- `GET /get_stats` - Get aggregated statistics
- `GET /export_csv` - Export sessions as CSV
- `POST /import_csv` - Import sessions from CSV
- `GET /health` - Health check endpoint

## Configuration

Copy `.env.example` to `.env` and modify:

```env
FLASK_ENV=production
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
DB_PATH=~/study_tracker.db
IDLE_THRESHOLD_SECONDS=3
```

## File Structure

```
study_tracker/
├── app.py                 # Main Flask application
├── run.py                 # Production runner
├── database.py            # Database operations
├── session_manager.py      # Session state management
├── activity_monitor.py    # Activity tracking
├── config.py             # Configuration management
├── utils.py              # Utility functions
├── requirements.txt       # Python dependencies
├── templates/index.html   # Web interface
├── .env.example          # Environment template
└── README.md             # This file
```

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Database Migrations
```bash
python -c "from database import DatabaseManager; db = DatabaseManager(); db.init_database()"
```

## Privacy & Security

- **Local-first**: All data stored locally on your machine
- **No cloud dependencies**: Works completely offline
- **Privacy protection**: Sensitive input automatically redacted
- **Data encryption**: Optional database encryption available

## Troubleshooting

### macOS Accessibility Issues
```bash
# Check if accessibility is enabled
python -c "from pynput.keyboard import Controller; Controller().press('shift')"
```

### Database Issues
```bash
# Check database health
curl http://localhost:5000/health
```

### Port Conflicts
```bash
# Change port in .env
FLASK_PORT=5001 python run.py
```

## License

MIT License - see LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review log files for debugging information