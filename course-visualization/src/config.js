// Default port configuration
const DEFAULT_PORT = 5001;

// User-specific port configurations
const USER_PORTS = {
  'hnaka24': 5001,
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

// Semester configurations - school-specific
const schoolId = process.env.REACT_APP_SCHOOL_ID || 'AMHERST';

export const AVAILABLE_SEMESTERS = schoolId === 'UPENN'
  ? ['2024F']
  : ['2324S', '2425F']; // Amherst format

export const CURRENT_SEMESTER = schoolId === 'UPENN'
  ? "2024F"
  : "2425F"; // Amherst latest semester


export function getSemesterDataPaths(semester) {
  const schoolId = process.env.REACT_APP_SCHOOL_ID || 'AMHERST';

  if (schoolId === 'UPENN') {
    return {
      courseDetails: `/upenn_courses.json`,
      tsneCoords: `/penn_educ_tsne_coords.json`,
      similarityData: `/upenn_embeddings_2024F.json`,
    };
  } else {
    // Default to Amherst
    return {
      courseDetails: `/amherst_courses_all.json`,
      tsneCoords: `/precomputed_tsne_coords_all.json`,
      similarityData: `/amherst_similarity_data.json`,
    };
  }
}