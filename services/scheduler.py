"""
Scheduler Service - Handles scheduled tasks
- Daily midnight reset of meal usage
- Log file rotation
- Database maintenance
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from config.settings import config
from database.db_manager import get_db_manager
from utils.logger import get_logger

logger = get_logger(__name__)

class SchedulerService:
    """Manages scheduled background tasks"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.db_manager = get_db_manager()
    
    def start(self):
        """Start the scheduler with all jobs"""
        # Parse reset time from config (format: "HH:MM")
        reset_hour, reset_minute = map(int, config.DAILY_RESET_TIME.split(':'))
        
        # Daily reset job (runs at midnight or configured time)
        self.scheduler.add_job(
            func=self.daily_reset,
            trigger=CronTrigger(hour=reset_hour, minute=reset_minute),
            id='daily_reset',
            name='Daily Meal Usage Reset',
            replace_existing=True
        )
        
        # Database cleanup job (runs weekly on Sunday at 2 AM)
        self.scheduler.add_job(
            func=self.database_cleanup,
            trigger=CronTrigger(day_of_week='sun', hour=2, minute=0),
            id='db_cleanup',
            name='Database Cleanup',
            replace_existing=True
        )
        
        # Health check job (runs every hour)
        self.scheduler.add_job(
            func=self.health_check,
            trigger=CronTrigger(minute=0),
            id='health_check',
            name='System Health Check',
            replace_existing=True
        )
        

        # Daily summary job (runs at 2 PM Panama time)
        self.scheduler.add_job(
            func=self.daily_summary,
            trigger=CronTrigger(hour=14, minute=0),
            id='daily_summary',
            name='Daily Summary to Google Sheets',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("Scheduler service started")
        self._log_scheduled_jobs()
    
    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler service stopped")
    
    def daily_reset(self):
        """
        Daily reset of meal usage
        Called automatically at midnight (or configured time)
        """
        logger.info("Starting daily meal usage reset...")
        
        try:
            from database.models import DailyMealUsage, MundowareStudentLookup
            from datetime import date
            
            # Delete ALL daily meal usage records (not just old ones)
            deleted = DailyMealUsage.query.delete()
            db.session.commit()
            
            # Clear MUNDOWARE lookups
            MundowareStudentLookup.query.delete()
            db.session.commit()
            
            logger.info(f"Daily reset complete. Cleared {deleted} usage records.")
            print(f"🔄 DAILY RESET: Cleared {deleted} usage records at midnight")
            
            return True
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during daily reset: {e}")
            return False
    
    def database_cleanup(self):
        """
        Weekly database maintenance
        - Remove old transaction logs (older than retention period)
        - Vacuum database (SQLite only)
        """
        logger.info("Starting database cleanup...")
        
        try:
            from database.models import db, MealTransaction
            from datetime import timedelta
            
            # Calculate cutoff date (keep logs for LOG_RETENTION_DAYS)
            cutoff_date = datetime.utcnow() - timedelta(days=config.LOG_RETENTION_DAYS)
            
            # Delete old transactions
            deleted = MealTransaction.query.filter(
                MealTransaction.transaction_timestamp < cutoff_date
            ).delete()
            
            db.session.commit()
            
            logger.info(f"Database cleanup complete. Removed {deleted} old transactions.")
            
            # Vacuum SQLite database (if using SQLite)
            if config.DATABASE_TYPE == 'sqlite':
                db.session.execute('VACUUM')
                logger.info("SQLite database vacuumed")
            
            return True
        
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
            return False
    
    def health_check(self):
        """
        Hourly system health check
        Logs system status and alerts on issues
        """
        try:
            from database.models import db
            
            # Check database connection
            db.session.execute('SELECT 1')
            
            # Get daily stats
            stats = self.db_manager.get_daily_stats()
            
            logger.info(
                f"Health Check OK - Today: {stats['approved']} approved, "
                f"{stats['denied']} denied, {stats['total']} total"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def trigger_reset_now(self):
        """
        Manually trigger daily reset (for testing or emergency)
        
        Returns:
            True if successful
        """
        logger.warning("Manual daily reset triggered")
        return self.daily_reset()
    

    
    def daily_summary(self):
        """
        Generate daily summary at 2pm and send to Google Sheets
        Only counts APPROVED transactions
        """
        logger.info("Generating daily summary for Google Sheets...")
        
        try:
            from services.google_sheets_sync import get_sheets_service
            from datetime import date
            
            sheets_service = get_sheets_service()
            stats = self.db_manager.get_daily_stats()
            today = date.today().isoformat()
            
            # Send summary (only approved counts)
            sheets_service.log_daily_summary(
                date=today,
                breakfast_count=stats['breakfast'],
                lunch_count=stats['lunch'],
                snacks_count=stats['snack']
            )
            
            logger.info(f"Daily summary sent: {stats['breakfast']} breakfast, {stats['lunch']} lunch, {stats['snack']} snacks")
            return True
        
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
            return False
    def _log_scheduled_jobs(self):
        """Log all scheduled jobs for reference"""
        jobs = self.scheduler.get_jobs()
        logger.info(f"Scheduled {len(jobs)} jobs:")
        for job in jobs:
            logger.info(f"  - {job.name}: {job.trigger}")


# Singleton instance
_scheduler_service = None

def get_scheduler_service():
    """Get or create scheduler service singleton"""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service


if __name__ == "__main__":
    # Test scheduler
    print("=== Scheduler Service Test ===")
    
    from utils.logger import setup_logging
    setup_logging()
    
    scheduler = SchedulerService()
    
    print("\nStarting scheduler...")
    scheduler.start()
    
    print("\nScheduled jobs:")
    for job in scheduler.scheduler.get_jobs():
        print(f"  {job.name}")
        print(f"    Next run: {job.next_run_time}")
        print(f"    Trigger: {job.trigger}")
        print()
    
    print("Testing manual reset...")
    scheduler.trigger_reset_now()
    
    print("\nScheduler running. Press Ctrl+C to stop.")
    
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.stop()
        print("Test complete!")