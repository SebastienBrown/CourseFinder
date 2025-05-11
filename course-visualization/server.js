const express = require('express');
const path = require('path');
const fs = require('fs').promises;

const app = express();
const port = process.env.PORT || 3000;

// Serve static files from the build directory
app.use(express.static(path.join(__dirname, 'build')));

// API endpoint to get all course data
app.get('/api/courses', async (req, res) => {
  try {
    const coursesDir = path.join(__dirname, '..', 'llm_cleaned');
    const files = await fs.readdir(coursesDir);
    
    // Read all JSON files and combine their contents
    const allCourses = [];
    for (const file of files) {
      if (file.endsWith('.json')) {
        const content = await fs.readFile(path.join(coursesDir, file), 'utf8');
        const courses = JSON.parse(content);
        allCourses.push(...courses);
      }
    }
    
    res.json(allCourses);
  } catch (error) {
    console.error('Error reading course data:', error);
    res.status(500).json({ error: 'Failed to load course data' });
  }
});

// Serve the React app for all other routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'build', 'index.html'));
});

app.listen(port, () => {
  console.log(`Server running on port ${port}`);
}); 