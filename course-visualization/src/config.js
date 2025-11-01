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

// Semester configurations
export const AVAILABLE_SEMESTERS = ['0910F', '0910S', '1011F', '1011S', '1112F', '1112S', '1213F', '1213S', '1314F', '1314S', '1415F', '1415S', '1516F', '1516S', '1617F', '1617S', '1718F', '1718S', '1819F', '1819S', '1920F', '1920S', '2021F', '2021J', '2021S', '2122F', '2122J', '2122S', '2223F', '2223S', '2324F', '2324S', '2425F', '2425S'];
export const CURRENT_SEMESTER = "2324S";

export function getSemesterDataPaths(semester) {
  return {
    courseDetails: `/amherst_courses_all.json`,
    tsneCoords: `/precomputed_tsne_coords_all_5707402.json`,
    similarityData: `/output_similarity_all.json`,
  };
} 