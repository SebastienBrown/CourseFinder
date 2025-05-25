import * as d3 from 'd3';

// Import the course data
import courseData from '../data/amherst_courses_2324S.json';

export async function loadAllCourseData() {
  console.log('Loading course data:', courseData.length, 'courses');
  return courseData;
}

export function preprocessCourseData(courses) {
  console.log('Preprocessing', courses.length, 'courses');
  // Create a map of unique course codes to their descriptions
  const courseMap = new Map();
  
  courses.forEach(course => {
    course.course_codes.forEach(code => {
      if (!courseMap.has(code)) {
        courseMap.set(code, {
          code,
          description: course.description || '',
          department: code.split('-')[0]
        });
      }
    });
  });
  
  const processedCourses = Array.from(courseMap.values());
  console.log('Processed into', processedCourses.length, 'unique courses');
  return processedCourses;
}

export function computeSimilarityMatrix(courses) {
  console.log('Computing similarity matrix for', courses.length, 'courses');
  const n = courses.length;
  const similarityMatrix = Array(n).fill().map(() => Array(n).fill(0));
  
  // Simple cosine similarity based on word overlap
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const similarity = computeCosineSimilarity(
        courses[i].description,
        courses[j].description
      );
      similarityMatrix[i][j] = similarity;
      similarityMatrix[j][i] = similarity;
    }
  }
  
  // Check for NaN/undefined
  let hasNaN = false;
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      if (!Number.isFinite(similarityMatrix[i][j])) {
        hasNaN = true;
        console.error(`NaN/undefined at [${i}][${j}]`, similarityMatrix[i][j]);
      }
    }
  }
  if (hasNaN) {
    console.error('Similarity matrix contains NaN/undefined values!');
  }
  console.log('Sample similarity matrix row:', similarityMatrix[0]);
  return similarityMatrix;
}

function computeCosineSimilarity(text1, text2) {
  // Simple word-based similarity
  const words1 = new Set(text1.toLowerCase().split(/\W+/));
  const words2 = new Set(text2.toLowerCase().split(/\W+/));
  
  const intersection = new Set([...words1].filter(x => words2.has(x)));
  const union = new Set([...words1, ...words2]);
  
  return intersection.size / union.size;
}

export function applyTSNE(similarityMatrix) {
  // --- PCA-based 2D projection for visualization ---
  // 1. Center the similarity matrix (subtract mean from each row)
  // 2. Compute the covariance matrix
  // 3. Compute the top 2 eigenvectors (principal components)
  // 4. Project each course onto these two components for (x, y) coordinates

  console.log('Applying PCA for dimensionality reduction');
  const n = similarityMatrix.length;
  // Center the matrix
  const means = similarityMatrix.map(row => row.reduce((a, b) => a + b, 0) / n);
  const centered = similarityMatrix.map((row, i) => row.map(val => val - means[i]));

  // Compute covariance matrix
  const cov = Array(n).fill().map(() => Array(n).fill(0));
  for (let i = 0; i < n; i++) {
    for (let j = 0; j < n; j++) {
      let sum = 0;
      for (let k = 0; k < n; k++) {
        sum += centered[i][k] * centered[j][k];
      }
      cov[i][j] = sum / (n - 1);
    }
  }

  // Power iteration to find top 2 eigenvectors
  function powerIteration(mat, numVecs = 2, numIter = 100) {
    const n = mat.length;
    let vecs = [];
    let used = Array(n).fill(false);
    for (let v = 0; v < numVecs; v++) {
      let b = Array(n).fill(0).map(() => Math.random());
      // Orthogonalize to previous vectors
      for (let iter = 0; iter < numIter; iter++) {
        let bNew = Array(n).fill(0);
        for (let i = 0; i < n; i++) {
          for (let j = 0; j < n; j++) {
            bNew[i] += mat[i][j] * b[j];
          }
        }
        // Normalize
        const norm = Math.sqrt(bNew.reduce((a, x) => a + x * x, 0));
        b = bNew.map(x => x / norm);
        // Orthogonalize to previous vectors
        for (let u = 0; u < vecs.length; u++) {
          const dot = b.reduce((a, x, i) => a + x * vecs[u][i], 0);
          for (let i = 0; i < n; i++) b[i] -= dot * vecs[u][i];
        }
      }
      vecs.push(b);
    }
    return vecs;
  }

  const [pc1, pc2] = powerIteration(cov, 2, 50);

  // Project each course onto the top 2 principal components
  const coordinates = [];
  for (let i = 0; i < n; i++) {
    coordinates.push([
      pc1.reduce((a, x, j) => a + x * centered[i][j], 0),
      pc2.reduce((a, x, j) => a + x * centered[i][j], 0)
    ]);
  }

  // Normalize coordinates to [-1, 1] range
  const xExtent = d3.extent(coordinates, d => d[0]);
  const yExtent = d3.extent(coordinates, d => d[1]);
  coordinates.forEach(coord => {
    coord[0] = (coord[0] - xExtent[0]) / (xExtent[1] - xExtent[0]) * 2 - 1;
    coord[1] = (coord[1] - yExtent[0]) / (yExtent[1] - yExtent[0]) * 2 - 1;
  });

  // Add check for NaN/undefined in coordinates
  let hasNaN = false;
  for (let i = 0; i < coordinates.length; i++) {
    if (!Number.isFinite(coordinates[i][0]) || !Number.isFinite(coordinates[i][1])) {
      hasNaN = true;
      console.error('NaN/undefined in coordinates at', i, coordinates[i]);
    }
  }
  if (hasNaN) {
    console.error('Coordinates contain NaN/undefined values!');
  }
  console.log('Sample coordinates:', coordinates.slice(0, 5));
  return coordinates;
}

export function prepareGraphData(courses, coordinates) {
  console.log('Preparing graph data');
  const nodes = courses.map((course, i) => ({
    id: course.code,
    x: coordinates[i][0],
    y: coordinates[i][1],
    department: course.department
  }));
  
  console.log('Graph data prepared with', nodes.length, 'nodes');
  return { nodes };
} 