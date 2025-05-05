import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function CourseSimilarityGraph() {
  const svgRef = useRef(null);
  
  useEffect(() => {
    // Data preparation
    const courseData = [
      {
        "course_codes": ["AMST-117"],
        "compared_courses": [
          { "course_codes": ["EDST-200", "AMST-200", "SOCI-200"], "similarity_score": 0.8144880108076742 },
          { "course_codes": ["AMST-206", "LLAS-200"], "similarity_score": 0.8007958539057355 },
          { "course_codes": ["EDST-120", "AMST-220", "ENGL-120"], "similarity_score": 0.7621657089016289 },
          { "course_codes": ["AMST-221"], "similarity_score": 0.8137644527059013 },
          { "course_codes": ["AMST-222", "EUST-217", "GERM-222"], "similarity_score": 0.7683744217329497 },
          { "course_codes": ["AMST-224"], "similarity_score": 0.7774069122618295 },
          { "course_codes": ["AMST-225"], "similarity_score": 0.7924241746700348 },
          { "course_codes": ["EDST-240", "AMST-240", "SWAG-243"], "similarity_score": 0.7771912952230373 },
          { "course_codes": ["AMST-309", "BLST-309", "SWAG-311"], "similarity_score": 0.8286853670701964 }
        ]
      },
      {
        "course_codes": ["EDST-200", "AMST-200", "SOCI-200"],
        "compared_courses": [
          { "course_codes": ["AMST-117"], "similarity_score": 0.8144880108076742 },
          { "course_codes": ["AMST-206", "LLAS-200"], "similarity_score": 0.8170053172888235 },
          { "course_codes": ["EDST-120", "AMST-220", "ENGL-120"], "similarity_score": 0.7943254501780199 },
          { "course_codes": ["AMST-221"], "similarity_score": 0.8490741648444965 },
          { "course_codes": ["AMST-222", "EUST-217", "GERM-222"], "similarity_score": 0.7845018450719587 },
          { "course_codes": ["AMST-224"], "similarity_score": 0.7590823602310848 },
          { "course_codes": ["AMST-225"], "similarity_score": 0.815906384708068 },
          { "course_codes": ["EDST-240", "AMST-240", "SWAG-243"], "similarity_score": 0.8098763123760957 },
          { "course_codes": ["AMST-309", "BLST-309", "SWAG-311"], "similarity_score": 0.816997498619652 }
        ]
      },
      {
        "course_codes": ["AMST-206", "LLAS-200"],
        "compared_courses": [
          { "course_codes": ["AMST-117"], "similarity_score": 0.8007958539057355 },
          { "course_codes": ["EDST-200", "AMST-200", "SOCI-200"], "similarity_score": 0.8170053172888235 },
          { "course_codes": ["EDST-120", "AMST-220", "ENGL-120"], "similarity_score": 0.7667456697629633 },
          { "course_codes": ["AMST-221"], "similarity_score": 0.7848273931030125 },
          { "course_codes": ["AMST-222", "EUST-217", "GERM-222"], "similarity_score": 0.7863217439176867 },
          { "course_codes": ["AMST-224"], "similarity_score": 0.7693872376994885 },
          { "course_codes": ["AMST-225"], "similarity_score": 0.7998134025330792 },
          { "course_codes": ["EDST-240", "AMST-240", "SWAG-243"], "similarity_score": 0.8132284328374446 },
          { "course_codes": ["AMST-309", "BLST-309", "SWAG-311"], "similarity_score": 0.8221037692549494 }
        ]
      }
    ];

    // Create a unified list of all course codes
    const allCourseCodes = new Set();
    courseData.forEach(course => {
      course.course_codes.forEach(code => allCourseCodes.add(code));
      course.compared_courses.forEach(compared => {
        compared.course_codes.forEach(code => allCourseCodes.add(code));
      });
    });

    // Create nodes for each unique course code
    const nodes = Array.from(allCourseCodes).map(code => ({ id: code }));

    // Create links between courses with similarity scores
    const links = [];
    const processedPairs = new Set();

    courseData.forEach(course => {
      const sourceCodes = course.course_codes;
      
      course.compared_courses.forEach(compared => {
        const targetCodes = compared.course_codes;
        
        // Create a unique key for this pair to avoid duplicates
        const pairKey = [...sourceCodes, ...targetCodes].sort().join('|');
        
        if (!processedPairs.has(pairKey) && sourceCodes.some(code => allCourseCodes.has(code)) && 
            targetCodes.some(code => allCourseCodes.has(code))) {
          
          // Convert similarity to distance (higher similarity = lower distance)
          const distance = Math.round(compared.similarity_score * 100);
          
          // Add each pair combination
          sourceCodes.forEach(source => {
            targetCodes.forEach(target => {
              if (source !== target) {
                links.push({
                  source: source,
                  target: target,
                  value: compared.similarity_score,
                  distance: distance
                });
              }
            });
          });
          
          processedPairs.add(pairKey);
        }
      });
    });

    // Create the graph
    const width = 800;
    const height = 600;
    
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    
    svg
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("width", "100%")
      .attr("height", "100%");

    // Add a border and background
    svg.append("rect")
      .attr("width", width)
      .attr("height", height)
      .attr("fill", "#f8f9fa")
      .attr("stroke", "#dee2e6")
      .attr("stroke-width", 1);

    // Improved distance formula: Higher similarity = shorter distance
    // Using an exponential function to make highly similar courses much closer
    const distanceFormula = (similarityScore) => {
      // Map similarity score 0.75-0.85 to distances 150-50
      // Using an inverse exponential relationship
      return 150 * Math.pow(0.5, (similarityScore - 0.75) * 10);
    };

    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(d => distanceFormula(d.value)))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(60));

    // Create the links
    const link = svg.append("g")
      .selectAll("line")
      .data(links)
      .enter()
      .append("line")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", d => Math.max(1, d.value * 3));

    // Create the link labels (distance values)
    const linkLabel = svg.append("g")
      .selectAll("text")
      .data(links)
      .enter()
      .append("text")
      .attr("dy", -3)
      .attr("text-anchor", "middle")
      .attr("font-size", "10px")
      .attr("fill", "#555")
      .text(d => d.distance);

    // Create a group for each node
    const nodeGroup = svg.append("g")
      .selectAll("g")
      .data(nodes)
      .enter()
      .append("g");

    // Add circle for each node
    nodeGroup.append("circle")
      .attr("r", 25)
      .attr("fill", d => {
        // Color nodes by department prefix
        const dept = d.id.split('-')[0];
        const colorMap = {
          'AMST': '#4e79a7',
          'EDST': '#f28e2c',
          'SOCI': '#e15759',
          'LLAS': '#76b7b2',
          'ENGL': '#59a14f',
          'EUST': '#edc949',
          'GERM': '#af7aa1',
          'SWAG': '#ff9da7',
          'BLST': '#9c755f'
        };
        return colorMap[dept] || '#bab0ab';
      })
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5);

    // Add course code label
    nodeGroup.append("text")
      .attr("text-anchor", "middle")
      .attr("dy", 4)
      .attr("font-size", "10px")
      .attr("fill", "white")
      .attr("font-weight", "bold")
      .text(d => d.id);

    // Add titles for tooltips
    nodeGroup.append("title")
      .text(d => d.id);

    // Update positions on each tick of the simulation
    simulation.on("tick", () => {
      link
        .attr("x1", d => Math.max(30, Math.min(width - 30, d.source.x)))
        .attr("y1", d => Math.max(30, Math.min(height - 30, d.source.y)))
        .attr("x2", d => Math.max(30, Math.min(width - 30, d.target.x)))
        .attr("y2", d => Math.max(30, Math.min(height - 30, d.target.y)));

      nodeGroup.attr("transform", d => `translate(${Math.max(30, Math.min(width - 30, d.x))},${Math.max(30, Math.min(height - 30, d.y))})`);

      linkLabel
        .attr("x", d => (Math.max(30, Math.min(width - 30, d.source.x)) + Math.max(30, Math.min(width - 30, d.target.x))) / 2)
        .attr("y", d => (Math.max(30, Math.min(height - 30, d.source.y)) + Math.max(30, Math.min(height - 30, d.target.y))) / 2);
    });

    // Add a legend for department colors
    const depts = ['AMST', 'EDST', 'SOCI', 'LLAS', 'ENGL', 'EUST', 'GERM', 'SWAG', 'BLST'];
    const colorMap = {
      'AMST': '#4e79a7',
      'EDST': '#f28e2c', 
      'SOCI': '#e15759',
      'LLAS': '#76b7b2',
      'ENGL': '#59a14f',
      'EUST': '#edc949',
      'GERM': '#af7aa1',
      'SWAG': '#ff9da7',
      'BLST': '#9c755f'
    };

    const legend = svg.append("g")
      .attr("transform", `translate(20, 20)`);

    depts.forEach((dept, i) => {
      const legendRow = legend.append("g")
        .attr("transform", `translate(0, ${i * 20})`);
      
      legendRow.append("rect")
        .attr("width", 15)
        .attr("height", 15)
        .attr("fill", colorMap[dept]);
      
      legendRow.append("text")
        .attr("x", 20)
        .attr("y", 12.5)
        .attr("text-anchor", "start")
        .style("font-size", "12px")
        .text(dept);
    });

    // Add title
    svg.append("text")
      .attr("x", width / 2)
      .attr("y", 30)
      .attr("text-anchor", "middle")
      .style("font-size", "20px")
      .style("font-weight", "bold")
      .text("Course Similarity Network");

    // Add subtitle explaining the edges
    svg.append("text")
      .attr("x", width / 2)
      .attr("y", 50)
      .attr("text-anchor", "middle")
      .style("font-size", "12px")
      .text("Numbers on edges represent similarity scores (0-100)");

  }, []);

  return (
    <div className="flex flex-col items-center justify-center p-4">
      <svg 
        ref={svgRef} 
        className="w-full h-full max-w-4xl border border-gray-300 rounded shadow-lg"
        style={{ minHeight: '600px' }}
      />
      <p className="mt-4 text-sm text-gray-600">
        Each node represents a course, colored by department. The numbers on the edges represent similarity scores (0-100).
        Higher similarity scores result in closer node placement.
      </p>
    </div>
  );
}