# Meal Plan Verification System

Automated cafeteria meal plan verification system using RFID cards, touchscreen displays, and daily usage tracking.

---

## 🎯 Project Overview

**Purpose:** Eliminate manual student name entry, enforce daily meal limits, and integrate with MUNDOWARE POS system.

**Key Features:**

- ✅ RFID card scanning for instant student identification
- ✅ Real-time eligibility verification (daily meal limits)
- ✅ Dual-screen cashier workflow (MUNDOWARE + verification touchscreen)
- ✅ Encrypted student data (names & card UIDs)
- ✅ Automatic midnight usage reset
- ✅ Transaction logging and reporting
- ✅ Manual override options for cashiers
- ✅ Admin dashboard with analytics

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
- Database server (if using shared MySQL database)

---

## 🚀 Installation Guide

### Step 1: Clone or Download Repository

```bash
# Clone repository (if using Git)
git clone https://github.com/your-school/meal-plan-verification.git
cd meal-plan-verification

# OR download and extract ZIP file
```

### Step 2: Install Python Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

**If you encounter errors:**

- Windows: Install Visual C++ Build Tools for `pyscard`
- Linux: `sudo apt-get install pcscd libpcsclite-dev swig`
- macOS: `brew install swig`

### Step 3: Generate Encryption Key

```bash
# Generate encryption key (KEEP THIS SECRET!)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Save this key securely!** You'll need it in the next step.

### Step 4: Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your settings
# Windows: notepad .env
# Linux/Mac: nano .env
```

**Required Configuration:**

```bash
# Database (start with SQLite for simplicity)
DATABASE_TYPE=sqlite
DATABASE_PATH=meal_plan.db

# CRITICAL: Paste your encryption key here
ENCRYPTION_KEY=YOUR_GENERATED_KEY_FROM_STEP_3

# Flask settings
FLASK_SECRET_KEY=your-random-secret-key-here
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# Station identification
STATION_ID=Station_1  # Change to Station_2, Station_3 for other cashiers
CASHIER_ID=CASHIER_01

# RFID Reader
RFID_ENABLED=True

# MUNDOWARE Integration (configure after testing)
MUNDOWARE_ENABLED=False  # Set to True when ready to connect
```

### Step 5: Initialize Database

```bash
# Start Python shell
python

# Run database initialization
>>> from web.app import create_app
>>> from database.sample_data import populate_database
>>> app = create_app()
>>> with app.app_context():
...     populate_database(50, clear_existing=False)
>>> exit()
```

This creates 50 sample students for testing.

### Step 6: Test RFID Reader (Optional but Recommended)

```bash
# Test ACR122U connection
python services/rfid_reader.py

# You should see:
# - "Using reader: ACS ACR122U..."
# - Wave a MIFARE card near reader
# - Card UID should display
# - Press Ctrl+C to stop
```

### Step 7: Start the System

```bash
# Start all services
python main.py
```

**You should see:**

```
====================================================
MEAL PLAN VERIFICATION SYSTEM
====================================================

Station: Station_1
Database: sqlite

Touchscreen: http://0.0.0.0:5000/
Admin Panel: http://0.0.0.0:5000/admin

System ready! Press Ctrl+C to stop
====================================================
```

### Step 8: Access Interfaces

**Touchscreen Interface** (for cashiers):

- Open browser on touchscreen PC
- Navigate to: `http://localhost:5000/`
- **Optional:** Set browser to fullscreen (F11)

**Admin Dashboard**:

- Navigate to: `http://localhost:5000/admin`
- View statistics, manage students, export reports

---

## 🖥️ Multi-Station Setup

### Station 1 Configuration

```bash
# .env file for Station 1
STATION_ID=Station_1
CASHIER_ID=CASHIER_01
FLASK_PORT=5000
```

### Station 2 Configuration

```bash
# .env file for Station 2
STATION_ID=Station_2
CASHIER_ID=CASHIER_02
FLASK_PORT=5001  # Different port if on same machine
```

### Station 3 Configuration

```bash
# .env file for Station 3
STATION_ID=Station_3
CASHIER_ID=CASHIER_03
FLASK_PORT=5002
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

1. Go to `http://localhost:5000/admin`
2. Click "Add Student"
3. Scan student card to get UID
4. Enter student details
5. Save

**Method 3: Manual Database Entry**

```python
python
>>> from web.app import create_app
>>> from database.db_manager import get_db_manager
>>> app = create_app()
>>> with app.app_context():
...     dm = get_db_manager()
...     dm.add_student(
...         student_id='12345',
...         card_rfid_uid='04A3B2C145',  # Get from RFID scan
...         student_name='John Smith',
...         grade_level=10,
...         meal_plan_type='Premium',
...         daily_meal_limit=2,
...         status='Active'
...     )
```

### Exporting Student Data

```bash
# Export all students to CSV
# Visit: http://localhost:5000/admin/export-students-csv
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

### Option B: Keyboard Automation (Fallback)

If MUNDOWARE cannot read from shared table, the system can:

- Automatically type student information into MUNDOWARE
- Requires window focus on MUNDOWARE terminal

Enable in `services/mundoware_sync.py` (code provided but disabled by default)

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
   - Students scan cards
   - Cashier verifies eligibility on touchscreen
   - Clicks APPROVE or DENY
   - Completes transaction in MUNDOWARE

3. **Manual Overrides:**
   - If card doesn't work: Click "Manual Entry"
   - Type student ID
   - Continue normally

### Midnight Reset

**Automatic:** System resets all daily meal counts at midnight.

**Manual Reset** (if needed):

```bash
# Via admin dashboard
http://localhost:5000/admin -> "Trigger Daily Reset" button

# OR via Python
python
>>> from services.scheduler import get_scheduler_service
>>> scheduler = get_scheduler_service()
>>> scheduler.trigger_reset_now()
```

### Weekly Maintenance

- **Log Cleanup:** System auto-deletes logs older than 30 days
- **Database Vacuum:** SQLite databases optimized weekly
- **Review Reports:** Check admin dashboard for anomalies

---

## 📊 Reports & Analytics

### Daily Statistics

Access via admin dashboard:

- Total meals served today
- Approved vs denied transactions
- Breakdown by meal type (breakfast, lunch, snack)
- Breakdown by meal plan type (basic, premium, unlimited)

### Transaction Export

```bash
# Export transactions to CSV
curl http://localhost:5000/admin/transactions > transactions.csv
```

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

### Database Connection Failed

**Symptoms:** "Error connecting to database"

**Solutions:**

1. SQLite: Check file path in `.env`
2. MySQL: Verify host/port/credentials
3. Test connection:
   ```bash
   python
   >>> from config.settings import config
   >>> print(config.SQLALCHEMY_DATABASE_URI)
   ```

### Touchscreen Not Responsive

**Solutions:**

1. Calibrate touchscreen (Windows Settings > Devices > Touchscreen)
2. Check USB-C connection
3. Try different browser (Chrome recommended)
4. Verify touch drivers installed

### Encryption Key Error

**Symptoms:** "Invalid encryption key format"

**Solutions:**

1. Verify key copied correctly from Step 3
2. No extra spaces or quotes in `.env` file
3. Regenerate key and update all stations

### Student Card Not Found

**Solutions:**

1. Verify card UID in database:
   ```bash
   python services/rfid_reader.py  # Scan card to get UID
   ```
2. Check student exists in database
3. Use "Manual Entry" as fallback

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
3. If no backup:
   ```bash
   # Rebuild from transaction logs
   python scripts/rebuild_database.py logs/transactions.log
   ```

### Lost Encryption Key

**⚠️ WARNING:** Data is unrecoverable without key.

**Prevention:**

- Backup key in password manager
- IT department offline backup
- Test backup restoration monthly

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

---

## 🔄 Version History

**v1.0.0** (January 2026)

- Initial release
- Core features: RFID scanning, eligibility checking, daily limits
- Encryption for student data
- SQLite and MySQL support
- Admin dashboard
- Sample data generation

---

## 🚧 Future Enhancements

**Planned Features:**

- Mobile app for students (check meal status)
- Email/SMS notifications
- Real-time multi-station dashboard
- Facial recognition as RFID backup
- Parent portal (view student meal usage)
- Integration with student information system
- Advanced analytics and reporting
