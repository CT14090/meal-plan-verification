"""
Flask Routes - API endpoints and page routes
Handles all touchscreen interactions and admin functions
UPDATED: Meal type selection, photo upload, student CRUD
"""

from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, date
import csv
import io
import os
from config.settings import config
from config.encryption import get_encryption_manager
from database.db_manager import get_db_manager
from database.models import db, Student, MealTransaction
from database.sample_data import populate_database, export_student_cards_csv
from services.scheduler import get_scheduler_service
from utils.logger import get_logger, log_transaction
from services.google_sheets_sync import get_sheets_service

logger = get_logger(__name__)
em = get_encryption_manager()
db_manager = get_db_manager()
sheets_service = get_sheets_service()

# Create blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)
admin_bp = Blueprint('admin', __name__)

# Helper function for photo uploads
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_PHOTO_EXTENSIONS

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
    """Student info display with meal type selection"""
    return render_template('student_info.html')

@main_bp.route('/approved')
def approved():
    """Meal approved confirmation"""
    return render_template('approved.html')

@main_bp.route('/denied')
def denied():
    """Meal denied screen"""
    return render_template('denied.html')

@admin_bp.route('/scan-card')
def scan_card_page():
    """Card UID scanner for enrollment"""
    return render_template('scan_card.html')

@api_bp.route('/scan-card', methods=['POST'])
def scan_card():
    """Handle card scan from RFID reader"""
    try:
        data = request.get_json()
        card_uid = data.get('card_uid', '').strip().upper()
        
        if not card_uid:
            return jsonify({
                'success': False,
                'error': 'No card UID provided'
            }), 400
        
        logger.info(f"Card scanned: {card_uid[:8]}***")

        # Store in session for card enrollment
        from flask import session
        session['last_scanned_card_uid'] = card_uid
        
        # Find student
        student = db_manager.find_student_by_rfid(card_uid)
        
        if not student:
            logger.warning(f"Card not found: {card_uid}")
            return jsonify({
                'success': False,
                'error': 'card_not_found',
                'message': config.DENIAL_REASONS['CARD_NOT_FOUND']
            }), 404
        
        # Get allowed meal types for this student
        allowed_meal_types = config.MEAL_PLAN_ALLOWED_TYPES.get(student.meal_plan_type, [])
        
        # Check eligibility for each meal type
        eligibility_by_type = {}
        for meal_type in config.MEAL_TYPES:
            eligibility_by_type[meal_type] = db_manager.check_eligibility(student, meal_type)
        
        # Decrypt student data for display
        student_data = student.to_dict(decrypt=True)
        
        # Update MUNDOWARE lookup (use general eligibility - eligible if ANY meal type available)
        any_eligible = any(e['eligible'] for e in eligibility_by_type.values())
        db_manager.update_mundoware_lookup(student, any_eligible)
        print(f"📝 Updated MUNDOWARE lookup: {student_data['student_id']} (eligible: {any_eligible})")
        
        return jsonify({
            'success': True,
            'student': student_data,
            'allowed_meal_types': allowed_meal_types,
            'eligibility_by_type': eligibility_by_type
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
    """Manual student lookup by ID"""
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
        
        # Get allowed meal types
        allowed_meal_types = config.MEAL_PLAN_ALLOWED_TYPES.get(student.meal_plan_type, [])
        
        # Check eligibility for each meal type
        eligibility_by_type = {}
        for meal_type in config.MEAL_TYPES:
            eligibility_by_type[meal_type] = db_manager.check_eligibility(student, meal_type)
        
        # Decrypt student data
        student_data = student.to_dict(decrypt=True)
        
        # Update MUNDOWARE lookup
        any_eligible = any(e['eligible'] for e in eligibility_by_type.values())
        db_manager.update_mundoware_lookup(student, any_eligible)
        
        return jsonify({
            'success': True,
            'student': student_data,
            'allowed_meal_types': allowed_meal_types,
            'eligibility_by_type': eligibility_by_type
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
    """Approve meal transaction with specific meal type"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        meal_type = data.get('meal_type')
        
        if not student_id or not meal_type:
            return jsonify({
                'success': False,
                'error': 'Missing student ID or meal type'
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
        
        # Double-check eligibility for this specific meal type
        eligibility = db_manager.check_eligibility(student, meal_type)
        if not eligibility['eligible']:
            logger.warning(f"Approval attempted for ineligible student: {student_id} - {meal_type}")
            
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
        
        # Increment meal usage for this specific meal type
        success = db_manager.increment_meal_usage(student_id, meal_type)
        
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
        log_transaction(student_id, student_name, meal_type, 'Approved')
        
        logger.info(f"Meal approved: {student_id} - {meal_type}")
        
        # Console output for visibility
        print(f"✅ MEAL APPROVED: {student_name} ({student_id}) - {meal_type}")
        
        # Log to Google Sheets
        sheets_service.log_transaction(student_id, meal_type, config.STATUS_APPROVED)
        
        # Get updated eligibility
        updated_eligibility = db_manager.check_eligibility(student, meal_type)
        
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
    """Deny meal transaction"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        meal_type = data.get('meal_type')
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
            meal_type=meal_type,
            status=config.STATUS_DENIED,
            denied_reason=reason
        )
        
        log_transaction(student_id, student_name, meal_type or 'N/A', 'Denied', reason)
        logger.info(f"Meal denied: {student_id} - {reason}")
        
        # Console output
        print(f"❌ MEAL DENIED: {student_name} ({student_id}) - {reason}")
        
        # Log to Google Sheets
        sheets_service.log_transaction(student_id, meal_type, config.STATUS_DENIED)
        
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

@api_bp.route('/check-recent-scan', methods=['GET'])
def check_recent_scan():
    """Check if a card was recently scanned"""
    try:
        from database.models import MundowareStudentLookup
        from datetime import datetime, timedelta
        
        recent_cutoff = datetime.utcnow() - timedelta(seconds=3)
        
        lookup = MundowareStudentLookup.query.filter(
            MundowareStudentLookup.station_id == config.STATION_ID,
            MundowareStudentLookup.timestamp >= recent_cutoff
        ).order_by(MundowareStudentLookup.timestamp.desc()).first()
        
        if lookup:
            print(f"🔍 Recent scan detected: {lookup.student_id}")
            return jsonify({
                'success': True,
                'student_id': lookup.student_id,
                'timestamp': lookup.timestamp.isoformat()
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

@api_bp.route('/clear-lookup', methods=['POST'])
def clear_lookup():
    """Clear the MUNDOWARE lookup table"""
    try:
        db_manager.clear_mundoware_lookup()
        print(f"🧹 Cleared MUNDOWARE lookup for {config.STATION_ID}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error clearing lookup: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/last-card-scan', methods=['GET'])
def last_card_scan():
    """Get the last scanned card UID from session"""
    try:
        from flask import session
        card_uid = session.get('last_scanned_card_uid')
        
        if card_uid:
            return jsonify({
                'success': True,
                'card_uid': card_uid
            })
        else:
            return jsonify({
                'success': True,
                'card_uid': None
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ADMIN ROUTES ====================

@admin_bp.route('/')
def dashboard():
    """Admin dashboard"""
    stats = db_manager.get_daily_stats()
    student_count = Student.query.filter_by(status='Active').count()
    
    return render_template('admin_dashboard.html', 
                          stats=stats,
                          student_count=student_count)

@admin_bp.route('/scan-card')
@admin_bp.route('/students')
def students_page():
    """Student management page"""
    return render_template('admin_students.html')

@admin_bp.route('/api/students', methods=['GET'])
def list_students():
    """API: List all students"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 50
        search = request.args.get('search', '').strip()
        
        query = Student.query
        
        # Search by student ID (exact match since encrypted names can't be searched)
        if search:
            query = query.filter(Student.student_id.like(f'%{search}%'))
        
        students = query.order_by(Student.student_id).paginate(page=page, per_page=per_page, error_out=False)
        
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
    except Exception as e:
        logger.error(f"Error listing students: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/student/<student_id>', methods=['GET'])
def get_student(student_id):
    """API: Get single student details"""
    try:
        student = db_manager.find_student_by_id(student_id)
        if not student:
            return jsonify({'success': False, 'error': 'Student not found'}), 404
        
        student_data = student.to_dict(decrypt=True)
        return jsonify({'success': True, 'student': student_data})
    except Exception as e:
        logger.error(f"Error getting student: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/student/<student_id>', methods=['PUT'])
def update_student(student_id):
    """API: Update student information"""
    try:
        data = request.get_json()
        
        # Prepare update data
        update_data = {}
        if 'student_name' in data:
            update_data['student_name'] = data['student_name']
        if 'card_rfid_uid' in data:
            update_data['card_rfid_uid'] = data['card_rfid_uid']
        if 'grade_level' in data:
            update_data['grade_level'] = int(data['grade_level'])
        if 'meal_plan_type' in data:
            update_data['meal_plan_type'] = data['meal_plan_type']
            # Update daily limit based on meal plan
            update_data['daily_meal_limit'] = config.MEAL_PLAN_TYPES.get(data['meal_plan_type'], 1)
        if 'status' in data:
            update_data['status'] = data['status']
        
        student = db_manager.update_student(student_id, **update_data)
        
        if student:
            return jsonify({
                'success': True,
                'message': 'Student updated successfully',
                'student': student.to_dict(decrypt=True)
            })
        else:
            return jsonify({'success': False, 'error': 'Update failed'}), 500
    except Exception as e:
        logger.error(f"Error updating student: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/student/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    """API: Deactivate student"""
    try:
        success = db_manager.delete_student(student_id)
        if success:
            return jsonify({'success': True, 'message': 'Student deactivated'})
        else:
            return jsonify({'success': False, 'error': 'Delete failed'}), 500
    except Exception as e:
        logger.error(f"Error deleting student: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/student', methods=['POST'])
def add_student():
    """API: Add new student"""
    try:
        data = request.get_json()
        
        student = db_manager.add_student(
            student_id=data['student_id'],
            card_rfid_uid=data['card_rfid_uid'],
            student_name=data['student_name'],
            grade_level=int(data['grade_level']),
            meal_plan_type=data['meal_plan_type'],
            daily_meal_limit=config.MEAL_PLAN_TYPES.get(data['meal_plan_type'], 1),
            status=data.get('status', 'Active')
        )
        
        if student:
            return jsonify({
                'success': True,
                'message': 'Student added successfully',
                'student': student.to_dict(decrypt=True)
            })
        else:
            return jsonify({'success': False, 'error': 'Add failed'}), 500
    except Exception as e:
        logger.error(f"Error adding student: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/student/<student_id>/photo', methods=['POST'])
def upload_student_photo(student_id):
    """API: Upload student photo"""
    try:
        if 'photo' not in request.files:
            return jsonify({'success': False, 'error': 'No photo file'}), 400
        
        file = request.files['photo']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            # Use student_id as filename
            extension = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{student_id}.{extension}"
            filepath = os.path.join(config.PHOTO_UPLOAD_FOLDER, filename)
            
            # Create directory if it doesn't exist
            os.makedirs(config.PHOTO_UPLOAD_FOLDER, exist_ok=True)
            
            file.save(filepath)
            
            # Update student record
            student = db_manager.update_student(student_id, photo_filename=filename)
            
            if student:
                return jsonify({
                    'success': True,
                    'message': 'Photo uploaded successfully',
                    'photo_filename': filename
                })
            else:
                return jsonify({'success': False, 'error': 'Failed to update student'}), 500
        else:
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
    except Exception as e:
        logger.error(f"Error uploading photo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
    """Manually trigger daily reset"""
    try:
        print("\n" + "="*60)
        print("DAILY RESET STARTED")
        print("="*60)
        
        logger.info("Manual daily reset triggered from admin panel")
        
        from datetime import date, datetime
        from database.models import DailyMealUsage, MundowareStudentLookup
        
        # Delete ALL daily meal usage records
        deleted_usage = DailyMealUsage.query.delete()
        print(f"Cleared {deleted_usage} daily usage records")
        
        # Delete today's transactions
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        deleted_transactions = MealTransaction.query.filter(
            MealTransaction.transaction_timestamp >= today_start
        ).delete()
        print(f"Deleted {deleted_transactions} transaction records")
        
        # Clear MUNDOWARE lookups
        deleted_lookups = MundowareStudentLookup.query.delete()
        print(f"Cleared {deleted_lookups} MUNDOWARE lookup entries")
        
        db.session.commit()
        print("="*60)
        print("DAILY RESET COMPLETE")
        print("="*60 + "\n")
        
        return jsonify({
            'success': True,
            'message': 'Daily reset completed',
            'usage_cleared': deleted_usage,
            'transactions_cleared': deleted_transactions,
            'lookups_cleared': deleted_lookups
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error triggering reset: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/export-students-csv')
def export_students_csv():
    """Export all students to CSV"""
    try:
        students = Student.query.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Student ID', 'Student Name', 'Card UID', 'Grade', 'Meal Plan', 'Daily Limit', 'Status', 'Photo'])
        
        for student in students:
            data = student.to_dict(decrypt=True)
            writer.writerow([
                data['student_id'],
                data['student_name'],
                data['card_rfid_uid'],
                data['grade_level'],
                data['meal_plan_type'],
                data['daily_meal_limit'],
                data['status'],
                data.get('photo_filename', '')
            ])
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'students_{date.today().isoformat()}.csv'
        )
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500