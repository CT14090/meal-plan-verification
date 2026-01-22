"""
Database Models - SQLAlchemy ORM models for all database tables
Supports both SQLite and MySQL through SQLAlchemy
"""

from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from config.encryption import get_encryption_manager

db = SQLAlchemy()

class Student(db.Model):
    """
    Student Master Data
    Stores student information with encrypted sensitive fields
    """
    __tablename__ = 'students'
    
    student_id = db.Column(db.String(20), primary_key=True)
    card_rfid_uid = db.Column(db.String(200), unique=True, nullable=False)  # Encrypted
    student_name = db.Column(db.String(200), nullable=False)  # Encrypted
    grade_level = db.Column(db.Integer)
    meal_plan_type = db.Column(db.String(50), nullable=False)
    daily_meal_limit = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Active')
    photo_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    daily_usage = db.relationship('DailyMealUsage', backref='student', lazy=True, cascade='all, delete-orphan')
    transactions = db.relationship('MealTransaction', backref='student', lazy=True)
    
    def __repr__(self):
        return f"<Student {self.student_id}>"
    
    def to_dict(self, decrypt=True):
        """
        Convert to dictionary
        
        Args:
            decrypt: If True, decrypt sensitive fields
        """
        em = get_encryption_manager()
        
        data = {
            'student_id': self.student_id,
            'card_rfid_uid': self.card_rfid_uid,
            'student_name': self.student_name,
            'grade_level': self.grade_level,
            'meal_plan_type': self.meal_plan_type,
            'daily_meal_limit': self.daily_meal_limit,
            'status': self.status,
            'photo_url': self.photo_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if decrypt:
            try:
                data['student_name'] = em.decrypt(self.student_name)
                data['card_rfid_uid'] = em.decrypt(self.card_rfid_uid)
            except:
                pass  # If decryption fails, return as-is
        
        return data
    
    @staticmethod
    def create_encrypted(student_id, card_rfid_uid, student_name, grade_level, 
                        meal_plan_type, daily_meal_limit, status='Active', photo_url=None):
        """
        Create new student with encrypted fields
        
        Args:
            All student fields (plaintext)
        
        Returns:
            Student object with encrypted sensitive fields
        """
        em = get_encryption_manager()
        
        student = Student(
            student_id=student_id,
            card_rfid_uid=em.encrypt(card_rfid_uid),
            student_name=em.encrypt(student_name),
            grade_level=grade_level,
            meal_plan_type=meal_plan_type,
            daily_meal_limit=daily_meal_limit,
            status=status,
            photo_url=photo_url
        )
        
        return student


class DailyMealUsage(db.Model):
    """
    Daily Meal Usage Tracking
    Tracks how many meals each student has used today
    Resets at midnight
    """
    __tablename__ = 'daily_meal_usage'
    
    usage_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), db.ForeignKey('students.student_id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    meals_used_today = db.Column(db.Integer, default=0)
    last_meal_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint: one record per student per day
    __table_args__ = (
        db.UniqueConstraint('student_id', 'date', name='unique_student_date'),
    )
    
    def __repr__(self):
        return f"<DailyMealUsage {self.student_id} - {self.date}>"
    
    def to_dict(self):
        return {
            'usage_id': self.usage_id,
            'student_id': self.student_id,
            'date': self.date.isoformat(),
            'meals_used_today': self.meals_used_today,
            'last_meal_time': self.last_meal_time.isoformat() if self.last_meal_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def has_meals_remaining(self, daily_limit):
        """Check if student has meals remaining today"""
        return self.meals_used_today < daily_limit
    
    def increment_usage(self):
        """Increment meal count and update timestamp"""
        self.meals_used_today += 1
        self.last_meal_time = datetime.utcnow()


class MealTransaction(db.Model):
    """
    Meal Transaction Log
    Permanent audit trail of all meal transactions
    """
    __tablename__ = 'meal_transactions'
    
    transaction_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), db.ForeignKey('students.student_id'), nullable=False)
    student_name = db.Column(db.String(200), nullable=False)  # Encrypted
    meal_plan_type = db.Column(db.String(50), nullable=False)
    meal_type = db.Column(db.String(20))  # Breakfast, Lunch, Snack
    transaction_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    cashier_station = db.Column(db.String(20))
    cashier_id = db.Column(db.String(50))
    status = db.Column(db.String(20), nullable=False)  # Approved, Denied, Error
    denied_reason = db.Column(db.String(200))
    
    def __repr__(self):
        return f"<MealTransaction {self.transaction_id} - {self.status}>"
    
    def to_dict(self, decrypt=True):
        """Convert to dictionary with optional decryption"""
        em = get_encryption_manager()
        
        data = {
            'transaction_id': self.transaction_id,
            'student_id': self.student_id,
            'student_name': self.student_name,
            'meal_plan_type': self.meal_plan_type,
            'meal_type': self.meal_type,
            'transaction_timestamp': self.transaction_timestamp.isoformat() if self.transaction_timestamp else None,
            'cashier_station': self.cashier_station,
            'cashier_id': self.cashier_id,
            'status': self.status,
            'denied_reason': self.denied_reason
        }
        
        if decrypt:
            try:
                data['student_name'] = em.decrypt(self.student_name)
            except:
                pass
        
        return data
    
    @staticmethod
    def create_encrypted(student_id, student_name, meal_plan_type, meal_type,
                        cashier_station, cashier_id, status, denied_reason=None):
        """Create transaction with encrypted name"""
        em = get_encryption_manager()
        
        transaction = MealTransaction(
            student_id=student_id,
            student_name=em.encrypt(student_name),
            meal_plan_type=meal_plan_type,
            meal_type=meal_type,
            cashier_station=cashier_station,
            cashier_id=cashier_id,
            status=status,
            denied_reason=denied_reason
        )
        
        return transaction


class MundowareStudentLookup(db.Model):
    """
    MUNDOWARE Shared Lookup Table
    Written by this system, read by MUNDOWARE
    Contains current student awaiting transaction
    """
    __tablename__ = 'mundoware_student_lookup'
    
    lookup_id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.String(20), nullable=False)
    student_id = db.Column(db.String(20), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)  # Plaintext for MUNDOWARE
    meal_plan_type = db.Column(db.String(50), nullable=False)
    eligible = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint: one active lookup per station
    __table_args__ = (
        db.UniqueConstraint('station_id', name='unique_station'),
    )
    
    def __repr__(self):
        return f"<MundowareStudentLookup {self.station_id} - {self.student_id}>"
    
    def to_dict(self):
        return {
            'lookup_id': self.lookup_id,
            'station_id': self.station_id,
            'student_id': self.student_id,
            'student_name': self.student_name,
            'meal_plan_type': self.meal_plan_type,
            'eligible': self.eligible,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
    return db