# ANSI escape codes for colors
RED = '\033[91m'
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

def log_with_color(message, color=None):
    """Print log message with color"""
    if color:
        print(f"{color}{message}{RESET}")
    else:
        print(message) 