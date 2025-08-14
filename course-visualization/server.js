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
    // Point to the amherst_courses_all.json in the public directory
    const coursesFilePath = path.join(__dirname, 'public', 'amherst_courses_all.json');
    
    const content = await fs.readFile(coursesFilePath, 'utf8');
    const allCourses = JSON.parse(content);
    
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