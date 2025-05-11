import React, { useState } from 'react';
import CourseSimilarityGraph from './CourseSimilarityGraph';
import CourseSimilarityTSNEGraph from './CourseSimilarityTSNEGraph';
import CourseSimilarityPrecomputedGraph from './CourseSimilarityPrecomputedGraph';

function App() {
  const [mode, setMode] = useState('pca');
  return (
    <div className="App">
      <div style={{ position: 'absolute', top: 10, left: 10, zIndex: 10 }}>
       {/*  <button onClick={() => setMode('pca')} style={{ marginRight: 8, padding: '0.5em 1em', fontWeight: mode === 'pca' ? 'bold' : 'normal' }}>PCA</button>
        <button onClick={() => setMode('tsne')} style={{ marginRight: 8, padding: '0.5em 1em', fontWeight: mode === 'tsne' ? 'bold' : 'normal' }}>t-SNE</button>
        <button onClick={() => setMode('precomputed-pca')} style={{ marginRight: 8, padding: '0.5em 1em', fontWeight: mode === 'precomputed-pca' ? 'bold' : 'normal' }}>Precomputed PCA</button> */}
        <button onClick={() => setMode('precomputed-tsne')} style={{ padding: '0.5em 1em', fontWeight: mode === 'precomputed-tsne' ? 'bold' : 'normal' }}>Precomputed t-SNE</button>
      </div>
      {/* {mode === 'pca' && <CourseSimilarityGraph />}
      {mode === 'tsne' && <CourseSimilarityTSNEGraph />}
      {mode === 'precomputed-pca' && <CourseSimilarityPrecomputedGraph mode="pca" />} */}
      {mode === 'precomputed-tsne' && <CourseSimilarityPrecomputedGraph mode="tsne" />}
    </div>
  );
}

export default App;