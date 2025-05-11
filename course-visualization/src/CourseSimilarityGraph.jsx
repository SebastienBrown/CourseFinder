import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { loadAllCourseData, preprocessCourseData, computeSimilarityMatrix, applyTSNE, prepareGraphData } from './CourseSimilarityProcessor';

export default function CourseSimilarityGraph() {
  const svgRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dimensions, setDimensions] = useState({ width: window.innerWidth, height: window.innerHeight });

  useEffect(() => {
    function handleResize() {
      setDimensions({ width: window.innerWidth, height: window.innerHeight });
    }
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    async function initializeGraph() {
      try {
        console.log('Starting graph initialization');
        // Load and process course data
        const courses = await loadAllCourseData();
        console.log('Courses loaded:', courses);
        const processedCourses = preprocessCourseData(courses);
        console.log('Courses processed:', processedCourses);
        // Compute similarity matrix
        const similarityMatrix = computeSimilarityMatrix(processedCourses);
        console.log('Similarity matrix:', similarityMatrix);
        // Apply PCA
        const coordinates = applyTSNE(similarityMatrix);
        console.log('Coordinates:', coordinates);
        // Prepare graph data
        const { nodes } = prepareGraphData(processedCourses, coordinates);
        console.log('Nodes prepared:', nodes);
        // Set up the visualization
        const width = dimensions.width;
        const height = dimensions.height;
        const svg = d3.select(svgRef.current);
        console.log('SVG element:', svg.node());
        // Clear any existing content
        svg.selectAll('*').remove();
        // Set explicit dimensions on the SVG
        svg.attr('width', width)
          .attr('height', height)
          .attr('viewBox', `0 0 ${width} ${height}`);
        // Create main group
        const g = svg.append('g');
        console.log('Group created');
        // Add background
        g.append('rect')
          .attr('width', width)
          .attr('height', height)
          .attr('fill', '#f8f9fa')
          .attr('stroke', '#dee2e6')
          .attr('stroke-width', 1);
        // Create color scale for departments
        const departments = [...new Set(nodes.map(d => d.department))];
        console.log('Departments:', departments);
        const colorScale = d3.scaleOrdinal()
          .domain(departments)
          .range(d3.schemeCategory10);
        // Set up scales for fixed positioning
        const padding = Math.max(40, Math.min(width, height) * 0.08);
        const xScale = d3.scaleLinear()
          .domain(d3.extent(nodes, d => d.x))
          .range([padding * 1.5, width - padding * 1.5]);
        const yScale = d3.scaleLinear()
          .domain(d3.extent(nodes, d => d.y))
          .range([padding * 1.5, height - padding * 1.5]);
        // Draw nodes
        const nodeGroup = g.append('g')
          .selectAll('g')
          .data(nodes)
          .enter()
          .append('g')
          .attr('transform', d => `translate(${xScale(d.x)},${yScale(d.y)})`);
        // Add circles
        nodeGroup.append('circle')
          .attr('r', 4)
          .attr('fill', d => colorScale(d.department))
          .attr('stroke', '#fff')
          .attr('stroke-width', 1);
        // Add course codes
        nodeGroup.append('text')
          .attr('text-anchor', 'middle')
          .attr('dy', -8)
          .attr('font-size', '10px')
          .attr('fill', '#333')
          .text(d => d.id);
        // Add legend (dynamic position)
        const legend = svg.append('g')
          .attr('transform', `translate(${padding}, ${padding})`)
          .attr('class', 'legend');
        departments.forEach((dept, i) => {
          const row = legend.append('g')
            .attr('transform', `translate(0, ${i * 20})`);
          row.append('rect')
            .attr('width', 15)
            .attr('height', 15)
            .attr('fill', colorScale(dept));
          row.append('text')
            .attr('x', 20)
            .attr('y', 12)
            .text(dept)
            .style('font-size', '12px');
        });
        // Add title (dynamic position)
        svg.append('text')
          .attr('x', width / 2)
          .attr('y', padding * 0.6)
          .attr('text-anchor', 'middle')
          .style('font-size', Math.max(18, padding * 0.3))
          .style('font-weight', 'bold')
          .text('Course Similarity Network (PCA)');
        console.log('Graph initialization complete');
        setLoading(false);
      } catch (err) {
        console.error('Error initializing graph:', err);
        setError(err.message);
        setLoading(false);
      }
    }
    initializeGraph();
  }, [dimensions]);

  if (loading) {
    return <div className="flex items-center justify-center p-4">Loading...</div>;
  }

  if (error) {
    return <div className="flex items-center justify-center p-4 text-red-500">Error: {error}</div>;
  }

  return (
    <div style={{ width: '100vw', height: '100vh', margin: 0, padding: 0, position: 'relative', overflow: 'hidden' }}>
      <svg
        ref={svgRef}
        style={{ width: '100vw', height: '100vh', display: 'block', position: 'absolute', top: 0, left: 0 }}
      />
      <div style={{ position: 'absolute', bottom: 0, left: 0, width: '100vw', background: 'rgba(255,255,255,0.95)', textAlign: 'center', fontSize: '1rem', padding: '0.5rem 0' }}>
        Each point represents a course, positioned using t-SNE based on course description similarity. Courses with similar content are placed closer together. Colors indicate departments.
      </div>
    </div>
  );
}