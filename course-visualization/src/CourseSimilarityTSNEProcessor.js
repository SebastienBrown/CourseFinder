import * as d3 from 'd3';
import courseData from './data/amherst_courses_2324S.json';
import TSNE from 'tsne-js';

export async function loadAllCourseData() {
  // Use only about a third of the courses for t-SNE performance
  const n = Math.ceil(courseData.length / 3);
  return courseData.slice(0, n);
}

export function preprocessCourseData(courses) {
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
  return Array.from(courseMap.values());
}

export function computeSimilarityMatrix(courses) {
  const n = courses.length;
  const similarityMatrix = Array(n).fill().map(() => Array(n).fill(0));
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
  return similarityMatrix;
}

function computeCosineSimilarity(text1, text2) {
  const words1 = new Set(text1.toLowerCase().split(/\W+/));
  const words2 = new Set(text2.toLowerCase().split(/\W+/));
  const intersection = new Set([...words1].filter(x => words2.has(x)));
  const union = new Set([...words1, ...words2]);
  return intersection.size / union.size;
}

// Bag-of-words vectorizer for course descriptions
function vectorizeCourses(courses) {
  const vocab = new Map();
  let vocabIndex = 0;
  const docs = courses.map(course => {
    const words = course.description.toLowerCase().split(/\W+/).filter(Boolean);
    const counts = {};
    words.forEach(word => {
      if (!vocab.has(word)) {
        vocab.set(word, vocabIndex++);
      }
      const idx = vocab.get(word);
      counts[idx] = (counts[idx] || 0) + 1;
    });
    return counts;
  });
  // Build dense matrix
  const matrix = docs.map(counts => {
    const vec = Array(vocab.size).fill(0);
    for (const idx in counts) {
      vec[idx] = counts[idx];
    }
    return vec;
  });
  return { matrix, vocab };
}

export async function applyTSNE(similarityMatrix, courses) {
  // Instead of using the similarity matrix, use bag-of-words features
  try {
    if (!courses) {
      throw new Error('Courses array must be provided to applyTSNE for vectorization.');
    }
    const { matrix, vocab } = vectorizeCourses(courses);
    const n = matrix.length;
    const d = matrix[0].length;
    console.log(`[t-SNE] Bag-of-words matrix shape: ${n} x ${d}`);
    console.log('[t-SNE] Sample row:', matrix[0]);
    if (!Array.isArray(matrix) || !Array.isArray(matrix[0])) {
      console.error('[t-SNE] Matrix is not a 2D array.');
      throw new Error('Matrix is not a 2D array.');
    }
    if (matrix.length === 0 || matrix[0].length === 0) {
      console.error('[t-SNE] Matrix is empty.');
      throw new Error('Matrix is empty.');
    }
    let hasNaN = false;
    for (let i = 0; i < n; i++) {
      for (let j = 0; j < d; j++) {
        if (!Number.isFinite(matrix[i][j])) {
          hasNaN = true;
          console.error(`[t-SNE] NaN/undefined at [${i}][${j}]:`, matrix[i][j]);
        }
      }
    }
    if (hasNaN) {
      throw new Error('[t-SNE] Matrix contains NaN/undefined values!');
    }
    // Run t-SNE
    const model = new TSNE({
      dim: 2,
      perplexity: Math.min(30, Math.floor(n / 3)),
      earlyExaggeration: 4.0,
      learningRate: 100.0,
      nIter: 500,
      metric: 'euclidean'
    });
    model.init({ data: matrix });
    console.log('[t-SNE] Starting t-SNE run...');
    await model.run();
    console.log('[t-SNE] t-SNE run complete.');
    let output = model.getOutputScaled();
    output = output.map(([x, y]) => [x * 2 - 1, y * 2 - 1]);
    console.log('[t-SNE] Output sample:', output.slice(0, 5));
    return output;
  } catch (err) {
    console.error('[t-SNE] Error:', err);
    throw err;
  }
} 