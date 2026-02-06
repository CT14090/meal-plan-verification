# Add this to preserve the original admin dashboard
# The admin dashboard at /admin should still work
# Student management is at /admin/students

@admin_bp.route('/')
def dashboard():
    """Admin dashboard - ORIGINAL (meal stats, reset)"""
    stats = db_manager.get_daily_stats()
    student_count = Student.query.filter_by(status='Active').count()
    
    return render_template('admin_dashboard.html', 
                          stats=stats,
                          student_count=student_count)

@admin_bp.route('/students')
def students_page():
    """NEW: Student management page"""
    return render_template('admin_students.html')
