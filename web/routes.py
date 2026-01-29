"""
Flask Routes - API endpoints and page routes
Handles all touchscreen interactions and admin functions
"""

from flask import Blueprint, render_template, request, jsonify, send_file
from datetime import datetime, date
import csv
import io
from config.settings import config
from config.encryption import get_encryption_manager
from database.db_manager import get_db_manager
from database.models import db, Student, MealTransaction
from database.sample_data import populate_database, export_student_cards_csv
from services.scheduler import get_scheduler_service
from utils.logger import get_logger, log_transaction

logger = get_logger(__name__)
em = get_encryption_manager()
db_manager = get_db_manager()

# Create blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)
admin_bp = Blueprint('admin', __name__)

# ==================== MAIN TOUCHSCREEN ROUTES ====================

@main_bp.route('/')
def index():
    """Main touchscreen interface - waiting for card scan"""
    stats = db_manager.get_daily_stats()
    return render_template('waiting.html', stats=stats)

@main_bp.route('/manual')
def manual_entry():
    """Manual student ID entry (fallback when card fails)"""
    return render_template('manual_entry.html')

@main_bp.route('/student-info')
def student_info():
    """Student info display (for RFID scans and manual entry)"""
    return render_template('student_info.html')

@main_bp.route('/approved')
def approved():
    """Meal approved confirmation"""
    return render_template('approved.html')

@main_bp.route('/denied')
def denied():
    """Meal denied screen"""
    return render_template('denied.html')

# ==================== API ENDPOINTS ====================

@api_bp.route('/scan-card', methods=['POST'])
def scan_card():
    """
    Handle card scan from RFID reader
    
    Request JSON:
        {
            "card_uid": "04A3B2C145"
        }
    
    Response JSON:
        {
            "success": true,
            "student": {...},
            "eligibility": {...}
        }
    """
    try:
        data = request.get_json()
        card_uid = data.get('card_uid', '').strip().upper()
        
        if not card_uid:
            return jsonify({
                'success': False,
                'error': 'No card UID provided'
            }), 400
        
        logger.info(f"Card scanned: {card_uid[:8]}***")
        
        # Find student
        student = db_manager.find_student_by_rfid(card_uid)
        
        if not student:
            logger.warning(f"Card not found: {card_uid}")
            return jsonify({
                'success': False,
                'error': 'card_not_found',
                'message': config.DENIAL_REASONS['CARD_NOT_FOUND']
            }), 404
        
        # Check eligibility
        eligibility = db_manager.check_eligibility(student)
        
        # Decrypt student data for display
        student_data = student.to_dict(decrypt=True)
        
        # Update MUNDOWARE lookup table
        db_manager.update_mundoware_lookup(student, eligibility['eligible'])
        
        return jsonify({
            'success': True,
            'student': student_data,
            'eligibility': eligibility
        })
    
    except Exception as e:
        logger.error(f"Error processing card scan: {e}")
        return jsonify({
            'success': False,
            'error': 'system_error',
            'message': str(e)
        }), 500

@api_bp.route('/manual-lookup', methods=['POST'])
def manual_lookup():
    """
    Manual student lookup by ID
    
    Request JSON:
        {
            "student_id": "12345"
        }
    """
    try:
        data = request.get_json()
        student_id = data.get('student_id', '').strip()
        
        if not student_id:
            return jsonify({
                'success': False,
                'error': 'No student ID provided'
            }), 400
        
        logger.info(f"Manual lookup: {student_id}")
        
        # Find student
        student = db_manager.find_student_by_id(student_id)
        
        if not student:
            return jsonify({
                'success': False,
                'error': 'student_not_found',
                'message': 'Student ID not found'
            }), 404
        
        # Check eligibility
        eligibility = db_manager.check_eligibility(student)
        
        # Decrypt student data
        student_data = student.to_dict(decrypt=True)
        
        # Update MUNDOWARE lookup
        db_manager.update_mundoware_lookup(student, eligibility['eligible'])
        
        return jsonify({
            'success': True,
            'student': student_data,
            'eligibility': eligibility
        })
    
    except Exception as e:
        logger.error(f"Error in manual lookup: {e}")
        return jsonify({
            'success': False,
            'error': 'system_error',
            'message': str(e)
        }), 500

@api_bp.route('/approve-meal', methods=['POST'])
def approve_meal():
    """
    Approve meal transaction
    
    Request JSON:
        {
            "student_id": "12345",
            "meal_type": "Lunch"  (optional)
        }
    """
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        meal_type = data.get('meal_type')  # May be None if not selected yet
        
        if not student_id:
            return jsonify({
                'success': False,
                'error': 'No student ID provided'
            }), 400
        
        # Get student
        student = db_manager.find_student_by_id(student_id)
        if not student:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404
        
        # Decrypt student name for logging
        student_name = em.decrypt(student.student_name)
        
        # Double-check eligibility
        eligibility = db_manager.check_eligibility(student)
        if not eligibility['eligible']:
            logger.warning(f"Approval attempted for ineligible student: {student_id}")
            
            # Log denied transaction
            db_manager.log_transaction(
                student_id=student_id,
                student_name=student_name,
                meal_plan_type=student.meal_plan_type,
                meal_type=meal_type,
                status=config.STATUS_DENIED,
                denied_reason=eligibility['reason']
            )
            
            return jsonify({
                'success': False,
                'error': 'not_eligible',
                'message': eligibility['reason']
            }), 403
        
        # Increment meal usage
        success = db_manager.increment_meal_usage(student_id)
        
        if not success:
            logger.error(f"Failed to increment meal usage for {student_id}")
            return jsonify({
                'success': False,
                'error': 'Failed to update usage'
            }), 500
        
        # Log approved transaction
        db_manager.log_transaction(
            student_id=student_id,
            student_name=student_name,
            meal_plan_type=student.meal_plan_type,
            meal_type=meal_type,
            status=config.STATUS_APPROVED
        )
        
        # Log to transaction file
        log_transaction(student_id, student_name, meal_type or 'Unknown', 'Approved')
        
        logger.info(f"Meal approved: {student_id} - {meal_type}")
        
        # Get updated usage
        updated_eligibility = db_manager.check_eligibility(student)
        
        return jsonify({
            'success': True,
            'message': 'Meal approved',
            'updated_eligibility': updated_eligibility
        })
    
    except Exception as e:
        logger.error(f"Error approving meal: {e}")
        return jsonify({
            'success': False,
            'error': 'system_error',
            'message': str(e)
        }), 500

@api_bp.route('/deny-meal', methods=['POST'])
def deny_meal():
    """
    Deny meal transaction (manual override by cashier)
    
    Request JSON:
        {
            "student_id": "12345",
            "reason": "Manual denial reason"
        }
    """
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        reason = data.get('reason', config.DENIAL_REASONS['MANUAL_OVERRIDE'])
        
        if not student_id:
            return jsonify({
                'success': False,
                'error': 'No student ID provided'
            }), 400
        
        # Get student
        student = db_manager.find_student_by_id(student_id)
        if not student:
            return jsonify({
                'success': False,
                'error': 'Student not found'
            }), 404
        
        student_name = em.decrypt(student.student_name)
        
        # Log denied transaction
        db_manager.log_transaction(
            student_id=student_id,
            student_name=student_name,
            meal_plan_type=student.meal_plan_type,
            meal_type=None,
            status=config.STATUS_DENIED,
            denied_reason=reason
        )
        
        log_transaction(student_id, student_name, 'N/A', 'Denied', reason)
        logger.info(f"Meal denied: {student_id} - {reason}")
        
        # Clear MUNDOWARE lookup
        db_manager.clear_mundoware_lookup()
        
        return jsonify({
            'success': True,
            'message': 'Meal denied'
        })
    
    except Exception as e:
        logger.error(f"Error denying meal: {e}")
        return jsonify({
            'success': False,
            'error': 'system_error',
            'message': str(e)
        }), 500

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get current daily statistics"""
    try:
        stats = db_manager.get_daily_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== ADMIN ROUTES ====================

@admin_bp.route('/')
def dashboard():
    """Admin dashboard"""
    stats = db_manager.get_daily_stats()
    student_count = Student.query.filter_by(status='Active').count()
    
    return render_template('admin_dashboard.html', 
                          stats=stats,
                          student_count=student_count)

@admin_bp.route('/students')
def list_students():
    """List all students (paginated)"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    students = Student.query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Decrypt for display
    students_data = []
    for student in students.items:
        data = student.to_dict(decrypt=True)
        students_data.append(data)
    
    return jsonify({
        'success': True,
        'students': students_data,
        'total': students.total,
        'pages': students.pages,
        'current_page': page
    })

@admin_bp.route('/transactions')
def list_transactions():
    """List recent transactions"""
    limit = request.args.get('limit', 50, type=int)
    transactions = db_manager.get_recent_transactions(limit)
    
    transactions_data = [t.to_dict(decrypt=True) for t in transactions]
    
    return jsonify({
        'success': True,
        'transactions': transactions_data
    })

@admin_bp.route('/generate-sample-data', methods=['POST'])
def generate_sample_data():
    """Generate sample student data"""
    try:
        count = request.json.get('count', 50)
        clear_existing = request.json.get('clear_existing', False)
        
        created = populate_database(count, clear_existing)
        
        return jsonify({
            'success': True,
            'message': f'Created {created} sample students',
            'count': created
        })
    except Exception as e:
        logger.error(f"Error generating sample data: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/trigger-reset', methods=['POST'])
def trigger_reset():
    """Manually trigger daily reset - clears usage AND today's transactions"""
    try:
        logger.info("Manual daily reset triggered from admin panel")
        
        from datetime import date, datetime
        from database.models import DailyMealUsage
        
        # 1. Delete ALL daily meal usage records (students get fresh allowances)
        deleted_usage = DailyMealUsage.query.delete()
        logger.info(f"Cleared {deleted_usage} usage records - all students now have fresh allowances")
        
        # 2. Delete today's transactions (so stats show 0)
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        
        deleted_transactions = MealTransaction.query.filter(
            MealTransaction.transaction_timestamp >= today_start
        ).delete()
        
        db.session.commit()
        logger.info(f"Deleted {deleted_transactions} transaction records from today")
        
        total_deleted = deleted_usage + deleted_transactions
        
        return jsonify({
            'success': True,
            'message': f'Daily reset completed. All students have fresh meal allowances.',
            'records_cleared': total_deleted,
            'usage_cleared': deleted_usage,
            'transactions_cleared': deleted_transactions
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error triggering reset: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Reset failed. Check server logs.'
        }), 500
@api_bp.route('/check-recent-scan', methods=['GET'])
def check_recent_scan():
    """Check if a card was recently scanned (for auto-navigation)"""
    try:
        from database.models import MundowareStudentLookup
        from datetime import datetime, timedelta
        
        # Check if there's a recent lookup (within last 2 seconds)
        recent_cutoff = datetime.utcnow() - timedelta(seconds=2)
        
        lookup = MundowareStudentLookup.query.filter(
            MundowareStudentLookup.station_id == config.STATION_ID,
            MundowareStudentLookup.timestamp >= recent_cutoff
        ).first()
        
        if lookup:
            return jsonify({
                'success': True,
                'student_id': lookup.student_id
            })
        else:
            return jsonify({
                'success': True,
                'student_id': None
            })
    
    except Exception as e:
        logger.error(f"Error checking recent scan: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
