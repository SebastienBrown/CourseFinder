import React, { useState } from 'react';
import CourseSimilarityGraph from './CourseSimilarityGraph';
import CourseSimilarityTSNEGraph from './CourseSimilarityTSNEGraph';

function App() {
  const [mode, setMode] = useState('pca');
  return (
    <div className="App">
      <div style={{ position: 'absolute', top: 10, right: 10, zIndex: 10 }}>
        <button onClick={() => setMode('pca')} style={{ marginRight: 8, padding: '0.5em 1em', fontWeight: mode === 'pca' ? 'bold' : 'normal' }}>PCA</button>
        <button onClick={() => setMode('tsne')} style={{ padding: '0.5em 1em', fontWeight: mode === 'tsne' ? 'bold' : 'normal' }}>t-SNE</button>
      </div>
      {mode === 'pca' ? <CourseSimilarityGraph /> : <CourseSimilarityTSNEGraph />}
    </div>
  );
}

export default App;