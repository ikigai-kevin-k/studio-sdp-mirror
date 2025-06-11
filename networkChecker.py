import errno
import socket
from typing import Union, Tuple

def networkChecker(error: Union[OSError, socket.error]) -> Tuple[bool, str]:
    """
    Check if the error is a common network-related error.
    
    Args:
        error: The error object to check (OSError or socket.error)
        
    Returns:
        Tuple[bool, str]: A tuple containing:
            - bool: True if it's a network error, False otherwise
            - str: A human-readable description of the error
    """
    network_errors = {
        errno.ENETUNREACH: "Network unreachable (errno 101)",
        errno.ECONNRESET: "Connection reset by peer (errno 104)",
        errno.ECONNREFUSED: "Connection refused (errno 111)",
        errno.ETIMEDOUT: "Connection timed out (errno 110)",
        errno.ENETDOWN: "Network is down (errno 100)",
        errno.EHOSTUNREACH: "No route to host (errno 113)",
        errno.EPIPE: "Broken pipe (errno 32)"
    }
    
    try:
        error_code = error.errno
        if error_code in network_errors:
            return True, network_errors[error_code]
        return False, f"Not a common network error. Error code: {error_code}"
    except AttributeError:
        return False, "Invalid error object provided"

# Example usage
if __name__ == "__main__":
    # Simulate a network unreachable error
    try:
        # Create a socket and try to connect to an unreachable address
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("240.0.0.0", 80))  # This IP is reserved and unreachable
    except OSError as e:
        is_network_error, error_message = networkChecker(e)
        print(f"Is network error: {is_network_error}")
        print(f"Error message: {error_message}") 