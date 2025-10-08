import socket


class SingleInstance:
    """Ensures only one instance of the application runs."""

    def __init__(self, port: int = 45654):
        self.port = port
        self.socket = None

    def is_running(self) -> bool:
        """Check if another instance is already running."""
        try:
            # Try to bind to a local socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(("127.0.0.1", self.port))
            self.socket.listen(1)
            return False  # We successfully bound, so no other instance is running
        except OSError:
            return True  # Another instance is already running

    def cleanup(self) -> None:
        """Clean up the socket."""
        if self.socket:
            self.socket.close()

