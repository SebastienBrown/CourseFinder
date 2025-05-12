import React, { useLayoutEffect, useRef, useState, useEffect, useCallback } from 'react';
import * as d3 from 'd3';
import { loadPrecomputedCourseData, applyPCA, applyTSNE } from './CourseSimilarityPrecomputedProcessor';
import precomputedTSNECoords from './data/precomputed_tsne_coords.json';

// === Tranche & Shape Definitions ===
const TRANCHE_SHAPES = {
  arts: 'circle',
  humanities: 'square',
  sciences: 'triangle',
  social: 'star'
};

const TRANCHES = {
  arts: ['ARCH', 'ARHA', 'MUSI', 'MUSL', 'THDA'],
  humanities: ['AAPI', 'AMST', 'ARAB', 'ASLC', 'BLST', 'CHIN', 'CLAS', 'EDST', 'ENGL', 'ENST', 'EUST', 'FAMS', 'FREN', 'GERM', 'GREE', 'HIST', 'JAPA', 'LATI', 'LJST', 'LLAS', 'PHIL', 'RELI', 'RUSS', 'SPAN', 'SWAG'],
  sciences: ['ASTR', 'BCBP', 'BIOL', 'CHEM', 'COSC', 'GEOL', 'MATH', 'NEUR', 'PHYS', 'STAT'],
  social: ['ANTH', 'ECON', 'POSC', 'PSYC', 'SOCI']
};

const getTrancheForDept = (dept) => {
  for (const [tranche, majors] of Object.entries(TRANCHES)) {
    if (majors.includes(dept)) return tranche;
  }
  return 'other';
};

const getShapeForDept = (dept) => TRANCHE_SHAPES[getTrancheForDept(dept)] || 'circle';

export default function CourseSimilarityPrecomputedGraph({ mode }) {
  const svgRef = useRef(null);
  const [svgReady, setSvgReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dimensions, setDimensions] = useState({ width: window.innerWidth, height: window.innerHeight });

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
          const codeToIndex = new Map(courses.map((c, i) => [c.code, i]));
          coordinates = Array(courses.length).fill().map(() => [NaN, NaN]);
          precomputedTSNECoords.forEach(({ code, x, y }) => {
            const idx = codeToIndex.get(code);
            if (idx !== undefined) {
              coordinates[idx] = [x, y];
            }
          });
        }

        const allMajors = Object.values(TRANCHES).flat();
        const colorPalette = d3.schemeCategory10.concat(d3.schemeSet3).concat(d3.schemePaired);
        const majorColorMap = new Map();
        let colorIndex = 0;
        for (const tranche of Object.values(TRANCHES)) {
          for (const major of tranche) {
            if (!majorColorMap.has(major)) {
              majorColorMap.set(major, colorPalette[colorIndex % colorPalette.length]);
              colorIndex++;
            }
          }
        }

        const nodes = courses
          .map((course, i) => {
            const [x, y] = coordinates[i];
            if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
            return {
              id: course.code,
              x,
              y,
              department: course.department,
              shape: getShapeForDept(course.department),
              color: majorColorMap.get(course.department) || '#999'
            };
          })
          .filter(Boolean);

        const width = dimensions.width;
        const height = dimensions.height;
        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();
        svg.attr('width', width).attr('height', height).attr('viewBox', `0 0 ${width} ${height}`);
        const g = svg.append('g');

        g.append('rect')
          .attr('width', width)
          .attr('height', height)
          .attr('fill', '#f8f9fa')
          .attr('stroke', '#dee2e6')
          .attr('stroke-width', 1);

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

        nodeGroup.each(function(d) {
          const group = d3.select(this);
          const size = 6;
          const color = d.color;

          switch (d.shape) {
            case 'circle':
              group.append('circle')
                .attr('r', size)
                .attr('fill', color)
                .attr('stroke', '#fff')
                .attr('stroke-width', 1);
              break;
            case 'square':
              group.append('rect')
                .attr('x', -size)
                .attr('y', -size)
                .attr('width', size * 2)
                .attr('height', size * 2)
                .attr('fill', color)
                .attr('stroke', '#fff')
                .attr('stroke-width', 1);
              break;
            case 'triangle':
              group.append('path')
                .attr('d', d3.symbol().type(d3.symbolTriangle).size(size * size * 6)())
                .attr('fill', color)
                .attr('stroke', '#fff')
                .attr('stroke-width', 1);
              break;
            case 'star':
              group.append('path')
                .attr('d', d3.symbol().type(d3.symbolStar).size(size * size * 6)())
                .attr('fill', color)
                .attr('stroke', '#fff')
                .attr('stroke-width', 1);
              break;
            default:
              group.append('circle')
                .attr('r', size)
                .attr('fill', color)
                .attr('stroke', '#fff')
                .attr('stroke-width', 1);
          }
        });

        nodeGroup.append('text')
          .attr('text-anchor', 'middle')
          .attr('dy', d => -8 + Math.random() * 6 - 3)
          .attr('font-size', '10px')
          .attr('fill', '#333')
          .text(d => d.id);

        // Optional: shape-aware legend (can be enhanced)
        const legend = svg.append('g')
          .attr('transform', `translate(${padding}, ${padding})`)
          .attr('class', 'legend');

        let legendIndex = 0;
        for (const [dept, color] of majorColorMap.entries()) {
          const shape = getShapeForDept(dept);
          const row = legend.append('g')
            .attr('transform', `translate(0, ${legendIndex * 20})`);
          const size = 6;

          switch (shape) {
            case 'circle':
              row.append('circle').attr('r', size).attr('fill', color);
              break;
            case 'square':
              row.append('rect').attr('x', -size).attr('y', -size).attr('width', size * 2).attr('height', size * 2).attr('fill', color);
              break;
            case 'triangle':
              row.append('path')
                .attr('d', d3.symbol().type(d3.symbolTriangle).size(size * size * 6)())
                .attr('fill', color)
                .attr('transform', `translate(0, 0)`);
              break;
            case 'star':
              row.append('path')
                .attr('d', d3.symbol().type(d3.symbolStar).size(size * size * 6)())
                .attr('fill', color)
                .attr('transform', `translate(0, 0)`);
              break;
          }

          row.append('text')
            .attr('x', 20)
            .attr('y', 5)
            .text(dept)
            .style('font-size', '12px');

          legendIndex++;
        }

        svg.append('text')
          .attr('x', width / 2)
          .attr('y', padding * 0.6)
          .attr('text-anchor', 'middle')
          .style('font-size', Math.max(18, padding * 0.3))
          .style('font-weight', 'bold')
          .text(`Course Similarity Network (Precomputed, ${mode.toUpperCase()})`);

        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    }

    if (svgReady) {
      initializeGraph();
    }
  }, [dimensions, mode, svgReady]);

  return (
    <div style={{ width: '100vw', height: '100vh', margin: 0, padding: 0, position: 'relative', overflow: 'hidden' }}>
      <svg
        ref={setSvgRef}
        style={{ width: '100vw', height: '100vh', display: 'block', position: 'absolute', top: 0, left: 0 }}
      />
      <div style={{ position: 'absolute', bottom: 0, left: 0, width: '100vw', background: 'rgba(255,255,255,0.95)', textAlign: 'center', fontSize: '1rem', padding: '0.5rem 0' }}>
        Each point represents a course, positioned using precomputed similarity scores. Shape indicates major group, and color distinguishes individual departments.
      </div>
    </div>
  );
}
