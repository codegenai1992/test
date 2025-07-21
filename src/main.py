"""
Main application entry point for the Snowflake AI Assistant.
"""

import logging
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import get_settings
from services.app_service import AppService

# Configure logging
def setup_logging():
    """Setup application logging."""
    settings = get_settings()
    
    logging.basicConfig(
        level=getattr(logging, settings.app.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('snowflake_ai_assistant.log')
        ]
    )

def main():
    """Main application entry point."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting Snowflake AI Assistant...")
        
        # Initialize settings
        settings = get_settings()
        logger.info(f"Application: {settings.app.name} v{settings.app.version}")
        
        # Initialize application service
        app_service = AppService()
        
        # Test connections
        logger.info("Testing system connections...")
        connection_status = app_service.test_connections()
        
        if connection_status['overall']:
            logger.info("✅ All connections successful")
        else:
            logger.warning("⚠️ Some connections failed:")
            for error in connection_status.get('errors', []):
                logger.warning(f"  - {error}")
        
        # Get system status
        system_status = app_service.get_system_status()
        logger.info(f"System status: {system_status['health']['overall_healthy']}")
        
        # Example query processing (for testing)
        if len(sys.argv) > 1:
            test_query = " ".join(sys.argv[1:])
            logger.info(f"Processing test query: {test_query}")
            
            result = app_service.process_query(test_query)
            
            print("\n" + "="*50)
            print("QUERY RESULT")
            print("="*50)
            print(f"Success: {result.success}")
            print(f"Message: {result.message}")
            print(f"Execution Time: {result.total_execution_time:.2f}s")
            print(f"Agents Used: {len(result.agent_results)}")
            
            if result.suggestions:
                print("\nSuggestions:")
                for i, suggestion in enumerate(result.suggestions, 1):
                    print(f"  {i}. {suggestion}")
            
            if result.final_result and result.final_result.get('data'):
                print(f"\nData Available: Yes")
            
            print("="*50)
        
        else:
            logger.info("No test query provided. Use: python src/main.py 'your query here'")
            logger.info("For Streamlit UI, run: streamlit run streamlit_app.py")
        
        logger.info("Application ready")
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        logger.error("Stack trace:", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Shutting down...")

if __name__ == "__main__":
    main()

