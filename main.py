"""
Main Entry Point - Starts the complete system
Coordinates all services: RFID reader, Flask web server, scheduler
"""

import sys
import signal
from web.app import create_app
from config.settings import config
from services.rfid_reader import RFIDReaderService
from services.scheduler import get_scheduler_service
from utils.logger import setup_logging, get_logger

# Setup logging first
setup_logging()
logger = get_logger(__name__)

# Global services
rfid_service = None
scheduler_service = None
app = None

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    logger.info("\nShutdown signal received...")
    cleanup()
    sys.exit(0)

def cleanup():
    """Stop all services"""
    global rfid_service, scheduler_service
    
    if rfid_service:
        logger.info("Stopping RFID reader service...")
        rfid_service.stop()
    
    if scheduler_service:
        logger.info("Stopping scheduler service...")
        scheduler_service.stop()
    
    logger.info("Cleanup complete")

def on_card_scanned(card_uid):
    """
    Callback when RFID card is detected
    Sends card UID to web interface via HTTP
    
    Args:
        card_uid: Card UID from RFID reader
    """
    import requests
    
    try:
        # Send to local Flask API
        url = f"http://{config.FLASK_HOST}:{config.FLASK_PORT}/api/scan-card"
        response = requests.post(url, json={'card_uid': card_uid}, timeout=2)
        
        if response.status_code == 200:
            logger.info(f"Card {card_uid[:8]}*** processed successfully")
        else:
            logger.warning(f"Card processing failed: {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error sending card to API: {e}")

def start_system():
    """Start all system services"""
    global rfid_service, scheduler_service, app
    
    logger.info("="*60)
    logger.info("MEAL PLAN VERIFICATION SYSTEM")
    logger.info("="*60)
    
    # Create Flask app
    logger.info("Creating Flask application...")
    app = create_app()
    
    # Start scheduler service
    logger.info("Starting scheduler service...")
    scheduler_service = get_scheduler_service()
    scheduler_service.start()
    
    # Start RFID reader service (if enabled)
    if config.RFID_ENABLED:
        logger.info("Starting RFID reader service...")
        rfid_service = RFIDReaderService(callback=on_card_scanned)
        rfid_service.start()
    else:
        logger.warning("RFID reader disabled in configuration")
    
    logger.info("")
    logger.info("="*60)
    logger.info(f"Station: {config.STATION_ID}")
    logger.info(f"Database: {config.DATABASE_TYPE}")
    logger.info("")
    logger.info(f"Touchscreen: http://{config.FLASK_HOST}:{config.FLASK_PORT}/")
    logger.info(f"Admin Panel: http://{config.FLASK_HOST}:{config.FLASK_PORT}/admin")
    logger.info("")
    logger.info("System ready! Press Ctrl+C to stop")
    logger.info("="*60)
    logger.info("")
    
    # Start Flask server (blocking)
    try:
        app.run(
            host=config.FLASK_HOST,
            port=config.FLASK_PORT,
            debug=config.FLASK_DEBUG,
            use_reloader=False  # Disable reloader to prevent double-initialization
        )
    except KeyboardInterrupt:
        pass

def main():
    """Main function"""
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        start_system()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        cleanup()
        sys.exit(1)
    finally:
        cleanup()

if __name__ == "__main__":
    main()