"""RichMan - Chinese Stock Market Quantitative Analysis Platform.

Main Flask application with CORS enabled, blueprint registration,
and SQLite cache initialization.
"""

import logging
import os
import sys

from flask import Flask, jsonify
from flask_cors import CORS

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Apply TLS bypass patch before importing akshare-dependent modules
from patches.tls_patch import apply_patch as apply_tls_patch
apply_tls_patch()

from services.cache import init_db, clear_expired
from api.market import market_bp
from api.stock import stock_bp
from api.trend import trend_bp
from api.quant import quant_bp
from api.news import news_bp


def create_app():
    """Create and configure the Flask application.

    Returns:
        Configured Flask app instance.
    """
    app = Flask(__name__)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    logger = logging.getLogger(__name__)

    # Enable CORS for all routes and origins
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    })

    # Initialize the SQLite cache database
    try:
        init_db()
        clear_expired()
        logger.info("Cache database initialized and expired entries cleared")
    except Exception as e:
        logger.error("Failed to initialize cache database: %s", e)

    # Register blueprints
    app.register_blueprint(market_bp)
    app.register_blueprint(stock_bp)
    app.register_blueprint(trend_bp)
    app.register_blueprint(quant_bp)
    app.register_blueprint(news_bp)

    logger.info("All blueprints registered successfully")

    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            "code": 0,
            "data": {
                "status": "ok",
                "service": "RichMan Backend",
                "version": "1.0.0",
            },
            "message": "success",
        })

    # Global error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({
            "code": 404,
            "data": None,
            "message": "Endpoint not found",
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 errors."""
        return jsonify({
            "code": 405,
            "data": None,
            "message": "Method not allowed",
        }), 405

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        logger.error("Internal server error: %s", error)
        return jsonify({
            "code": 500,
            "data": None,
            "message": "Internal server error",
        }), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle unhandled exceptions."""
        logger.error("Unhandled exception: %s", error, exc_info=True)
        return jsonify({
            "code": -1,
            "data": None,
            "message": f"An unexpected error occurred: {str(error)}",
        }), 500

    logger.info("RichMan Backend application created successfully")
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
