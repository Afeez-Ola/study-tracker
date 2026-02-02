# Study Tracker - Multi-Platform

A study tracking application available for **Windows, macOS, Linux, iOS, and Android**.

## 📱 Platform Overview

### Desktop (Windows/macOS/Linux)
- ✅ **System-wide activity tracking** (keyboard/mouse)
- ✅ **Automatic idle detection**
- ✅ **SQLite database on your computer**
- ✅ **CSV export/import**
- ✅ **Honest productivity tracking**

### Mobile (iOS/Android)
- ✅ **Manual timer tracking**
- ✅ **Study streaks**
- ✅ **Session history**
- ✅ **Data export**
- ⚠️ **Note:** Cannot track system-wide activity (iOS/Android security restriction)

---

## 🖥️ Desktop Installation

### Option 1: Run from Source (All Platforms)

**Requirements:**
- Python 3.7+

**Steps:**
1. Install dependencies:
   ```bash
   pip install flask pynput
   ```

2. Run the server:
   ```bash
   python study_tracker_server.py
   ```

3. Open browser: `http://localhost:5000`

### Option 2: Build Standalone Executable

#### Windows
1. Run `build_windows.bat`
2. Executable will be in `dist\StudyTracker.exe`
3. Double-click to run

#### macOS/Linux
1. Make build script executable:
   ```bash
   chmod +x build_mac_linux.sh
   ```
2. Run build script:
   ```bash
   ./build_mac_linux.sh
   ```
3. Executable will be in `dist/StudyTracker`

---

## 📱 Mobile Installation (iOS/Android)

### Prerequisites
- Node.js 16+ installed
- Expo CLI installed: `npm install -g expo-cli`

### Steps

1. **Navigate to mobile app folder:**
   ```bash
   cd mobile_app
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm start
   ```

4. **Run on device:**
   - **iOS:** Press `i` (requires macOS and Xcode)
   - **Android:** Press `a` (requires Android Studio)
   - **Phone:** Install "Expo Go" app and scan QR code

### Building for Production

#### iOS (requires macOS)
```bash
expo build:ios
```
Follow prompts to create .ipa file for App Store submission.

#### Android
```bash
expo build:android
```
Creates .apk or .aab file for Google Play Store.

---

## 📊 Features Comparison

| Feature | Desktop | Mobile |
|---------|---------|--------|
| System-wide tracking | ✅ Yes | ❌ No (OS restriction) |
| Manual timer | ✅ Yes | ✅ Yes |
| Idle detection | ✅ Automatic | ❌ N/A |
| Database | SQLite (local) | AsyncStorage |
| CSV Export | ✅ Yes | ✅ Yes |
| CSV Import | ✅ Yes | ❌ Not yet |
| Offline | ✅ Yes | ✅ Yes |
| GitHub-style graph | ✅ Yes | ❌ Not yet |

---

## 🔄 Data Sync Between Devices

Currently, data sync is manual:

1. **Export from Desktop:**
   - Click "Export to CSV"
   - Save file

2. **Import to Another Desktop:**
   - Click "Import from CSV"
   - Select saved file

3. **Mobile to Desktop:**
   - Mobile export creates CSV text
   - Copy/paste into file
   - Import on desktop

**Future:** Cloud sync feature planned!

---

## 📂 Data Storage Locations

### Desktop
- **Windows:** `C:\Users\YourName\study_tracker.db`
- **macOS:** `/Users/yourname/study_tracker.db`
- **Linux:** `/home/yourname/study_tracker.db`

### Mobile
- iOS: App sandbox (AsyncStorage)
- Android: App data directory (AsyncStorage)

---

## 🚨 Important Notes

### Mobile Limitations
Mobile operating systems (iOS/Android) **do not allow apps to monitor system-wide keyboard/mouse activity** for security and privacy reasons. This means:

- ❌ Cannot detect typing in other apps
- ❌ Cannot detect when you switch apps
- ❌ Cannot automatically track idle time

**Solution:** The mobile app uses a **manual timer** - you start it when you begin studying and stop it when you finish. This is still accurate if you're honest with yourself!

### Desktop Permissions

**macOS:** You'll need to grant accessibility permissions:
1. System Preferences → Security & Privacy → Privacy
2. Select "Accessibility"
3. Add Terminal or Python app

**Windows:** No special permissions needed

**Linux:** May need to run as user (not root)

---

## 🛠️ Troubleshooting

### Desktop

**"Module not found" Error:**
```bash
pip install flask pynput
```

**Port 5000 already in use:**
Edit `study_tracker_server.py` line 237:
```python
app.run(debug=False, host='0.0.0.0', port=5001)
```

**Cannot track activity on macOS:**
Grant accessibility permissions (see above)

### Mobile

**"Unable to resolve module":**
```bash
cd mobile_app
rm -rf node_modules
npm install
```

**Expo app won't connect:**
- Ensure phone and computer are on same WiFi
- Restart Expo dev server
- Try scanning QR code again

---

## 📈 Roadmap

- [ ] Cloud sync between devices
- [ ] Pomodoro timer mode
- [ ] Study goals and reminders
- [ ] Charts and analytics
- [ ] Dark/light theme toggle
- [ ] Widget support (mobile)
- [ ] GitHub-style contribution graph (mobile)

---

## 💡 Tips

1. **Desktop:** Let it run in background while studying
2. **Mobile:** Start timer when you begin, stop when done
3. **Export regularly:** Backup your data weekly
4. **Be honest:** The tracker only works if you use it properly

---

## 🔒 Privacy

- **100% local data** - nothing sent to cloud
- **No accounts required**
- **No tracking or analytics**
- **You own your data**
- **Export anytime**

---

## 📄 License

Free to use and modify for personal use.

---

## 🆘 Support

If you encounter issues:
1. Check the troubleshooting section
2. Make sure you have the latest version
3. Check that all dependencies are installed

---

## 🙏 Credits

Built to help students track their study time honestly and improve their habits!
