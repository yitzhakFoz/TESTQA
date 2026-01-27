from socket import socket, AF_INET, SOCK_STREAM
import re
from typing import Optional


def request_current_from_ammeter(port: int, command: bytes, timeout: float = 5.0) -> Optional[float]:
    """
    Request a current measurement from an ammeter server.

    Args:
        port: The port number of the ammeter server
        command: The command bytes to send to the ammeter
        timeout: Socket timeout in seconds

    Returns:
        The measurement value as a float, or None if failed
    """
    try:
        with socket(AF_INET, SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(('localhost', port))
            s.sendall(command)
            data = s.recv(1024)
            if data:
                response = data.decode('utf-8')
                # Extract numeric value from response (e.g., "Current: 1.234 A" -> 1.234)
                match = re.search(r'[-+]?\d*\.?\d+', response)
                if match:
                    return float(match.group())
            return None
    except (ConnectionRefusedError, TimeoutError, OSError) as e:
        print(f"Connection error on port {port}: {e}")
        return None

