import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { loadAllCourseData, preprocessCourseData, computeSimilarityMatrix, applyTSNE } from './CourseSimilarityTSNEProcessor';

export default function CourseSimilarityTSNEGraph() {
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
    function initializeGraphAsync() {
      setTimeout(async () => {
        try {
          const courses = await loadAllCourseData();
          const processedCourses = preprocessCourseData(courses);
          const similarityMatrix = computeSimilarityMatrix(processedCourses);
          const coordinates = await applyTSNE(similarityMatrix, processedCourses); // t-SNE is async and now needs courses
          const nodes = processedCourses.map((course, i) => ({
            id: course.code,
            x: coordinates[i][0],
            y: coordinates[i][1],
            department: course.department
          }));
          console.log('[t-SNE] Number of nodes:', nodes.length);
          console.log('[t-SNE] Sample node coordinates:', nodes.slice(0, 5).map(n => [n.id, n.x, n.y]));
          let hasNaN = false;
          for (let i = 0; i < nodes.length; i++) {
            if (!Number.isFinite(nodes[i].x) || !Number.isFinite(nodes[i].y)) {
              hasNaN = true;
              console.error('[t-SNE] NaN/undefined in node coordinates at', i, nodes[i]);
            }
          }
          if (hasNaN) {
            console.error('[t-SNE] Some node coordinates are NaN/undefined!');
          }
          if (nodes.length === 0) {
            console.error('[t-SNE] No nodes to render!');
          }
          const width = dimensions.width;
          const height = dimensions.height;
          const svg = d3.select(svgRef.current);
          svg.selectAll('*').remove();
          svg.attr('width', width)
            .attr('height', height)
            .attr('viewBox', `0 0 ${width} ${height}`);
          const g = svg.append('g');
          g.append('rect')
            .attr('width', width)
            .attr('height', height)
            .attr('fill', '#f8f9fa')
            .attr('stroke', '#dee2e6')
            .attr('stroke-width', 1);
          const departments = [...new Set(nodes.map(d => d.department))];
          const colorScale = d3.scaleOrdinal()
            .domain(departments)
            .range(d3.schemeCategory10);
          const padding = Math.max(40, Math.min(width, height) * 0.08);
          const xScale = d3.scaleLinear()
            .domain(d3.extent(nodes, d => d.x))
            .range([padding * 1.5, width - padding * 1.5]);
          const yScale = d3.scaleLinear()
            .domain(d3.extent(nodes, d => d.y))
            .range([padding * 1.5, height - padding * 1.5]);
          const nodeGroup = g.append('g')
            .selectAll('g')
            .data(nodes)
            .enter()
            .append('g')
            .attr('transform', d => `translate(${xScale(d.x)},${yScale(d.y)})`);
          nodeGroup.append('circle')
            .attr('r', 4)
            .attr('fill', d => colorScale(d.department))
            .attr('stroke', '#fff')
            .attr('stroke-width', 1);
          nodeGroup.append('text')
            .attr('text-anchor', 'middle')
            .attr('dy', -8)
            .attr('font-size', '10px')
            .attr('fill', '#333')
            .text(d => d.id);
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
          svg.append('text')
            .attr('x', width / 2)
            .attr('y', padding * 0.6)
            .attr('text-anchor', 'middle')
            .style('font-size', Math.max(18, padding * 0.3))
            .style('font-weight', 'bold')
            .text('Course Similarity Network (t-SNE)');
          setLoading(false);
        } catch (err) {
          setError(err.message);
          setLoading(false);
        }
      }, 0);
    }
    initializeGraphAsync();
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