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
} from "./CourseSimilarityPrecomputedProcessor";
import precomputedTSNECoords from "./data/precomputed_tsne_coords.json";
import courseDetails from "./data/amherst_courses_2324S.json";
import CoursePopup from "./CoursePopup";

// === Tranche & Shape Definitions ===
const TRANCHE_SHAPES = {
  "Arts": "circle",
  "Humanities": "square",
  "Sciences": "triangle",
  "Social sciences": "star",
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
}) {
  const svgRef = useRef(null);
  const [svgReady, setSvgReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dimensions, setDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });
  const [selectedCourse, setSelectedCourse] = useState(null);

  const setSvgRef = useCallback((node) => {
    svgRef.current = node;
    if (node) setSvgReady(true);
  }, []);

  useEffect(() => {
    function handleResize() {
      setDimensions({ width: window.innerWidth, height: window.innerHeight });
    }
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useLayoutEffect(() => {
    async function initializeGraph() {
      try {
        setLoading(true);
        if (!svgRef.current) {
          console.error("[Graph] SVG element is null, skipping D3 drawing.");
          setLoading(false);
          return;
        }

        const { courses, similarityMatrix } = loadPrecomputedCourseData();
        let coordinates;

        if (mode === "pca") {
          coordinates = applyPCA(similarityMatrix);
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
              majorColorMap.set(
                major,
                colorPalette[colorIndex % colorPalette.length]
              );
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
              color: majorColorMap.get(course.department) || "#999",
              highlighted: highlighted.includes(course.code),
              conflicted: conflicted.includes(course.code),
            };
          })
          .filter((node) => node && !node.conflicted);

        const width = dimensions.width;
        const height = dimensions.height;
        const svg = d3.select(svgRef.current);
        svg.selectAll("*").remove();
        svg
          .attr("width", width)
          .attr("height", height)
          .attr("viewBox", `0 0 ${width} ${height}`);
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
        
        const xExtent = d3.extent(nodes, (d) => d.x);
        const yExtent = d3.extent(nodes, (d) => d.y);

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
          .data(nodes)
          .enter()
          .append("g")
          .attr("transform", (d) => `translate(${xScale(d.x)},${yScale(d.y)})`);

        nodeGroup.each(function (d) {
          const group = d3.select(this);
          const baseSize = 6;
          const shapeColor = d.conflicted
            ? "#856cb0" // this allows conflicted courses to be shown in a different color, but this is not currently used right now. We can use it later if we want to toggle show conflicted courses
            : d.highlighted
            ? "#311a4d" // user-selected course
            : d.color;
          const shapeSize = d.highlighted ? baseSize * 1.5 : baseSize;

          group.style("cursor", "pointer").on("click", () => {
            const full = courseDetails.find((entry) =>
              entry.course_codes.includes(d.id)
            );
            setSelectedCourse(full || { course_title: "Unknown", ...d });
          });

          switch (d.shape) {
            case "circle":
              group
                .append("circle")
                .attr("r", shapeSize)
                .attr("fill", shapeColor)
                .attr("stroke", "#fff")
                .attr("stroke-width", 1);
              break;
            case "square":
              group
                .append("rect")
                .attr("x", -shapeSize)
                .attr("y", -shapeSize)
                .attr("width", shapeSize * 2)
                .attr("height", shapeSize * 2)
                .attr("fill", shapeColor)
                .attr("stroke", "#fff")
                .attr("stroke-width", 0.5);
              break;
            case "triangle":
              group
                .append("path")
                .attr(
                  "d",
                  d3
                    .symbol()
                    .type(d3.symbolTriangle)
                    .size(shapeSize * shapeSize * 6)()
                )
                .attr("fill", shapeColor)
                .attr("stroke", "#fff")
                .attr("stroke-width", 1);
              break;
            case "star":
              group
                .append("path")
                .attr(
                  "d",
                  d3
                    .symbol()
                    .type(d3.symbolStar)
                    .size(shapeSize * shapeSize * 6)()
                )
                .attr("fill", shapeColor)
                .attr("stroke", "#fff")
                .attr("stroke-width", 1);
              break;
            default:
              group
                .append("circle")
                .attr("r", shapeSize)
                .attr("fill", shapeColor)
                .attr("stroke", "#fff")
                .attr("stroke-width", 1);
          }
        });

        nodeGroup
          .append("text")
          .attr("text-anchor", "middle")
          .attr("dy", (d) => -8 + Math.random() * 6 - 3)
          .attr("font-size", "7px")
          .attr("fill", "#333")
          .text((d) => d.id);

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
                    .size(size * size * 6)()
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
                    .size(size * size * 6)()
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
                    .size(size * size * 6)()
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
                    .size(size * size * 6)()
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
            `Course Similarity Network (Precomputed, ${mode.toUpperCase()})`
          );

        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    }

    if (svgReady) {
      initializeGraph();
    }
  }, [
    dimensions,
    mode,
    svgReady,
    JSON.stringify(highlighted),
    JSON.stringify(conflicted),
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

      <div className="absolute bottom-0 left-0 w-full bg-white/90 text-center text-sm py-2 border-t border-[#e8e2f2]">
        Each point represents a course, positioned using precomputed similarity
        scores. Shape indicates major group, and color distinguishes individual
        departments.
      </div>
    </div>
  );
}