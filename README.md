# Study Tracker

A comprehensive study tracking application with system-wide activity monitoring, productivity analysis, and cross-platform support.

## Features

- 🖥 **System-wide activity monitoring** using pynput
- 📊 **Real-time productivity tracking** with idle detection
- 💾 **Local SQLite database** for session storage
- 📈 **Statistics and analytics** with streak tracking
- 📤 **CSV import/export** for data portability
- 🌐 **Web-based interface** with responsive design
- 🔒 **Privacy-first approach** with local data storage

## Architecture

- **Backend**: Flask Python server with REST API
- **Database**: SQLite with migration support
- **Frontend**: HTML/CSS/JavaScript with real-time updates
- **Monitoring**: pynput for keyboard/mouse activity tracking
- **Deployment**: Local server with production runner

## Quick Start

### Prerequisites
- Python 3.8+
- macOS/Windows/Linux (system-wide monitoring requires permissions)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/study_tracker.git
   cd study_tracker
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server**
   ```bash
   # Development mode
   python app.py
   
   # Production mode
   python run.py
   ```

4. **Open browser**
   Navigate to `http://localhost:5000`

### macOS Permissions

For system-wide activity monitoring on macOS:

1. **Open System Preferences**
2. **Go to Security & Privacy → Privacy**
3. **Select "Accessibility"**
4. **Add Terminal** or your Python interpreter
5. **Restart the application**

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