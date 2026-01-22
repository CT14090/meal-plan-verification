"""
Flask Application - Main web application
Serves touchscreen interface and admin dashboard
"""

from flask import Flask
from flask_cors import CORS
from config.settings import config
from database.models import init_db
from utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

def create_app():
    """
    Create and configure Flask application
    
    Returns:
        Configured Flask app instance
    """
    # Initialize Flask
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['SQLALCHEMY_ECHO'] = config.SQLALCHEMY_ECHO
    
    # Enable CORS for touchscreen (if needed for external requests)
    CORS(app)
    
    # Setup logging
    setup_logging()
    logger.info("Starting Meal Plan Verification System")
    logger.info(f"Station ID: {config.STATION_ID}")
    logger.info(f"Database: {config.DATABASE_TYPE}")
    
    # Validate configuration
    try:
        config.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    
    # Initialize database
    init_db(app)
    logger.info("Database initialized")
    
    # Register blueprints
    from web.routes import main_bp, api_bp, admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    logger.info("Routes registered")
    
    # Context processors (make config available in templates)
    @app.context_processor
    def inject_config():
        return {
            'station_id': config.STATION_ID,
            'station_name': config.STATION_ID.replace('_', ' '),
            'touchscreen_fullscreen': config.TOUCHSCREEN_FULLSCREEN
        }
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"404 error: {error}")
        return "Page not found", 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"500 error: {error}")
        return "Internal server error", 500
    
    logger.info("Flask application created successfully")
    return app


if __name__ == "__main__":
    app = create_app()
    
    print("\n" + "="*60)
    print("MEAL PLAN VERIFICATION SYSTEM")
    print("="*60)
    print(f"\nStation: {config.STATION_ID}")
    print(f"Database: {config.DATABASE_TYPE}")
    print(f"\nStarting server...")
    print(f"Touchscreen Interface: http://{config.FLASK_HOST}:{config.FLASK_PORT}/")
    print(f"Admin Dashboard: http://{config.FLASK_HOST}:{config.FLASK_PORT}/admin")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")
    
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG
    )