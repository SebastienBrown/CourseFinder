import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function CourseSimilarityGraph() {
  const svgRef = useRef(null);

  useEffect(() => {
    const courseData = [
      {
        course_codes: ['AMST-117'],
        compared_courses: [
          { course_codes: ['EDST-200', 'AMST-200', 'SOCI-200'], similarity_score: 0.814 },
          { course_codes: ['AMST-206', 'LLAS-200'], similarity_score: 0.801 },
          { course_codes: ['EDST-120', 'AMST-220', 'ENGL-120'], similarity_score: 0.762 },
          { course_codes: ['AMST-221'], similarity_score: 0.814 },
          { course_codes: ['AMST-222', 'EUST-217', 'GERM-222'], similarity_score: 0.768 },
          { course_codes: ['AMST-224'], similarity_score: 0.777 },
          { course_codes: ['AMST-225'], similarity_score: 0.792 },
          { course_codes: ['EDST-240', 'AMST-240', 'SWAG-243'], similarity_score: 0.777 },
          { course_codes: ['AMST-309', 'BLST-309', 'SWAG-311'], similarity_score: 0.829 },
        ]
      }
    ];

    const getNodeKey = (codes) => codes.sort().join('/');
    const allCourseGroups = new Set();

    courseData.forEach(course => {
      allCourseGroups.add(getNodeKey(course.course_codes));
      course.compared_courses.forEach(c => allCourseGroups.add(getNodeKey(c.course_codes)));
    });

    const nodes = Array.from(allCourseGroups).map(codeGroup => ({
      id: codeGroup,
      codes: codeGroup.split('/')
    }));

    const links = [];
    const processedPairs = new Set();

    courseData.forEach(course => {
      const sourceKey = getNodeKey(course.course_codes);
      course.compared_courses.forEach(compared => {
        const targetKey = getNodeKey(compared.course_codes);
        const pairKey = [sourceKey, targetKey].sort().join('|');
        if (!processedPairs.has(pairKey) && sourceKey !== targetKey) {
          links.push({
            source: sourceKey,
            target: targetKey,
            value: compared.similarity_score
          });
          processedPairs.add(pairKey);
        }
      });
    });

    const width = 800;
    const height = 600;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    svg
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('width', '100%')
      .attr('height', '100%');

    svg.append('rect')
      .attr('width', width)
      .attr('height', height)
      .attr('fill', '#f8f9fa')
      .attr('stroke', '#dee2e6')
      .attr('stroke-width', 1);

    const centerX = width / 2;
    const centerY = height / 2;
    const maxRadius = 500; // max distance from center
    
    const centerNode = nodes.find(n => n.id === 'AMST-117');
    
    // Place center node
    centerNode.x = centerX;
    centerNode.y = centerY;
    
    // Arrange others radially based on similarity
    const peripheralNodes = nodes.filter(n => n !== centerNode);
    peripheralNodes.forEach((node, i) => {
      const link = links.find(l => 
        (l.source === centerNode.id && l.target === node.id) || 
        (l.target === centerNode.id && l.source === node.id)
      );
      
      const angle = (i / peripheralNodes.length) * 2 * Math.PI;
      // Use 1-similarity as the distance factor
      const similarity = link ? link.value : 0.5; // default similarity if missing
      const distance = maxRadius * (1 - similarity);
      
      node.x = centerX + distance * Math.cos(angle);
      node.y = centerY + distance * Math.sin(angle);
    });

    const nodeMap = new Map(nodes.map(n => [n.id, n]));

    // Assign source/target positions to links
    links.forEach(link => {
      link.source = nodeMap.get(link.source);
      link.target = nodeMap.get(link.target);
    });

    const link = svg.append('g')
      .selectAll('line')
      .data(links)
      .enter()
      .append('line')
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', d => Math.max(1, d.value * 3));

    const linkLabel = svg.append('g')
      .selectAll('text')
      .data(links)
      .enter()
      .append('text')
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2)
      .attr('dy', -3)
      .attr('text-anchor', 'middle')
      .attr('font-size', '10px')
      .attr('fill', '#555')
      .text(d => Math.round(d.value * 100));

    const getPrimaryDept = (node) => node.codes[0].split('-')[0];

    const colorMap = {
      AMST: '#4e79a7',
      EDST: '#f28e2c',
      SOCI: '#e15759',
      LLAS: '#76b7b2',
      ENGL: '#59a14f',
      EUST: '#edc949',
      GERM: '#af7aa1',
      SWAG: '#ff9da7',
      BLST: '#9c755f'
    };

    const nodeGroup = svg.append('g')
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .attr('transform', d => `translate(${d.x},${d.y})`);

    nodeGroup.append('circle')
      .attr('r', d => 25 + (d.codes.length > 1 ? 5 : 0))
      .attr('fill', d => colorMap[getPrimaryDept(d)] || '#bab0ab')
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5);

    nodeGroup.each(function (d) {
      const node = d3.select(this);
      const lineHeight = 12;
      const totalHeight = d.codes.length * lineHeight;
      const startY = -totalHeight / 2 + lineHeight / 2;

      d.codes.forEach((code, i) => {
        node.append('text')
          .attr('text-anchor', 'middle')
          .attr('dy', startY + (i * lineHeight))
          .attr('font-size', '10px')
          .attr('fill', 'white')
          .attr('font-weight', 'bold')
          .text(code);
      });
    });

    // Legend
    const legend = svg.append('g')
      .attr('transform', `translate(20, 20)`);

    Object.keys(colorMap).forEach((dept, i) => {
      const row = legend.append('g')
        .attr('transform', `translate(0, ${i * 20})`);

      row.append('rect')
        .attr('width', 15)
        .attr('height', 15)
        .attr('fill', colorMap[dept]);

      row.append('text')
        .attr('x', 20)
        .attr('y', 12)
        .text(dept)
        .style('font-size', '12px');
    });

    svg.append('text')
      .attr('x', width / 2)
      .attr('y', 30)
      .attr('text-anchor', 'middle')
      .style('font-size', '20px')
      .style('font-weight', 'bold')
      .text('Course Similarity Network');

    svg.append('text')
      .attr('x', width / 2)
      .attr('y', 50)
      .attr('text-anchor', 'middle')
      .style('font-size', '12px')
      .text('Numbers on edges represent similarity scores (0-100)');

  }, []);

  return (
    <div className="flex flex-col items-center justify-center p-4">
      <svg
        ref={svgRef}
        className="w-full h-full max-w-4xl border border-gray-300 rounded shadow-lg"
        style={{ minHeight: '600px' }}
      />
      <p className="mt-4 text-sm text-gray-600">
        Each node represents a course or group of cross-listed courses. Numbers on edges show similarity scores (0-100).
        Courses with higher similarity are placed closer together.
      </p>
    </div>
  );
}