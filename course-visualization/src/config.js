// Default port configuration
const DEFAULT_PORT = 5000;

// User-specific port configurations
const USER_PORTS = {
  'hnaka24': 5000,
  // Add other users and their ports here
};

// Try to get port in this order:
// 1. User-specific port from build
// 2. Port from localStorage (if user changed it)
// 3. Default port
const getPort = () => {
  const userPort = USER_PORTS[process.env.REACT_APP_USER];
  const savedPort = localStorage.getItem('apiPort');
  return savedPort || userPort || DEFAULT_PORT;
};

// Export the API base URL
export const API_BASE_URL = `http://127.0.0.1:${getPort()}`;

// Allow runtime changes to the port
export const updatePort = (newPort) => {
  if (newPort && !isNaN(newPort)) {
    localStorage.setItem('apiPort', newPort);
    window.location.reload();
  }
};

// Get current port (useful for UI)
export const getCurrentPort = () => getPort(); 