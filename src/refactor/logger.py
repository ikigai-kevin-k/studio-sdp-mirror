import os
import time
import logging
import logging.handlers

def setup_logging(enable_logging: bool, log_dir: str):
    """Setup logging configuration"""
    # Set basic configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if enable_logging:
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Setup file handler
        log_file = os.path.join(log_dir, f'sdp_game_{time.strftime("%Y%m%d_%H%M%S")}.log')
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # Setup formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        
        # Keep console output
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        root_logger.setLevel(logging.INFO)
        
        logging.info(f"Logging to file: {log_file}")

# Create a function to get logger
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name"""
    return logging.getLogger(name)
