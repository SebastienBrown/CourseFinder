import React, {
  useLayoutEffect,
  useRef,
  useState,
  useEffect,
  useCallback,
} from "react";
import * as d3 from "d3";
import {
  loadPrecomputedCourseData,
  applyPCA,
  applyTSNE,
  useLoadData,
} from "./CourseSimilarityPrecomputedProcessor";
import { CURRENT_SEMESTER, AVAILABLE_SEMESTERS, getSemesterDataPaths } from "./config/semesterConfig";
import CoursePopup from "./CoursePopup";
import { supabase } from "./supabaseClient"; // make sure this points to your initialized Supabase client

// Use the globally defined current semester
const semester = CURRENT_SEMESTER;

// === Tranche & Shape Definitions ===
const TRANCHE_SHAPES = {
  "Arts": "circle",
  "Humanities": "square",
  "Sciences": "triangle",
  "Social Sciences": "star",
  "First Year Seminar": "doubleCircle"
};

const TRANCHES = {
  "Arts": ["ARCH", "ARHA", "MUSI", "MUSL", "THDA"],
  "Humanities": [
    "AAPI",
    "AMST",
    "ARAB",
    "ASLC",
    "BLST",
    "CHIN",
    "CLAS",
    "COLQ",
    "EDST",
    "ENGL",
    "ENST",
    "EUST",
    "FAMS",
    "FREN",
    "GERM",
    "GREE",
    "HIST",
    "JAPA",
    "LATI",
    "LJST",
    "LLAS",
    "PHIL",
    "RELI",
    "RUSS",
    "SPAN",
    "SWAG",
  ],
  "Sciences": [
    "ASTR",
    "BCBP",
    "BIOL",
    "CHEM",
    "COSC",
    "GEOL",
    "MATH",
    "NEUR",
    "PHYS",
    "STAT",
  ],
  "Social Sciences": ["ANTH", "ECON", "POSC", "PSYC", "SOCI"],
  "First Year Seminar": ["FYSE"],
};

const getTrancheForDept = (dept) => {
  for (const [tranche, majors] of Object.entries(TRANCHES)) {
    if (majors.includes(dept)) return tranche;
  }
  return "other";
};

const getShapeForDept = (dept) =>
  TRANCHE_SHAPES[getTrancheForDept(dept)] || "circle";

export default function CourseSimilarityPrecomputedGraph({
  mode,
  highlighted = [],
  conflicted = [],
  onSemesterChange
}) {
  const svgRef = useRef(null);
  const [svgReady, setSvgReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [courseDetailsData, setCourseDetailsData] = useState(null);
  const [tsneCoords, setTsneCoords] = useState(null);
  const [dimensions, setDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [selectedSemester, setSelectedSemester] = useState(CURRENT_SEMESTER);
  const [userId, setUserId] = useState(null);

  // Add a new state variable to hold backend output data
const [backendOutputData, setBackendOutputData] = useState(null); 

  // Call onSemesterChange when selectedSemester changes
  useEffect(() => {
    onSemesterChange?.(selectedSemester);
  }, [selectedSemester, onSemesterChange]);

  const setSvgRef = useCallback((node) => {
    svgRef.current = node;
    if (node) setSvgReady(true);
  }, []);

  useEffect(() => {
    if (backendOutputData) {
      console.log("backendOutputData variable contents:", backendOutputData);
    }
  }, [backendOutputData]);

  useEffect(() => {
    function handleResize() {
      setDimensions({ width: window.innerWidth, height: window.innerHeight });
    }
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        
        // Load all data once and get filtered data for the selected semester
        const { courses, courseDetails, tsneCoords: filteredTsneCoords } = await loadPrecomputedCourseData(selectedSemester);
        setGraphData({ courses, similarityMatrix: null });
        setCourseDetailsData(courseDetails);
        setTsneCoords(filteredTsneCoords);
  
        setLoading(false);
      } catch (err) {
        console.error("Error loading data:", err);
        setError(err.message);
        setLoading(false);
      }
    }
    loadData();
  }, [selectedSemester]);

  useEffect(() => {
    async function fetchUser() {
      const {
        data: { user },
        error,
      } = await supabase.auth.getUser();

      if (error) {
        console.error("Error fetching user:", error);
      } else if (user) {
        setUserId(user.id);
      } else {
        console.warn("No user logged in.");
      }
    }
    fetchUser();
  }, []);


  async function fetchBackendData() {
    try {
      // Adjust URL and payload as per your backend
      const response = await fetch("http://127.0.0.1:8000/retrieve_courses", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: userId,            // send user ID here
          // include other data you want to send to backend
        }),
      });
  
      if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`);
      }
  
      const data = await response.json();
      console.log("Backend response data:", data); // <-- log the response here
      setBackendOutputData(data);  // store output here
    } catch (err) {
      setError(err.message);
      console.error("Error fetching backend data:", err);
    }
  }
  
  useEffect(() => {
    if (!svgReady || !userId) return; // wait for svgReady and userId before fetching
    fetchBackendData();
  }, [svgReady, tsneCoords, selectedSemester, userId]);


  useLayoutEffect(() => {
    // Ensure SVG is ready and all necessary data is loaded and in expected format
    if (!svgReady || !graphData || !courseDetailsData || !tsneCoords ||
        !Array.isArray(tsneCoords) || tsneCoords.length === 0 ||
        !Array.isArray(courseDetailsData) || courseDetailsData.length === 0) {
      return;
    }

    try {
      const { courses } = graphData;
      const courseDetails = courseDetailsData;
      const precomputedTSNECoords = tsneCoords;
      let coordinates;

      if (mode === "pca") {
        // coordinates = applyPCA(similarityMatrix);
      } else {
        const codeToIndex = new Map(courses.map((c, i) => [c.code, i]));
        coordinates = Array(courses.length)
          .fill()
          .map(() => [NaN, NaN]);
        precomputedTSNECoords.forEach(({ code, x, y }) => {
          const idx = codeToIndex.get(code);
          if (idx !== undefined) {
            coordinates[idx] = [x, y];
          }
        });
      }

      const allMajors = Object.values(TRANCHES).flat();
      const colorPalette = d3.schemePastel1.concat(d3.schemePastel2);
      const majorColorMap = new Map();
      let colorIndex = 0;
      for (const tranche of Object.values(TRANCHES)) {
        for (const major of tranche) {
          if (!majorColorMap.has(major)) {
            // Use dark gray for FYSE
            const color = major === "FYSE" ? "#4a4a4a" : colorPalette[colorIndex % colorPalette.length];
            majorColorMap.set(major, color);
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
            codes: [course.code], // Initialize with single code
            shape: getShapeForDept(course.department),
            color: majorColorMap.get(course.department) || "#999",
            highlighted: highlighted.includes(course.code),
            conflicted: conflicted.includes(course.code),
          };
        })
        .filter((node) => node && !node.conflicted);

      // Merge nodes with the same coordinates
      const mergedNodes = new Map();
      precomputedTSNECoords.forEach(({ codes, x, y }) => {
        // Ensure currentCodes is always an array, defaulting to ["TBD"] if codes is not a valid array or is empty
        const currentCodes = (Array.isArray(codes) && codes.length > 0) ? codes : ["TBD"];

        const key = `${x},${y}`;
        if (!mergedNodes.has(key)) {
          const firstCode = currentCodes[0] || "TBD";
          const dept = firstCode.split('-')[0];
          mergedNodes.set(key, {
            id: firstCode,
            x,
            y,
            department: dept,
            codes: currentCodes,
            shape: getShapeForDept(dept),
            color: majorColorMap.get(dept) || "#999",
            highlighted: currentCodes.some(code => highlighted.includes(code)),
            conflicted: currentCodes.some(code => conflicted.includes(code)),
          });
        } else {
          const node = mergedNodes.get(key);
          node.codes = [...new Set([...node.codes, ...currentCodes])];
          // Update department based on all codes
          const departments = node.codes.map(code => code.split('-')[0]);
          node.department = departments[0]; // Keep first department as primary
          node.shape = getShapeForDept(node.department);
          node.color = majorColorMap.get(node.department) || "#999";
          node.highlighted = node.codes.some(code => highlighted.includes(code));
          node.conflicted = node.codes.some(code => conflicted.includes(code));
        }
      });

      const finalNodes = Array.from(mergedNodes.values());

      const width = dimensions.width;
      const height = dimensions.height;
      const svg = d3.select(svgRef.current);
      svg.selectAll("*").remove();
      svg
        .attr("width", width)
        .attr("height", height)
        .attr("viewBox", `0 0 ${width} ${height}`);

      // Add zoom behavior
      const zoom = d3.zoom()
        .scaleExtent([0.5, 8]) // Min and max zoom levels
        .on("zoom", (event) => {
          g.attr("transform", event.transform);
        });

      svg.call(zoom);

      // Add a reset zoom button
      const resetButton = svg.append("g")
        .attr("class", "reset-zoom")
        .attr("transform", `translate(${width - 100}, 20)`)
        .style("cursor", "pointer");

      resetButton.append("rect")
        .attr("width", 80)
        .attr("height", 30)
        .attr("rx", 5)
        .attr("fill", "rgba(249, 247, 251, 0.95)")
        .attr("stroke", "#e8e2f2")
        .attr("stroke-width", 1);

      resetButton.append("text")
        .attr("x", 40)
        .attr("y", 20)
        .attr("text-anchor", "middle")
        .attr("dominant-baseline", "middle")
        .style("font-size", "12px")
        .text("Reset View");

      resetButton.on("click", () => {
        svg.transition()
          .duration(750)
          .call(zoom.transform, d3.zoomIdentity);
      });

      const g = svg.append("g");

      g.append("rect")
        .attr("width", width)
        .attr("height", height)
        .attr("fill", "#f9f7fb");

      // Calculate the legend space requirements
      const deptEntries = [...majorColorMap.entries()];
      const legendItemHeight = 20;
      const legendItemWidth = 80; // Width for each column (reduced)
      const colCount = 2; // Left legend columns
      
      // Left legend dimensions
      const leftLegendWidth = legendItemWidth * colCount + 30; // Added padding (reduced)
      const leftLegendHeight = Math.ceil(deptEntries.length / colCount) * legendItemHeight + 40;
      
      // Right legend dimensions
      const rightLegendWidth = leftLegendWidth; // Reduced width
      
      // Create padding for chart area
      const topPadding = 80; // Title space
      const bottomPadding = 40; // Footer space
      const leftPadding = leftLegendWidth;
      const rightPadding = rightLegendWidth + 20;
      
      const xExtent = d3.extent(finalNodes, (d) => d.x);
      const yExtent = d3.extent(finalNodes, (d) => d.y);

      // Add some padding inside the data extent to avoid drawing to the very edge
      const xMargin = (xExtent[1] - xExtent[0]) * 0.05;
      const yMargin = (yExtent[1] - yExtent[0]) * 0.05;

      const xScale = d3
        .scaleLinear()
        .domain([xExtent[0] - xMargin, xExtent[1] + xMargin])
        .range([leftPadding, width - rightPadding]);

      const yScale = d3
        .scaleLinear()
        .domain([yExtent[0] - yMargin, yExtent[1] + yMargin])
        .range([topPadding, height - bottomPadding]);


      const nodeGroup = g
        .append("g")
        .selectAll("g")
        .data(finalNodes)
        .enter()
        .append("g")
        .attr("transform", (d) => `translate(${xScale(d.x)},${yScale(d.y)})`);

      nodeGroup.each(function (d) {
        const group = d3.select(this);
        const baseSize = 6;
        const shapeSize = d.highlighted ? baseSize * 1.5 : baseSize;

        // Get all departments for this course
        const departments = d.codes.map(code => code.split('-')[0]);
        const uniqueDepts = [...new Set(departments)];
        
        // Define scaling factor for non-circle shapes in single-code nodes
        const singleShapeScale = 0.7; // Adjust this value to scale down non-circle shapes

        // Handle single vs. multi-code nodes
        if (d.codes.length === 1) {
          // Single code: Draw a single, unclipped shape
          const dept = departments[0];
          const shape = getShapeForDept(dept);
          const color = majorColorMap.get(dept) || "#999";

          let size = shapeSize; // Use base shapeSize
           switch (shape) {
              case "circle":
                group.append("circle")
                  .attr("r", size)
                  .attr("fill", color);
                break;
              case "doubleCircle":
                // Draw outer circle (unfilled)
                group.append("circle")
                  .attr("r", size * 1.2)
                  .attr("fill", "none")
                  .attr("stroke", color)
                  .attr("stroke-width", 1.5);
                // Draw inner circle (filled)
                group.append("circle")
                  .attr("r", size * 0.8)
                  .attr("fill", color);
                break;
              case "square":
                size = shapeSize * singleShapeScale; // Apply scale
                 group.append("rect")
                  .attr("x", -size)
                  .attr("y", -size)
                  .attr("width", size * 2.5)
                  .attr("height", size * 2.5)
                  .attr("fill", color);
                break;
                case "triangle":
                   size = shapeSize * singleShapeScale; // Apply scale
                   const triangleSymbolSize = size * size * 3; 
                   group.append("path")
                    .attr("d", d3.symbol().type(d3.symbolTriangle).size(triangleSymbolSize)())
                    .attr("fill", color);
                  break;
                case "star":
                   size = shapeSize * singleShapeScale; // Apply scale
                   const starSymbolSize = size * size * 3;
                   group.append("path")
                    .attr("d", d3.symbol().type(d3.symbolStar).size(starSymbolSize)())
                    .attr("fill", color);
                  break;
            }

        } else {
          // Multi code: Draw clipped shape segments (pie chart)

          // Calculate total weight for portions (based on department count)
          const totalWeight = departments.length; // Use total number of departments as weight
          
          // Calculate department weights (how many times each department appears)
          const departmentCounts = {};
          departments.forEach(dept => {
              departmentCounts[dept] = (departmentCounts[dept] || 0) + 1;
          });

          // Create a group for shapes and apply clipping
          const shapeContainer = group.append("g");

          let currentAngle = 0;
          // Sort departments to ensure consistent rendering order for pie slices
          const sortedDepartmentEntries = Object.entries(departmentCounts).sort((a, b) => a[0].localeCompare(b[0]));

          // Define scaling factor for non-circle shapes in multi-code nodes
          const multiShapeScale = 0.8; // Adjust this value to control size difference relative to single-code

          sortedDepartmentEntries.forEach(([dept, count]) => {
            const portion = count / totalWeight;
            const startAngle = currentAngle;
            const endAngle = startAngle + portion * 360;

            const shape = getShapeForDept(dept);
            const color = majorColorMap.get(dept) || "#999";
            
            // Create a clip path for this portion (pie slice)
            const clipPathId = `clip-${d.id}-${dept}-${startAngle}`;
            const clipPath = svg.append("defs").append("clipPath")
              .attr("id", clipPathId);
            
            const arc = d3.arc()
              .innerRadius(0)
              .outerRadius(shapeSize)
              .startAngle(startAngle * Math.PI / 180)
              .endAngle(endAngle * Math.PI / 180);
            
            clipPath.append("path")
              .attr("d", arc());

            // Create a group for this segment and apply the clip path
            const shapeSegmentGroup = shapeContainer.append("g")
               .attr("clip-path", `url(#${clipPathId})`);

            // Draw the full shape within the clipped area with adjusted size for non-circles
            let currentShapeSize = shapeSize; // Start with base size
             switch (shape) {
                case "circle":
                  // Circle size remains the same as single-code
                  shapeSegmentGroup.append("circle")
                    .attr("r", currentShapeSize)
                    .attr("fill", color);
                  break;
                case "doubleCircle":
                  // Draw outer circle (unfilled)
                  shapeSegmentGroup.append("circle")
                    .attr("r", currentShapeSize * 1.2)
                    .attr("fill", "none")
                    .attr("stroke", color)
                    .attr("stroke-width", 1.5);
                  // Draw inner circle (filled)
                  shapeSegmentGroup.append("circle")
                    .attr("r", currentShapeSize * 0.8)
                    .attr("fill", color);
                  break;
                case "square":
                  // Scale down square size for multi-code
                  currentShapeSize = shapeSize * multiShapeScale; // Apply multi-shape scale
                  shapeSegmentGroup.append("rect")
                    .attr("x", -currentShapeSize)
                    .attr("y", -currentShapeSize)
                    .attr("width", currentShapeSize * 2)
                    .attr("height", currentShapeSize * 2)
                    .attr("fill", color);
                  break;
                case "triangle":
                  // Scale down triangle size for multi-code, maintaining visual proportion
                  currentShapeSize = shapeSize * multiShapeScale; // Apply multi-shape scale
                  const multiTriangleSymbolSize = currentShapeSize * currentShapeSize * 3; // Use same area multiplier as single-code
                   shapeSegmentGroup.append("path")
                    .attr("d", d3.symbol().type(d3.symbolTriangle).size(multiTriangleSymbolSize)())
                    .attr("fill", color);
                  break;
                case "star":
                  // Scale down star size for multi-code, maintaining visual proportion
                  currentShapeSize = shapeSize * multiShapeScale; // Apply multi-shape scale
                  const multiStarSymbolSize = currentShapeSize * currentShapeSize * 2.7; // Use same area multiplier as single-code
                   shapeSegmentGroup.append("path")
                    .attr("d", d3.symbol().type(d3.symbolStar).size(multiStarSymbolSize)())
                    .attr("fill", color);
                  break;
            }

            currentAngle = endAngle;
          });
        }

        group.style("cursor", "pointer").on("click", () => {
          const full = courseDetails.find((entry) =>
            entry.course_codes.some(code => d.codes.includes(code))
          );
          setSelectedCourse(full || { course_title: "Unknown", ...d });
        });
      });

      // Update label handling to scale with zoom
      nodeGroup
        .append("text")
        .attr("text-anchor", "middle")
        .attr("dy", (d) => -8 + Math.random() * 6 - 3)
        .attr("font-size", "7px")
        .attr("fill", "#333")
        .attr("class", "node-label") // Add class for styling
        .text((d) => d.codes.length > 1 ? `${d.codes[0]}...` : d.codes[0]);

      // === DEPARTMENT LEGEND (2-COLUMN LAYOUT) ===
      const legendPadding = 20;
      const legendItemCount = deptEntries.length;
      const legendRows = Math.ceil(legendItemCount / colCount);
      
      // Create background for legend
      svg.append("rect")
        .attr("x", legendPadding - 10)
        .attr("y", legendPadding - 10)
        .attr("width", leftLegendWidth - 20)
        .attr("height", leftLegendHeight)
        .attr("fill", "rgba(249, 247, 251, 0.95)")
        .attr("stroke", "#e8e2f2")
        .attr("stroke-width", 1)
        .attr("rx", 5);
      
      // Add title to legend
      svg.append("text")
        .attr("x", legendPadding)
        .attr("y", legendPadding + 15)
        .attr("text-anchor", "start")
        .style("font-weight", "bold")
        .style("font-size", "14px")
        .text("Departments");
        
      const legend = svg
        .append("g")
        .attr("transform", `translate(${legendPadding}, ${legendPadding + 30})`)
        .attr("class", "legend");

      deptEntries.forEach((entry, i) => {
        const [dept, color] = entry;
        const col = Math.floor(i / legendRows);
        const row = i % legendRows;
        
        const legendItem = legend
          .append("g")
          .attr("transform", `translate(${col * legendItemWidth}, ${row * legendItemHeight})`);

        const shape = getShapeForDept(dept);
        const size = 6;

        switch (shape) {
          case "circle":
            legendItem.append("circle")
              .attr("r", size)
              .attr("fill", color);
            break;
          case "doubleCircle":
            // Draw outer circle (unfilled)
            legendItem.append("circle")
              .attr("r", size * 1.2)
              .attr("fill", "none")
              .attr("stroke", color)
              .attr("stroke-width", 1.5);
            // Draw inner circle (filled)
            legendItem.append("circle")
              .attr("r", size * 0.8)
              .attr("fill", color);
            break;
          case "square":
            legendItem
              .append("rect")
              .attr("x", -size)
              .attr("y", -size)
              .attr("width", size * 2)
              .attr("height", size * 2)
              .attr("fill", color);
            break;
          case "triangle":
            legendItem
              .append("path")
              .attr(
                "d",
                d3
                  .symbol()
                  .type(d3.symbolTriangle)
                  .size(size * size * 4)() // Reverted size multiplier
              )
              .attr("fill", color);
            break;
          case "star":
            legendItem
              .append("path")
              .attr(
                "d",
                d3
                  .symbol()
                  .type(d3.symbolStar)
                  .size(size * size * 4)() // Reverted size multiplier
              )
              .attr("fill", color);
            break;
        }

        legendItem
          .append("text")
          .attr("x", 10)
          .attr("y", 5)
          .text(dept)
          .style("font-size", "10px");
      });

      // === TRANCHE SHAPE LEGEND (RIGHT SIDE) ===
      const shapeEntries = Object.entries(TRANCHE_SHAPES);
      const shapeLegendX = legendPadding;
      const shapeLegendY = leftLegendHeight+25;
      const shapeLegendHeight = shapeEntries.length * legendItemHeight + 30;
      
      // Background for shape legend
      svg.append("rect")
        .attr("x", shapeLegendX - 10)
        .attr("y", shapeLegendY - 10)
        .attr("width", leftLegendWidth-20)
        .attr("height", shapeLegendHeight)
        .attr("fill", "rgba(249, 247, 251, 0.95)")
        .attr("stroke", "#e8e2f2")
        .attr("stroke-width", 1)
        .attr("rx", 5);
        
      const shapeLegend = svg
        .append("g")
        .attr("transform", `translate(${shapeLegendX}, ${shapeLegendY})`)
        .attr("class", "shape-legend");

      // Title for shape legend
      shapeLegend
        .append("text")
        .attr("x", 0)
        .attr("y", 5)
        .text("Department Groups")
        .style("font-weight", "bold")
        .style("font-size", "14px");

      shapeEntries.forEach(([tranche, shapeType], i) => {
        const legendItem = shapeLegend
          .append("g")
          .attr("transform", `translate(0, ${i * legendItemHeight + 25})`);

        const size = 6;
        // Use a standard color for the shape legend
        const color = "#666";

        switch (shapeType) {
          case "circle":
            legendItem.append("circle")
              .attr("r", size)
              .attr("fill", color);
            break;
          case "doubleCircle":
            // Draw outer circle (unfilled)
            legendItem.append("circle")
              .attr("r", size * 1.2)
              .attr("fill", "none")
              .attr("stroke", color)
              .attr("stroke-width", 1.5);
            // Draw inner circle (filled)
            legendItem.append("circle")
              .attr("r", size * 0.8)
              .attr("fill", color);
            break;
          case "square":
            legendItem
              .append("rect")
              .attr("x", -size)
              .attr("y", -size)
              .attr("width", size * 2)
              .attr("height", size * 2)
              .attr("fill", color);
            break;
          case "triangle":
            legendItem
              .append("path")
              .attr(
                "d",
                d3
                  .symbol()
                  .type(d3.symbolTriangle)
                  .size(size * size * 4)() // Reverted size multiplier
              )
              .attr("fill", color);
            break;
          case "star":
            legendItem
              .append("path")
              .attr(
                "d",
                d3
                  .symbol()
                  .type(d3.symbolStar)
                  .size(size * size * 4)() // Reverted size multiplier
              )
              .attr("fill", color);
            break;
        }

        legendItem
          .append("text")
          .attr("x", 12)
          .attr("y", 5)
          .text(tranche.charAt(0).toUpperCase() + tranche.slice(1)) // Capitalize
          .style("font-size", "10px");
      });

      // Optional: Add a visual separator between legends and graph
      svg.append("rect")
        .attr("x", leftPadding - 10)
        .attr("y", 0)
        .attr("width", 1)
        .attr("height", height)
        .attr("fill", "#e8e2f2");

      // Main title with adjusted positioning
      svg
        .append("text")
        .attr("x", leftPadding + (width - leftPadding - rightPadding) / 2)
        .attr("y", topPadding * 0.6)
        .attr("text-anchor", "middle")
        .style("font-size", "18px")
        .style("font-weight", "bold")
        .text(
          `Course Similarity Graph`
        );

      // Add CSS to handle label scaling
      const style = document.createElement('style');
      style.textContent = `
        .node-label {
          pointer-events: none;
          text-rendering: geometricPrecision;
        }
      `;
      document.head.appendChild(style);

      setLoading(false);
    } catch (err) {
      console.error('Error initializing graph:', err);
      setError(err.message);
      setLoading(false);
    }
  }, [
    dimensions,
    mode,
    svgReady,
    JSON.stringify(highlighted),
    JSON.stringify(conflicted),
    graphData,
    courseDetailsData,
    tsneCoords,
    selectedSemester,
  ]);

  return (
    <div className="relative w-full max-w-[1200px] mx-auto h-[80vh] bg-[#f9f7fb] shadow-md rounded-xl overflow-hidden border border-[#e8e2f2]">
      <svg
        ref={setSvgRef}
        className="w-full h-full absolute top-0 left-0"
      ></svg>

      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/50">
          <div className="text-lg font-medium">Loading visualization...</div>
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/80">
          <div className="text-red-500 text-lg font-medium">Error: {error}</div>
        </div>
      )}

      <CoursePopup
        course={selectedCourse}
        onClose={() => setSelectedCourse(null)}
      />

      {/* Semester Slider */}
      <div className="absolute bottom-0 left-0 w-full bg-white/90 p-4 border-t border-[#e8e2f2]">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Semester:</span>
          <span className="text-sm text-gray-600">{selectedSemester}</span>
        </div>
        <input
          type="range"
          min="0"
          max={AVAILABLE_SEMESTERS.length - 1}
          value={AVAILABLE_SEMESTERS.indexOf(selectedSemester)}
          onChange={(e) => setSelectedSemester(AVAILABLE_SEMESTERS[e.target.value])}
          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
        />
        <div className="flex justify-between mt-1">
          {AVAILABLE_SEMESTERS.map((sem) => (
            <span
              key={sem}
              className="text-xs text-gray-500"
              style={{
                color: sem === selectedSemester ? '#3f1f69' : '#6b7280',
                fontWeight: sem === selectedSemester ? 'bold' : 'normal'
              }}
            >
              {sem}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}