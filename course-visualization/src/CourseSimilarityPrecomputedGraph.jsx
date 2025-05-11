import React, { useLayoutEffect, useRef, useState, useEffect, useCallback } from 'react';
import * as d3 from 'd3';
import { loadPrecomputedCourseData, applyPCA, applyTSNE } from './CourseSimilarityPrecomputedProcessor';
import precomputedTSNECoords from './data/precomputed_tsne_coords.json';

export default function CourseSimilarityPrecomputedGraph({ mode }) {
  const svgRef = useRef(null);
  const [svgReady, setSvgReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dimensions, setDimensions] = useState({ width: window.innerWidth, height: window.innerHeight });

  // Callback ref to set svgReady when SVG is mounted
  const setSvgRef = useCallback(node => {
    svgRef.current = node;
    if (node) setSvgReady(true);
  }, []);

  useEffect(() => {
    function handleResize() {
      setDimensions({ width: window.innerWidth, height: window.innerHeight });
    }
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useLayoutEffect(() => {
    async function initializeGraph() {
      try {
        setLoading(true);
        if (!svgRef.current) {
          console.error('[Graph] SVG element is null, skipping D3 drawing.');
          setLoading(false);
          return;
        }
        const { courses, similarityMatrix } = loadPrecomputedCourseData();
        let coordinates;
        if (mode === 'pca') {
          coordinates = applyPCA(similarityMatrix);
        } else {
          // Use precomputed t-SNE coordinates
          const codeToIndex = new Map(courses.map((c, i) => [c.code, i]));
          coordinates = Array(courses.length).fill([0, 0]);
          precomputedTSNECoords.forEach(({ code, x, y }) => {
            const idx = codeToIndex.get(code);
            if (idx !== undefined) {
              coordinates[idx] = [x, y];
            }
          });
        }
        // Diagnostics
        console.log('[Graph] SVG element:', svgRef.current);
        console.log('[Graph] Number of courses:', courses.length);
        console.log('[Graph] Sample coordinates:', coordinates.slice(0, 5));
        let hasNaN = false;
        for (let i = 0; i < coordinates.length; i++) {
          if (!Number.isFinite(coordinates[i][0]) || !Number.isFinite(coordinates[i][1])) {
            hasNaN = true;
            console.error('[Graph] NaN/undefined in coordinates at', i, coordinates[i]);
          }
        }
        if (hasNaN) {
          console.error('[Graph] Some coordinates are NaN/undefined!');
        }
        const nodes = courses.map((course, i) => ({
          id: course.code,
          x: coordinates[i][0],
          y: coordinates[i][1],
          department: course.department
        }));
        if (nodes.length === 0) {
          console.error('[Graph] No nodes to render!');
        }
        console.log('[Graph] Sample nodes:', nodes.slice(0, 5));
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
          .text(`Course Similarity Network (Precomputed, ${mode.toUpperCase()})`);
        setLoading(false);
        console.log('[Graph] Drawing complete.');
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    }
    if (svgReady) {
      initializeGraph();
    }
  }, [dimensions, mode, svgReady]);

  if (loading) {
    return <div className="flex items-center justify-center p-4">Loading...</div>;
  }
  if (error) {
    return <div className="flex items-center justify-center p-4 text-red-500">Error: {error}</div>;
  }
  return (
    <div style={{ width: '100vw', height: '100vh', margin: 0, padding: 0, position: 'relative', overflow: 'hidden' }}>
      <svg
        ref={setSvgRef}
        style={{ width: '100vw', height: '100vh', display: 'block', position: 'absolute', top: 0, left: 0 }}
      />
      <div style={{ position: 'absolute', bottom: 0, left: 0, width: '100vw', background: 'rgba(255,255,255,0.95)', textAlign: 'center', fontSize: '1rem', padding: '0.5rem 0' }}>
        Each point represents a course, positioned using precomputed similarity scores. Courses with similar content are placed closer together. Colors indicate departments.
      </div>
    </div>
  );
} 