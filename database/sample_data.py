"""
Sample Data Generator - Creates test students for development/testing
Generates 50 students with varied meal plans and realistic data
"""

import random
from database.models import db, Student
from config.settings import config
from utils.logger import get_logger

logger = get_logger(__name__)

# Sample data pools
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Barbara", "David", "Elizabeth", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Edward", "Deborah"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell", "Carter",
    "Roberts", "Gomez"
]

def generate_card_uid():
    """
    Generate a realistic-looking MIFARE card UID
    Format: 8 hex characters (4 bytes)
    """
    return ''.join(random.choices('0123456789ABCDEF', k=8))

def generate_students(count=50):
    """
    Generate sample students
    
    Args:
        count: Number of students to generate
    
    Returns:
        List of Student objects
    """
    students = []
    used_uids = set()
    used_ids = set()
    
    # Meal plan distribution
    # 60% Basic, 30% Premium, 10% Unlimited
    meal_plans = (
        ['Basic'] * 30 +
        ['Premium'] * 15 +
        ['Unlimited'] * 5
    )
    random.shuffle(meal_plans)
    
    for i in range(count):
        # Generate unique student ID
        while True:
            student_id = f"{10000 + i + random.randint(0, 1000)}"
            if student_id not in used_ids:
                used_ids.add(student_id)
                break
        
        # Generate unique card UID
        while True:
            card_uid = generate_card_uid()
            if card_uid not in used_uids:
                used_uids.add(card_uid)
                break
        
        # Generate name
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        full_name = f"{first_name} {last_name}"
        
        # Random grade (9-12)
        grade = random.randint(9, 12)
        
        # Meal plan
        meal_plan_type = meal_plans[i % len(meal_plans)]
        daily_limit = config.MEAL_PLAN_TYPES[meal_plan_type]
        
        # 95% active, 5% inactive (for testing)
        status = 'Active' if random.random() < 0.95 else 'Inactive'
        
        student = Student.create_encrypted(
            student_id=student_id,
            card_rfid_uid=card_uid,
            student_name=full_name,
            grade_level=grade,
            meal_plan_type=meal_plan_type,
            daily_meal_limit=daily_limit,
            status=status
        )
        
        students.append(student)
    
    return students

def populate_database(count=50, clear_existing=False):
    """
    Populate database with sample students
    
    Args:
        count: Number of students to generate
        clear_existing: If True, delete existing students first
    
    Returns:
        Number of students created
    """
    try:
        if clear_existing:
            logger.warning("Clearing existing students...")
            Student.query.delete()
            db.session.commit()
            logger.info("Existing students cleared")
        
        logger.info(f"Generating {count} sample students...")
        students = generate_students(count)
        
        logger.info("Adding students to database...")
        for student in students:
            db.session.add(student)
        
        db.session.commit()
        logger.info(f"✅ Successfully created {len(students)} sample students")
        
        # Print summary
        basic_count = sum(1 for s in students if s.meal_plan_type == 'Basic')
        premium_count = sum(1 for s in students if s.meal_plan_type == 'Premium')
        unlimited_count = sum(1 for s in students if s.meal_plan_type == 'Unlimited')
        active_count = sum(1 for s in students if s.status == 'Active')
        
        print("\n=== Sample Data Summary ===")
        print(f"Total Students: {len(students)}")
        print(f"  Active: {active_count}")
        print(f"  Inactive: {len(students) - active_count}")
        print(f"\nMeal Plans:")
        print(f"  Basic (1/day): {basic_count}")
        print(f"  Premium (2/day): {premium_count}")
        print(f"  Unlimited: {unlimited_count}")
        print(f"\nGrades: 9-12")
        
        # Show a few sample students
        print("\n=== Sample Students (first 5) ===")
        from config.encryption import get_encryption_manager
        em = get_encryption_manager()
        
        for i, student in enumerate(students[:5], 1):
            name = em.decrypt(student.student_name)
            uid = em.decrypt(student.card_rfid_uid)
            print(f"{i}. {name}")
            print(f"   ID: {student.student_id} | Card: {uid}")
            print(f"   Grade: {student.grade_level} | Plan: {student.meal_plan_type} ({student.daily_meal_limit}/day)")
            print()
        
        return len(students)
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error populating database: {e}")
        return 0

def export_student_cards_csv(filename='student_cards.csv'):
    """
    Export student IDs and card UIDs to CSV for reference
    Useful for printing card mapping lists
    
    Args:
        filename: Output CSV filename
    """
    try:
        import csv
        from config.encryption import get_encryption_manager
        
        em = get_encryption_manager()
        students = Student.query.order_by(Student.student_id).all()
        
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Student ID', 'Student Name', 'Card UID', 'Meal Plan', 'Daily Limit', 'Grade', 'Status'])
            
            for student in students:
                writer.writerow([
                    student.student_id,
                    em.decrypt(student.student_name),
                    em.decrypt(student.card_rfid_uid),
                    student.meal_plan_type,
                    student.daily_meal_limit,
                    student.grade_level,
                    student.status
                ])
        
        logger.info(f"Exported {len(students)} students to {filename}")
        print(f"✅ Exported to {filename}")
        return True
    
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        return False


if __name__ == "__main__":
    print("=== Sample Data Generator ===")
    print("This script generates sample students for testing.\n")
    
    # This would normally be run from main.py with Flask app context
    print("To use this script:")
    print("1. Run: python main.py")
    print("2. In the admin interface, use the 'Generate Sample Data' button")
    print("\nOr use the Flask shell:")
    print("  flask shell")
    print("  >>> from database.sample_data import populate_database")
    print("  >>> populate_database(50)")