import os

# Default port configuration
DEFAULT_PORT = 5000

# User-specific port configurations
USER_PORTS = {
    'hnaka24': 5000,
    # Add other users and their ports here
}

# Get the current user's username
try:
    username = os.getlogin()
    # Get the port for the current user, or use default
    PORT = USER_PORTS.get(username, DEFAULT_PORT) 
except:
    PORT = DEFAULT_PORT