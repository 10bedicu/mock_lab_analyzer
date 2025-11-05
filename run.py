"""Main entry point to run both lab analyzer and Flask web app."""
import asyncio
import logging
import sys
import threading
from config.settings import Config
from lab_analyzer.analyzer import DummyLabAnalyzer
from web.app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def run_flask_app():
    """Run Flask web application in a separate thread."""
    app = create_app()
    logger.info(f"Starting Flask web app on {Config.FLASK_HOST}:{Config.FLASK_PORT}")
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=False,  # Must be False when running in thread
        use_reloader=False  # Must be False when running in thread
    )


async def run_lab_analyzer():
    """Run lab analyzer asyncio server."""
    analyzer = DummyLabAnalyzer(
        listen_host=Config.LISTEN_HOST,
        listen_port=Config.LISTEN_PORT
    )
    
    logger.info(f"Starting Lab Analyzer on {Config.LISTEN_HOST}:{Config.LISTEN_PORT}")
    await analyzer.start_server()


def main():
    """Main entry point."""
    logger.info("="*60)
    logger.info("Starting Lab Analyzer System")
    logger.info("="*60)
    
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    # Run lab analyzer in the main thread's event loop
    try:
        asyncio.run(run_lab_analyzer())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == '__main__':
    main()
