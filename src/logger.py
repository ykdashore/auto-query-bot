import os
import logging
from datetime import datetime

# Ensure logs directory exists
if not os.path.exists('logs'):
    os.makedirs('logs')

# Define log file path with a timestamp for uniqueness
log_file_path = f"logs/app_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

# Set up logging configuration
def setup_logger():
    logger = logging.getLogger(__name__)

    # Set logging level and format
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Add terminal logging (StreamHandler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add file logging (FileHandler)
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
