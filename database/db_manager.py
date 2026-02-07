"""
Database Manager - High-level database operations
UPDATED: Auto meal type detection based on time
"""

from datetime import date, datetime
from sqlalchemy import and_
from config.settings import config
from config.encryption import get_encryption_manager
from database.models import db, Student, DailyMealUsage, MealTransaction, MundowareStudentLookup
from utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """Manages all database operations"""
    
    def __init__(self):
        self.em = get_encryption_manager()
    
    def find_student_by_rfid(self, card_uid):
        try:
            students = Student.query.all()
            for student in students:
                try:
                    decrypted_uid = self.em.decrypt(student.card_rfid_uid)
                    if decrypted_uid == card_uid:
                        logger.info(f"Student found for RFID: {card_uid[:8]}***")
                        return student
                except:
                    continue
            logger.warning(f"No student found for RFID: {card_uid[:8]}***")
            return None
        except Exception as e:
            logger.error(f"Error finding student by RFID: {e}")
            return None
            
    def find_student_by_id(self, student_id):
        try:
            student = Student.query.filter_by(student_id=student_id).first()
            if student:
                logger.info(f"Student found: {student_id}")
            else:
                logger.warning(f"No student found: {student_id}")
            return student
        except Exception as e:
            logger.error(f"Error finding student by ID: {e}")
            return None
    
    def get_all_students(self, active_only=True):
        try:
            if active_only:
                students = Student.query.filter_by(status='Active').all()
            else:
                students = Student.query.all()
            return students
        except Exception as e:
            logger.error(f"Error getting all students: {e}")
            return []
    
    def add_student(self, student_id, card_rfid_uid, student_name, grade_level,
                   meal_plan_type, daily_meal_limit, status='Active', photo_filename=None):
        try:
            student = Student.create_encrypted(
                student_id=student_id,
                card_rfid_uid=card_rfid_uid,
                student_name=student_name,
                grade_level=grade_level,
                meal_plan_type=meal_plan_type,
                daily_meal_limit=daily_meal_limit,
                status=status,
                photo_filename=photo_filename
            )
            db.session.add(student)
            db.session.commit()
            logger.info(f"Student added: {student_id}")
            return student
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding student: {e}")
            return None
    
    def update_student(self, student_id, **kwargs):
        try:
            student = Student.query.filter_by(student_id=student_id).first()
            if not student:
                logger.warning(f"Cannot update - student not found: {student_id}")
                return None
            
            if 'card_rfid_uid' in kwargs:
                student.card_rfid_uid = self.em.encrypt(kwargs['card_rfid_uid'])
            if 'student_name' in kwargs:
                student.student_name = self.em.encrypt(kwargs['student_name'])
            
            for field in ['grade_level', 'meal_plan_type', 'daily_meal_limit', 'status', 'photo_filename']:
                if field in kwargs:
                    setattr(student, field, kwargs[field])
            
            student.updated_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"Student updated: {student_id}")
            return student
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating student: {e}")
            return None
    
    def delete_student(self, student_id):
        try:
            student = Student.query.filter_by(student_id=student_id).first()
            if not student:
                return False
            student.status = 'Inactive'
            db.session.commit()
            logger.info(f"Student deactivated: {student_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deactivating student: {e}")
            return False
    
    def get_today_usage(self, student_id):
        try:
            today = date.today()
            usage = DailyMealUsage.query.filter_by(student_id=student_id, date=today).first()
            if not usage:
                usage = DailyMealUsage(
                    student_id=student_id,
                    date=today,
                    meals_used_today=0,
                    breakfast_used=0,
                    lunch_used=0,
                    snack_used=0
                )
                db.session.add(usage)
                db.session.commit()
                logger.info(f"Created new daily usage record for {student_id}")
            return usage
        except Exception as e:
            logger.error(f"Error getting today's usage: {e}")
            return None
    
    def auto_detect_meal_type(self):
        """Auto-detect meal type based on current time in Panama timezone"""
        try:
            import pytz
            from datetime import datetime as dt
            
            panama_tz = pytz.timezone('America/Panama')
            panama_time = dt.now(panama_tz)
            current_hour = panama_time.hour
            current_minute = panama_time.minute
            
            # Log the time for debugging
            print(f"⏰ Panama time: {current_hour:02d}:{current_minute:02d}")
            
            # School meal times (24-hour format):
            # Breakfast: 6:00 AM - 10:00 AM
            # Lunch: 10:00 AM - 2:00 PM
            # Snack: 2:00 PM - 5:00 PM
            
            if 6 <= current_hour < 10:
                return 'Breakfast'
            elif 10 <= current_hour < 14:
                return 'Lunch'
            elif 14 <= current_hour < 17:
                return 'Snack'
            else:
                return None
        except Exception as e:
            print(f"⚠️  Timezone error: {e}, using system time")
            from datetime import datetime as dt
            current_hour = dt.now().hour
            
            if 6 <= current_hour < 10:
                return 'Breakfast'
            elif 10 <= current_hour < 14:
                return 'Lunch'
            elif 14 <= current_hour < 17:
                return 'Snack'
            else:
                return None

    def check_eligibility(self, student, meal_type=None):
        try:
            # AUTO-DETECT meal type if not provided
            if meal_type is None:
                meal_type = self.auto_detect_meal_type()
                if meal_type is None:
                    return {
                        'eligible': False,
                        'reason': 'No meals served at this time',
                        'meals_used': 0,
                        'meals_remaining': 0,
                        'meal_type_status': {},
                        'detected_meal_type': None
                    }
            
            if student.status != 'Active':
                return {
                    'eligible': False,
                    'reason': config.DENIAL_REASONS['INACTIVE'],
                    'meals_used': 0,
                    'meals_remaining': 0,
                    'meal_type_status': {},
                    'detected_meal_type': meal_type
                }
            # Check Friday meal plan logic
            # Friday plans (FridayBasic, FridayPlus, FridayPremium) = Work Mon-Fri (all 5 days)
            # Regular plans (Basic, Plus, Premium, Unlimited) = Work Mon-Thu only (NO Friday)
            
            try:
                import pytz
                panama_tz = pytz.timezone('America/Panama')
                panama_time = datetime.now(panama_tz)
                today_weekday = panama_time.weekday()
            except:
                today_weekday = date.today().weekday()
            
            is_friday = (today_weekday == 4)  # Friday = 4
            is_friday_plan = student.meal_plan_type.startswith('Friday')
            
            # Day check debug removed
            
            # Regular plans are NOT valid on Fridays
            if not is_friday_plan and is_friday:
                return {
                    'eligible': False,
                    'reason': 'Regular meal plans not valid on Fridays',
                    'meals_used': 0,
                    'meals_remaining': 0,
                    'meal_type_status': {},
                    'detected_meal_type': meal_type
                }
            
            # Friday plans work ALL days (Mon-Fri)
            # Regular plans work Mon-Thu only
            
            # Check meal type allowed
            allowed_types = config.MEAL_PLAN_ALLOWED_TYPES.get(student.meal_plan_type, [])
            if meal_type not in allowed_types:
                return {
                    'eligible': False,
                    'reason': config.DENIAL_REASONS['MEAL_TYPE_NOT_ALLOWED'],
                    'meals_used': 0,
                    'meals_remaining': 0,
                    'meal_type_status': {},
                    'detected_meal_type': meal_type
                }
            
            usage = self.get_today_usage(student.student_id)
            if not usage:
                return {
                    'eligible': False,
                    'reason': 'Error checking usage',
                    'meals_used': 0,
                    'meals_remaining': 0,
                    'meal_type_status': {},
                    'detected_meal_type': meal_type
                }
            
            # Check if meal type already used
            if not usage.has_meal_type_available(meal_type):
                return {
                    'eligible': False,
                    'reason': config.DENIAL_REASONS['MEAL_TYPE_ALREADY_USED'],
                    'meals_used': usage.meals_used_today,
                    'meals_remaining': 0,
                    'meal_type_status': {
                        'breakfast_used': usage.breakfast_used,
                        'lunch_used': usage.lunch_used,
                        'snack_used': usage.snack_used
                    },
                    'detected_meal_type': meal_type
                }
            
            # Check daily limit
            meals_used = usage.meals_used_today
            daily_limit = student.daily_meal_limit
            meals_remaining = max(0, daily_limit - meals_used)
            
            if meals_used >= daily_limit:
                return {
                    'eligible': False,
                    'reason': config.DENIAL_REASONS['LIMIT_REACHED'],
                    'meals_used': meals_used,
                    'meals_remaining': 0,
                    'last_meal_time': usage.last_meal_time,
                    'meal_type_status': {
                        'breakfast_used': usage.breakfast_used,
                        'lunch_used': usage.lunch_used,
                        'snack_used': usage.snack_used
                    },
                    'detected_meal_type': meal_type
                }
            
            return {
                'eligible': True,
                'reason': None,
                'meals_used': meals_used,
                'meals_remaining': meals_remaining,
                'last_meal_time': usage.last_meal_time,
                'meal_type_status': {
                    'breakfast_used': usage.breakfast_used,
                    'lunch_used': usage.lunch_used,
                    'snack_used': usage.snack_used
                },
                'detected_meal_type': meal_type
            }
        
        except Exception as e:
            logger.error(f"Error checking eligibility: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'eligible': False,
                'reason': 'System error',
                'meals_used': 0,
                'meals_remaining': 0,
                'meal_type_status': {},
                'detected_meal_type': meal_type
            }
    
    def increment_meal_usage(self, student_id, meal_type=None):
        try:
            if meal_type is None:
                meal_type = self.auto_detect_meal_type()
            
            usage = self.get_today_usage(student_id)
            if usage:
                usage.increment_usage(meal_type)
                db.session.commit()
                logger.info(f"Incremented {meal_type} usage for {student_id}: {usage.meals_used_today} total")
                return True
            return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error incrementing meal usage: {e}")
            return False
    
    def reset_daily_usage(self):
        try:
            yesterday = date.today()
            deleted = DailyMealUsage.query.filter(DailyMealUsage.date < yesterday).delete()
            db.session.commit()
            logger.info(f"Daily usage reset complete. Deleted {deleted} old records.")
            return deleted
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error resetting daily usage: {e}")
            return 0
    
    def log_transaction(self, student_id, student_name, meal_plan_type, meal_type,
                       status, denied_reason=None):
        try:
            transaction = MealTransaction.create_encrypted(
                student_id=student_id,
                student_name=student_name,
                meal_plan_type=meal_plan_type,
                meal_type=meal_type,
                cashier_station=config.STATION_ID,
                cashier_id=config.CASHIER_ID,
                status=status,
                denied_reason=denied_reason
            )
            db.session.add(transaction)
            db.session.commit()
            logger.info(f"Transaction logged: {student_id} - {status}")
            return transaction
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error logging transaction: {e}")
            return None
    
    def get_recent_transactions(self, limit=50):
        try:
            transactions = MealTransaction.query.order_by(
                MealTransaction.transaction_timestamp.desc()
            ).limit(limit).all()
            return transactions
        except Exception as e:
            logger.error(f"Error getting recent transactions: {e}")
            return []
    
    def get_daily_stats(self):
        try:
            today = date.today()
            today_start = datetime.combine(today, datetime.min.time())
            
            total = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start
            ).count()
            
            approved = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start,
                MealTransaction.status == config.STATUS_APPROVED
            ).count()
            
            denied = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start,
                MealTransaction.status == config.STATUS_DENIED
            ).count()
            
            breakfast = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start,
                MealTransaction.meal_type == 'Breakfast',
                MealTransaction.status == config.STATUS_APPROVED
            ).count()
            
            lunch = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start,
                MealTransaction.meal_type == 'Lunch',
                MealTransaction.status == config.STATUS_APPROVED
            ).count()
            
            snack = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp >= today_start,
                MealTransaction.meal_type == 'Snack',
                MealTransaction.status == config.STATUS_APPROVED
            ).count()
            
            return {
                'total': total,
                'approved': approved,
                'denied': denied,
                'breakfast': breakfast,
                'lunch': lunch,
                'snack': snack
            }
        except Exception as e:
            logger.error(f"Error getting daily stats: {e}")
            return {
                'total': 0,
                'approved': 0,
                'denied': 0,
                'breakfast': 0,
                'lunch': 0,
                'snack': 0
            }
    
    def update_mundoware_lookup(self, student, eligible):
        try:
            student_name = self.em.decrypt(student.student_name)
            MundowareStudentLookup.query.filter_by(station_id=config.STATION_ID).delete()
            
            lookup = MundowareStudentLookup(
                station_id=config.STATION_ID,
                student_id=student.student_id,
                student_name=student_name,
                meal_plan_type=student.meal_plan_type,
                eligible=eligible
            )
            db.session.add(lookup)
            db.session.commit()
            logger.info(f"✅ MUNDOWARE lookup created: {student.student_id} (eligible: {eligible})")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"❌ Error updating MUNDOWARE lookup: {e}")
            return False
    
    def clear_mundoware_lookup(self):
        try:
            MundowareStudentLookup.query.filter_by(station_id=config.STATION_ID).delete()
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error clearing MUNDOWARE lookup: {e}")
            return False


_db_manager = None

def get_db_manager():
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
