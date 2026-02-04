# Meal Plan Verification System

Automated cafeteria meal plan verification system using RFID cards, touchscreen displays, and daily usage tracking with Google Sheets integration.

---

## 🎯 Project Overview

**Purpose:** Eliminate manual student name entry, enforce daily meal limits, and integrate with MUNDOWARE POS system and Google Sheets for data tracking.

**Key Features:**

- ✅ RFID card scanning for instant student identification
- ✅ Real-time eligibility verification (daily meal limits)
- ✅ Dual-screen cashier workflow (MUNDOWARE + verification touchscreen)
- ✅ **Google Sheets integration** for real-time transaction logging and daily summaries
- ✅ Encrypted student data (names & card UIDs)
- ✅ Automatic midnight usage reset (Panama time)
- ✅ Transaction logging and reporting
- ✅ Manual override options for cashiers
- ✅ Admin dashboard with real-time analytics
- ✅ Clean terminal output (only important events)

---

## 📊 NEW: Google Sheets Integration

### Real-Time Data Tracking

The system automatically logs all transactions to Google Sheets:

**Transactions Sheet:**

- Logs every approval and denial immediately
- Columns: Day, Time, Student ID, Meal Type, Status
- Time format: 08:15 AM (no seconds)

**Daily Summary Sheet:**

- Generated automatically at 2:00 PM Panama time
- Only counts APPROVED meals
- Columns: Date, Breakfast, Lunch, Snacks, Total
- Provides daily analytics for administration

### Setup Google Sheets Integration

1. **Create Google Sheet** with two tabs: "Transactions" and "Daily Summary"

2. **Add Google Apps Script:**
   - Go to Extensions → Apps Script
   - Copy the script from `docs/google_apps_script.js` (provided separately)
   - Save and deploy as Web App
   - Set permissions: Execute as "Me", Access: "Anyone"

3. **Configure System:**
   - Add the Web App URL to `.env`:
     ```
     GOOGLE_SHEETS_ENABLED=True
     GOOGLE_SHEETS_WEB_APP_URL=https://script.google.com/macros/s/.../exec
     ```

4. **Run Setup Function:**
   - In Apps Script editor, select `setupSheets` from dropdown
   - Click Run to initialize sheets with headers

---

## 📋 System Requirements

### Hardware

- **3× Cashier Stations**, each with:
  - Windows 10/11 PC (existing cashier computers)
  - ACR122U USB RFID Reader
  - Lenovo ThinkVision M14t 14" USB Touchscreen
  - USB ports (2 available per station)

### Software

- Python 3.9 or higher
- pip (Python package manager)
- Web browser (Chrome/Edge recommended for touchscreen)

### Network

- Local network connectivity between cashier stations
- Internet connection for Google Sheets integration
- Database server (if using shared MySQL database)

---

## 🚀 Installation Guide

### Step 1: Clone or Download Repository

```bash
git clone https://github.com/your-school/meal-plan-verification.git
cd meal-plan-verification
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Mac/Linux
# OR
venv\Scripts\activate  # Windows
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt --break-system-packages
```

**If you encounter errors:**

- Windows: Install Visual C++ Build Tools for `pyscard`
- Linux: `sudo apt-get install pcscd libpcsclite-dev swig`
- macOS: `brew install swig`

### Step 4: Generate Encryption Key

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Save this key securely!** You'll need it in the next step.

### Step 5: Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your settings
nano .env  # or use your preferred editor
```

**Required Configuration:**

```bash
# Database (start with SQLite for simplicity)
DATABASE_TYPE=sqlite
DATABASE_PATH=meal_plan.db

# CRITICAL: Paste your encryption key here
ENCRYPTION_KEY=YOUR_GENERATED_KEY_FROM_STEP_4

# Flask settings
FLASK_SECRET_KEY=your-random-secret-key-here
FLASK_HOST=0.0.0.0
FLASK_PORT=5001

# Station identification
STATION_ID=Station_1  # Change to Station_2, Station_3 for other cashiers
CASHIER_ID=CASHIER_01

# RFID Reader
RFID_ENABLED=True

# MUNDOWARE Integration (configure after testing)
MUNDOWARE_ENABLED=False  # Set to True when ready to connect

# Google Sheets Integration
GOOGLE_SHEETS_ENABLED=True
GOOGLE_SHEETS_WEB_APP_URL=your-web-app-url-here

# Scheduler (Panama time)
DAILY_RESET_TIME=00:00  # Midnight
```

### Step 6: Initialize Database

```bash
python << 'EOF'
from web.app import create_app
from database.sample_data import populate_database

app = create_app()
with app.app_context():
    populate_database(50, clear_existing=False)
EOF
```

This creates 50 sample students for testing.

### Step 7: Test RFID Reader (Optional but Recommended)

```bash
python services/rfid_reader.py

# You should see:
# - "Using reader: ACS ACR122U..."
# - Wave a MIFARE card near reader
# - Card UID should display
# - Press Ctrl+C to stop
```

### Step 8: Start the System

```bash
python main.py
```

**You should see:**

```
 * Serving Flask app 'web.app'
 * Debug mode: on
```

### Step 9: Access Interfaces

**Touchscreen Interface** (for cashiers):

- Open browser: `http://localhost:5001/`
- **Optional:** Set browser to fullscreen (F11)

**Admin Dashboard**:

- Navigate to: `http://localhost:5001/admin`
- View statistics, manage students, export reports

---

## 🖥️ Multi-Station Setup

### Station 1 Configuration

```bash
# .env file for Station 1
STATION_ID=Station_1
CASHIER_ID=CASHIER_01
FLASK_PORT=5001
```

### Station 2 Configuration

```bash
# .env file for Station 2
STATION_ID=Station_2
CASHIER_ID=CASHIER_02
FLASK_PORT=5002  # Different port if on same machine
```

### Station 3 Configuration

```bash
# .env file for Station 3
STATION_ID=Station_3
CASHIER_ID=CASHIER_03
FLASK_PORT=5003
```

### Shared Database Setup (Recommended for Production)

**Option A: SQLite with Network Share** (Simpler)

```bash
# All stations use same database file on network drive
DATABASE_TYPE=sqlite
DATABASE_PATH=\\server\shared\meal_plan.db
```

**Option B: MySQL Database** (Better Performance)

1. Install MySQL server on one machine
2. Create database:

```sql
CREATE DATABASE meal_plan_db;
CREATE USER 'meal_plan_user'@'%' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON meal_plan_db.* TO 'meal_plan_user'@'%';
FLUSH PRIVILEGES;
```

3. Update all stations' `.env`:

```bash
DATABASE_TYPE=mysql
MYSQL_HOST=192.168.1.100  # IP of MySQL server
MYSQL_PORT=3306
MYSQL_USER=meal_plan_user
MYSQL_PASSWORD=secure_password
MYSQL_DATABASE=meal_plan_db
```

---

## 📊 Student Data Management

### Adding Real Students

**Method 1: CSV Import** (Recommended)

1. Create CSV file with columns:

   ```
   student_id,card_rfid_uid,student_name,grade_level,meal_plan_type,daily_meal_limit,status
   ```

2. Example CSV content:

   ```csv
   10001,04A3B2C145,John Smith,10,Premium,2,Active
   10002,04F8A9B3C2,Jane Doe,11,Basic,1,Active
   ```

3. Run import script (to be created):
   ```bash
   python scripts/import_students.py students.csv
   ```

**Method 2: Admin Interface**

1. Go to `http://localhost:5001/admin`
2. Click "Add Student"
3. Scan student card to get UID
4. Enter student details
5. Save

**Method 3: Manual Database Entry**

```python
python << 'EOF'
from web.app import create_app
from database.db_manager import get_db_manager

app = create_app()
with app.app_context():
    dm = get_db_manager()
    dm.add_student(
        student_id='12345',
        card_rfid_uid='04A3B2C145',  # Get from RFID scan
        student_name='John Smith',
        grade_level=10,
        meal_plan_type='Premium',
        daily_meal_limit=2,
        status='Active'
    )
EOF
```

---

## 🔄 MUNDOWARE Integration

### Option A: Shared Database Table (Recommended)

1. Request database access from MUNDOWARE support
2. Get connection details:
   - Host IP
   - Database name
   - Username & password
   - Table schema

3. Update `.env`:

```bash
MUNDOWARE_ENABLED=True
MUNDOWARE_HOST=192.168.1.200
MUNDOWARE_PORT=3306
MUNDOWARE_USER=mundoware_integration
MUNDOWARE_PASSWORD=secure_password
MUNDOWARE_DATABASE=mundoware_pos
```

4. This system writes to `mundoware_student_lookup` table:
   - MUNDOWARE reads student info from this table
   - Auto-fills student ID, name, meal plan type

---

## 🛡️ Security & Data Protection

### Encryption

**What is encrypted:**

- Student names (personally identifiable)
- RFID card UIDs (can be linked to students)

**NOT encrypted:**

- Student IDs (already anonymized school IDs)
- Meal plan types (public information)
- Transaction counts

### Encryption Key Management

**Critical:** The encryption key in `.env` file must be:

- ✅ Backed up securely (IT department)
- ✅ Same across all cashier stations
- ✅ Never committed to version control
- ❌ Never shared publicly

**Key Backup Process:**

1. Copy `ENCRYPTION_KEY` from `.env`
2. Store in school's secure password manager
3. IT department keeps offline backup

**If key is lost:** All encrypted data is permanently unrecoverable.

---

## 📅 Daily Operations

### Normal Operation

1. **Morning Setup:**
   - Power on cashier PCs
   - Verify RFID readers connected (green light)
   - Open browser to touchscreen interface
   - System automatically ready

2. **During Meal Service:**
   - Students scan cards (remove card after scan!)
   - System auto-detects scan and shows student info
   - Cashier verifies eligibility on touchscreen
   - Clicks APPROVE or DENY
   - Data logs to Google Sheets automatically
   - Completes transaction in MUNDOWARE

3. **Manual Overrides:**
   - If card doesn't work: Click "Manual Entry"
   - Type student ID
   - Continue normally

### Automatic Scheduled Tasks

**Midnight (00:00 Panama Time):**

- Resets all daily meal usage counts
- Students get fresh daily allowances

**2:00 PM (14:00 Panama Time):**

- Generates daily summary
- Sends to Google Sheets "Daily Summary" tab
- Only counts APPROVED meals

**Every Hour:**

- System health check
- Logs system status

**Weekly (Sunday 2:00 AM):**

- Database cleanup
- Deletes old transaction logs (older than 30 days)
- Optimizes database

### Manual Reset

If needed, you can manually trigger reset:

```bash
# Via admin dashboard
http://localhost:5001/admin → "Reset Daily Meal Counts" button
```

⚠️ **Warning:** This clears all usage counts AND today's transactions!

---

## 📊 Reports & Analytics

### Admin Dashboard

Access via `http://localhost:5001/admin`

**Real-time Statistics:**

- Total students in system
- Today's meals served (approved)
- Today's denials
- Breakdown by meal type (Breakfast, Lunch, Snack)

**Features:**

- Auto-refresh every 60 seconds
- Manual refresh button
- Export students to CSV
- Trigger manual reset (for testing)

### Google Sheets Reports

**Transactions Sheet:**

- Every transaction logged in real-time
- Filter by date, student, meal type, status
- Create custom pivot tables and charts
- Export to Excel if needed

**Daily Summary Sheet:**

- One row per day (added at 2pm)
- Shows approved meal counts only
- Easy to create trend charts
- Calculate weekly/monthly totals

### Log Files

Located in `logs/` directory:

- `system.log` - General application logs
- `transactions.log` - All meal transactions
- `errors.log` - Errors and warnings

**Log Rotation:** Logs rotate daily, kept for 30 days.

---

## 🔧 Troubleshooting

### RFID Reader Not Working

**Symptoms:** "No card readers found" error

**Solutions:**

1. Check USB connection
2. Install ACR122U drivers:
   - Windows: Download from https://www.acs.com.hk/
   - Linux: `sudo apt-get install pcscd`
3. Verify reader in Device Manager (Windows) or `lsusb` (Linux)
4. Try different USB port

### Card Scans Continuously

**Symptoms:** Terminal shows multiple scans without moving card

**Solutions:**

1. **Remove the card from the reader!** Card must be moved away between scans
2. Debounce is set to 5 seconds, but card must physically leave detection field
3. Place card only briefly (1-2 seconds), then remove

### Database Connection Failed

**Symptoms:** "Error connecting to database"

**Solutions:**

1. SQLite: Check file path in `.env`
2. MySQL: Verify host/port/credentials
3. Test connection:
   ```bash
   python -c "from config.settings import config; print(config.SQLALCHEMY_DATABASE_URI)"
   ```

### Touchscreen Not Responsive

**Solutions:**

1. Calibrate touchscreen (Windows Settings > Devices > Touchscreen)
2. Check USB-C connection
3. Try different browser (Chrome recommended)
4. Verify touch drivers installed

### Google Sheets Not Updating

**Symptoms:** Transactions not appearing in Google Sheets

**Solutions:**

1. Check `.env` has correct `GOOGLE_SHEETS_WEB_APP_URL`
2. Verify `GOOGLE_SHEETS_ENABLED=True`
3. Test the Web App URL manually (should show error, but confirms it's accessible)
4. Check terminal for error messages
5. Verify Apps Script is deployed correctly

### Screen Not Auto-Navigating After Scan

**Symptoms:** Card scans but waiting screen doesn't show student info

**Solutions:**

1. Check browser console (F12) for JavaScript errors
2. Verify lookup table is being created (check terminal for "📝 Updated MUNDOWARE lookup")
3. Ensure you're not scanning while on another page
4. Try manual entry as fallback

---

## 🆘 Emergency Procedures

### System Down During Meal Service

**Fallback Process:**

1. Use manual name entry in MUNDOWARE
2. Log student names on paper
3. After system restored, manually enter transactions
4. Cashiers can approve/deny based on memory

### Database Corruption

**Recovery Steps:**

1. Stop system: `Ctrl+C` in terminal
2. Restore from backup (daily backup recommended)
3. Check Google Sheets for transaction history
4. Manually recreate daily usage from Google Sheets data

### Lost Encryption Key

**⚠️ WARNING:** Data is unrecoverable without key.

**Prevention:**

- Backup key in password manager
- IT department offline backup
- Test backup restoration monthly

### Google Sheets Access Lost

**Fallback:**

- System continues working locally
- All data still saved to local database
- Admin dashboard still accessible
- Re-deploy Web App when access restored

---

## 🔍 System Monitoring

### Terminal Output Guide

**Clean Terminal Messages:**

```
📇 Card Scanned #1: 47C0E33D***
   API Response: 200
✅ Student: Thomas Lopez (10855)
   Eligible: True
   Meals used: 0/1

📝 Updated MUNDOWARE lookup: 10855 (eligible: True)
🔍 Recent scan detected: 10855 (timestamp: ...)

✅ MEAL APPROVED: Thomas Lopez (10855) - Lunch

🧹 Cleared MUNDOWARE lookup for Station_1
```

**What Each Icon Means:**

- 📇 = Card detected by RFID reader
- 📝 = MUNDOWARE lookup table updated
- 🔍 = Waiting screen detected the scan
- ✅ = Meal approved
- ❌ = Meal denied
- 🧹 = Lookup table cleared
- 🔄 = Daily reset triggered
- 📊 = Daily summary sent to Google Sheets

### Health Check

System runs automatic health check every hour:

- Verifies database connection
- Logs daily statistics
- Confirms system is operational

---

## 📞 Support & Contact

**Technical Issues:**

- System Administrator: [Your IT Contact]
- Developer: [Your Name/Contact]

**MUNDOWARE Integration:**

- MUNDOWARE Support: [Vendor Contact]

**Hardware Issues:**

- ACR122U: ACS Support (https://www.acs.com.hk/)
- Lenovo Touchscreen: Lenovo Support

---

## 📝 License & Credits

**Created for:** [Your School Name]  
**Project Duration:** 6 weeks  
**Budget:** $1,957  
**Developer:** [Your Name]  
**Date:** January 2026

**Technologies Used:**

- Python 3.9+
- Flask Web Framework
- SQLAlchemy ORM
- ACR122U RFID Reader
- MIFARE Classic 1K Cards
- Lenovo ThinkVision Touchscreen
- Google Sheets API (via Apps Script)

---

## 🔄 Version History

**v1.1.0** (January 30, 2026)

- ✅ Added Google Sheets integration
- ✅ Real-time transaction logging
- ✅ Automatic 2PM daily summaries
- ✅ Fixed auto-navigation issues
- ✅ Improved terminal output (clean, important events only)
- ✅ Enhanced RFID debouncing (5 seconds)
- ✅ Fixed approve/deny duplicate logging
- ✅ Improved reset functionality
- ✅ Better error handling throughout

**v1.0.0** (January 2026)

- Initial release
- Core features: RFID scanning, eligibility checking, daily limits
- Encryption for student data
- SQLite and MySQL support
- Admin dashboard
- Sample data generation

---

## 🚧 Future Enhancements & Next Steps

### High Priority

1. **CSV Student Import Tool**
   - Bulk import students from spreadsheet
   - Validation and error checking
   - Map RFID cards during import

2. **Enhanced Reporting**
   - Weekly/monthly summary reports
   - Student usage patterns
   - Peak time analysis
   - Export capabilities

3. **Multi-Language Support**
   - Spanish interface option
   - Configurable language per station

4. **Mobile App for Students**
   - Check meal balance
   - View transaction history
   - Receive notifications

### Medium Priority

5. **Google Sheets Data Archiving**
   - Monthly archiving of old data
   - Keep current sheets clean
   - Maintain historical records

6. **Advanced Analytics Dashboard**
   - Real-time graphs and charts
   - Trend analysis
   - Predictive analytics for meal planning

7. **Email/SMS Notifications**
   - Daily summary to administrators
   - Alert when student runs out of meals
   - System error notifications

8. **Facial Recognition Backup**
   - Alternative to RFID when card is lost
   - Photo capture on first scan
   - Privacy-compliant implementation

### Low Priority

9. **Parent Portal**
   - View student meal usage
   - Add funds to meal plan
   - Transaction history

10. **Integration with Student Information System**
    - Sync student data automatically
    - Update meal plans based on registration
    - Handle transfers/graduations

11. **Real-time Multi-Station Dashboard**
    - See activity across all stations
    - Monitor system health
    - Coordinate meal service

12. **Advanced MUNDOWARE Integration**
    - Bidirectional data sync
    - Automatic transaction completion
    - Error reconciliation

### Technical Improvements

13. **Automated Testing**
    - Unit tests for core functions
    - Integration tests for workflows
    - Performance testing

14. **Docker Containerization**
    - Easy deployment
    - Consistent environments
    - Simplified updates

15. **Backup & Recovery System**
    - Automated daily backups
    - Point-in-time recovery
    - Disaster recovery plan

16. **Performance Optimization**
    - Database query optimization
    - Caching for frequent lookups
    - Faster card detection

---

## 📚 Additional Documentation

- `docs/google_apps_script.js` - Google Sheets integration script
- `docs/TROUBLESHOOTING.md` - Detailed troubleshooting guide
- `docs/API.md` - API endpoint documentation
- `docs/DATABASE.md` - Database schema and models
- `setup_guide.md` - Detailed setup instructions

---

## 🎓 Training Resources

### For Cashiers

- Quick reference card (one-page guide)
- Video tutorial: Basic operations
- What to do when system is down
- Manual override procedures

### For Administrators

- Admin dashboard guide
- Report generation
- Student management
- System monitoring

### For IT Staff

- Installation and configuration
- Troubleshooting guide
- Database maintenance
- Security best practices

---

## ⚡ Quick Start Checklist

- [ ] Install Python 3.9+
- [ ] Create virtual environment
- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Generate encryption key
- [ ] Configure `.env` file
- [ ] Set up Google Sheets (create sheet, deploy script)
- [ ] Initialize database with sample data
- [ ] Test RFID reader
- [ ] Start system (`python main.py`)
- [ ] Access touchscreen interface
- [ ] Test card scan → approve flow
- [ ] Verify Google Sheets logging
- [ ] Check admin dashboard
- [ ] Test manual reset
- [ ] Review logs

---

## 💡 Tips for Success

1. **Test thoroughly before production** - Use sample data and test all scenarios
2. **Train cashiers properly** - Hands-on practice is essential
3. **Have a backup plan** - Paper logs for system outages
4. **Monitor Google Sheets regularly** - Verify data is being logged correctly
5. **Keep encryption key secure** - Multiple backups in secure locations
6. **Regular database backups** - Automated daily backups recommended
7. **Review transaction logs** - Check for anomalies weekly
8. **Plan for scale** - Consider MySQL for multiple stations
9. **Document customizations** - Keep notes on any changes made
10. **Stay updated** - Check for system updates and improvements

---

**For the latest updates, visit:** [Project Repository URL]
