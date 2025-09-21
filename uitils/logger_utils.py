import logging
import os
from datetime import datetime

def setup_logger(name: str, 
                log_level: int = logging.INFO,
                log_file: str = None,
                log_dir: str = "logs") -> logging.Logger:
    """
    Setup logger that outputs to both console and file.
    
    Args:
        name: Logger name
        log_level: Logging level (INFO, DEBUG, etc.)
        log_file: Log file path (defaults to timestamped file)
        log_dir: Directory for log files
        
    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file is None:
        # Create logs directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        today_date = datetime.now().strftime('%Y-%m-%d')
        log_file = f'{log_dir}/{name}_{today_date}.log'
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger