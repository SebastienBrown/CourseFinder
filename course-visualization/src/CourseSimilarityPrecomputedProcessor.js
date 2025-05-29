import * as d3 from 'd3';
import TSNE from 'tsne-js';
import { CURRENT_SEMESTER, getSemesterDataPaths } from './config/semesterConfig';

// Extract unique course codes
function getUniqueCourseCodes(data) {
  const codeSet = new Set();
  data.forEach(entry => {
    entry.course_codes.forEach(code => codeSet.add(code));
  });
  return Array.from(codeSet);
}

// Build a mapping from course code to index
function getCourseCodeToIndexMap(uniqueCodes) {
  const map = new Map();
  uniqueCodes.forEach((code, idx) => map.set(code, idx));
  return map;
}

// Build similarity matrix (n x n, symmetric, diagonal=1)
function buildSimilarityMatrix(data, uniqueCodes, codeToIdx) {
  const n = uniqueCodes.length;
  const matrix = Array(n).fill().map(() => Array(n).fill(0));
  // Set diagonal to 1
  for (let i = 0; i < n; i++) matrix[i][i] = 1;
  // Fill in similarities
  data.forEach(entry => {
    const idxA = codeToIdx.get(entry.course_codes[0]);
    entry.compared_courses.forEach(comp => {
      const idxB = codeToIdx.get(comp.course_codes[0]);
      if (idxA !== undefined && idxB !== undefined) {
        matrix[idxA][idxB] = comp.similarity_score;
        matrix[idxB][idxA] = comp.similarity_score;
      }
    });
  });
  return matrix;
}

export async function loadPrecomputedCourseData(semester) {
  // Fetch course details from the public directory
  const courseDetailsResponse = await fetch(getSemesterDataPaths(semester).courseDetails);
  if (!courseDetailsResponse.ok) {
    throw new Error(`HTTP error! status: ${courseDetailsResponse.status}`);
  }
  const courseDetails = await courseDetailsResponse.json();
  
  console.log('Course Details Sample:', courseDetails[0]); // Debug log

  // Prepare a simplified list of courses from the details for graph node generation
  // This assumes each entry in courseDetails corresponds to a unique course or merged node
  const courses = courseDetails.map(course => {
    console.log('Processing course:', course); // Debug log
    if (!course.course_codes || !course.course_codes[0]) {
      console.error('Invalid course data:', course);
      return null;
    }
    return {
      code: course.course_codes[0], // Use the first code as a primary identifier
      department: course.course_codes[0].split('-')[0], // Derive department
      // Add other relevant fields needed for nodes if any
    };
  }).filter(Boolean); // Remove any null entries

  return { courses, courseDetails };
}

// PCA logic (same as before)
export function applyPCA(similarityMatrix) {
  const n = similarityMatrix.length;
  // Center the matrix
  const means = similarityMatrix.map(row => row.reduce((a, b) => a + b, 0) / n);
  const centered = similarityMatrix.map((row, i) => row.map(val => val - means[i]));
  // Covariance
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
  // Power iteration for top 2 eigenvectors
  function powerIteration(mat, numVecs = 2, numIter = 100) {
    const n = mat.length;
    let vecs = [];
    for (let v = 0; v < numVecs; v++) {
      let b = Array(n).fill(0).map(() => Math.random());
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
        // Orthogonalize
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
  // Project
  const coordinates = [];
  for (let i = 0; i < n; i++) {
    coordinates.push([
      pc1.reduce((a, x, j) => a + x * centered[i][j], 0),
      pc2.reduce((a, x, j) => a + x * centered[i][j], 0)
    ]);
  }
  // Normalize
  const xExtent = d3.extent(coordinates, d => d[0]);
  const yExtent = d3.extent(coordinates, d => d[1]);
  coordinates.forEach(coord => {
    coord[0] = (coord[0] - xExtent[0]) / (xExtent[1] - xExtent[0]) * 2 - 1;
    coord[1] = (coord[1] - yExtent[0]) / (yExtent[1] - yExtent[0]) * 2 - 1;
  });
  return coordinates;
}

// t-SNE logic (using similarity matrix as distance)
export async function applyTSNE(similarityMatrix) {
  const n = similarityMatrix.length;
  // Convert similarity to distance
  const distanceMatrix = similarityMatrix.map(row => row.map(s => 1 - s));
  // Set diagonal to exactly zero
  for (let i = 0; i < n; i++) {
    distanceMatrix[i][i] = 0;
  }
  // Diagnostics
  let isSquare = true;
  let allNumbers = true;
  let diagonalZero = true;
  for (let i = 0; i < n; i++) {
    if (!Array.isArray(distanceMatrix[i]) || distanceMatrix[i].length !== n) {
      isSquare = false;
      console.error(`[Precomputed t-SNE] Row ${i} is not length ${n}`);
    }
    for (let j = 0; j < n; j++) {
      if (typeof distanceMatrix[i][j] !== 'number' || !Number.isFinite(distanceMatrix[i][j])) {
        allNumbers = false;
        console.error(`[Precomputed t-SNE] Non-numeric or NaN at [${i}][${j}]:`, distanceMatrix[i][j]);
      }
      if (i === j && distanceMatrix[i][j] !== 0) {
        diagonalZero = false;
        console.error(`[Precomputed t-SNE] Diagonal at [${i}][${j}] is not zero:`, distanceMatrix[i][j]);
      }
    }
  }
  if (!isSquare || !allNumbers || !diagonalZero) {
    console.error('[Precomputed t-SNE] Distance matrix failed validation:', {
      isSquare, allNumbers, diagonalZero
    });
    console.log('[Precomputed t-SNE] Sample of distance matrix:', distanceMatrix.slice(0, 3).map(row => row.slice(0, 3)));
    throw new Error('[Precomputed t-SNE] Distance matrix is invalid. See console for details.');
  }
  console.log(`[Precomputed t-SNE] Distance matrix shape: ${n} x ${n}`);
  console.log('[Precomputed t-SNE] Sample row:', distanceMatrix[0]);

  const model = new TSNE({
    dim: 2,
    perplexity: Math.min(30, Math.floor(n / 3)),
    earlyExaggeration: 4.0,
    learningRate: 100.0,
    nIter: 500,
    metric: 'precomputed'
  });
  model.init({ data: distanceMatrix, type: 'distanceMatrix' });
  await model.run();
  let output = model.getOutputScaled();
  output = output.map(([x, y]) => [x * 2 - 1, y * 2 - 1]);
  console.log('[Precomputed t-SNE] Output sample:', output.slice(0, 5));
  return output;
} 