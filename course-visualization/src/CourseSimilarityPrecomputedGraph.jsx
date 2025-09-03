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
import { CURRENT_SEMESTER, AVAILABLE_SEMESTERS, getSemesterDataPaths } from "./config";
import CoursePopup from "./CoursePopup";
import { supabase } from "./supabaseClient"; // make sure this points to your initialized Supabase client
// import { API_BASE_URL } from './config';
import Settings from './Settings';
import html2canvas from 'html2canvas'; // Import html2canvas
import OnboardingPopup from './OnboardingPopup';

// Use the globally defined current semester
// const semester = CURRENT_SEMESTER;
const backendUrl=process.env.REACT_APP_BACKEND_URL;

// === Tranche & Shape Definitions ===
const TRANCHE_SHAPES = {
  "Arts": "circle",
  "Humanities": "square",
  "Sciences": "triangle",
  "Social Sciences": "star",
  "First Year Seminar": "doubleCircle"
};

// Helper function to normalize department codes
const normalizeDepartment = (dept) => {
  if (dept === "WAGS") return "SWAG";
  return dept;
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
    "WAGS",
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
  const normalizedDept = normalizeDepartment(dept);
  for (const [tranche, majors] of Object.entries(TRANCHES)) {
    if (majors.includes(normalizedDept)) return tranche;
  }
  return "other";
};

const getShapeForDept = (dept) =>
  TRANCHE_SHAPES[getTrancheForDept(dept)] || "circle";

export default function CourseSimilarityPrecomputedGraph({
  mode,
  highlighted,
  conflicted,
  onSemesterChange,
  onHighlight,
  onConflicted,
  isPublicMode = false,
  showOnboarding,
  setShowOnboarding
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
  const [activeTab, setActiveTab] = useState(isPublicMode ? 'thisSemester' : 'thisSemester');
  const [showConflicts, setShowConflicts] = useState(true);
  const mapContainerRef = useRef(null);
  const contentToCaptureRef = useRef(null);
  const [legendCollapsed, setLegendCollapsed] = useState(false);


  // Add a new state variable to hold backend output data
  const [backendOutputData, setBackendOutputData] = useState(null);

  // Add new state for history data
  const [historyData, setHistoryData] = useState(null);
  const [userCourseCodes, setUserCourseCodes] = useState([]);

  const [showSettings, setShowSettings] = useState(false);

  // Check if this is the user's first visit
  useEffect(() => {
    const hasSeenOnboarding = localStorage.getItem('hasSeenOnboarding');
    if (!hasSeenOnboarding) {
      setShowOnboarding(true);
    }
  }, []);

  // Log dimensions when they change
  useEffect(() => {
    console.log('Current dimensions:', dimensions);
  }, [dimensions]);

  // Combined effect to handle semester changes and tab switches
  useEffect(() => {
    onSemesterChange?.(selectedSemester);
    
    // Only populate user courses if we're in Single Semester View and not in public mode
    if (activeTab === 'thisSemester' && !isPublicMode && userCourseCodes && userCourseCodes.length > 0) {
      console.log('Tab/UserCourses effect triggered:', { activeTab, selectedSemester, userCourseCodesLength: userCourseCodes?.length, isPublicMode });
      
      const userCoursesForSemester = userCourseCodes
        .filter(uc => uc.semester === selectedSemester)
        .map(uc => uc.code);
      
      console.log(`Populating user courses for semester ${selectedSemester}:`, userCoursesForSemester);
      
      if (userCoursesForSemester.length > 0) {
        onHighlight(userCoursesForSemester);
      } else {
        // Clear highlights if no courses for this semester
        onHighlight([]);
      }
    }
  }, [selectedSemester, activeTab, userCourseCodes, isPublicMode, onSemesterChange, onHighlight]);

  const setSvgRef = useCallback((node) => {
    svgRef.current = node;
    if (node) setSvgReady(true);
  }, []);

  console.log("Conflicted array:", conflicted);
  

  useEffect(() => {
    function handleResize() {
      setDimensions({ width: window.innerWidth, height: window.innerHeight });
    }
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Effect to extract user course codes whenever backend data is available
  useEffect(() => {
    if (backendOutputData && !isPublicMode) {
      console.log("Extracting user course codes from backend data:", backendOutputData);
      
      // Get the user's course codes with their semesters for highlighting
      const userCourses = backendOutputData
        .filter(course => course && course.course_code)
        .map(course => ({
          code: course.course_code,
          semester: course.semester
        }));
      console.log("User course codes extracted:", userCourses);
      setUserCourseCodes(userCourses);
    }
  }, [backendOutputData, isPublicMode]);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        
        // In public mode, force single semester view
        if (isPublicMode) {
          setActiveTab('thisSemester');
        }
        
        if (activeTab === 'thisSemester') {
          // Load single semester data
          const { courses, courseDetails, tsneCoords: filteredTsneCoords } = await loadPrecomputedCourseData(selectedSemester);
          setGraphData({ courses, similarityMatrix: null });
          setCourseDetailsData(courseDetails);
          setTsneCoords(filteredTsneCoords);
        } else {
          // Load history data (only if not in public mode)
          if (backendOutputData && !isPublicMode) {
            console.log("Processing backend data for history:", backendOutputData);
            
            // Get unique semesters from the history data
            const historySemesters = [...new Set(backendOutputData.map(course => course.semester))];
            console.log("Found history semesters:", historySemesters);
            
            // Group courses by semester for the history display
            const coursesBySemester = backendOutputData.reduce((acc, course) => {
              if (!course || !course.course_code) return acc;
              const semester = course.semester;
              if (!acc[semester]) {
                acc[semester] = [];
              }
              acc[semester].push({
                code: course.course_code,
                department: course.course_code.split('-')[0],
              });
              return acc;
            }, {});
            console.log("Grouped courses by semester:", coursesBySemester);

            // Identify semesters where the user took an FYSE course
            const userFyseSemesters = new Set(userCourseCodes
              .filter(course => course.code.startsWith('FYSE-'))
              .map(course => course.semester)
            );
            console.log("User FYSE semesters:", Array.from(userFyseSemesters));

            // Load all courses and coordinates for all semesters in history
            const allCourses = [];
            const allCourseDetailsMap = new Map();
            const allTsneCoords = [];

            for (const semester of historySemesters) {
              const { courses, courseDetails, tsneCoords } = await loadPrecomputedCourseData(semester);
              console.log(`Data for semester ${semester}:`, { courses, courseDetails, tsneCoords });

              // Filter FYSE courses if the user did not take an FYSE course in this semester
              const shouldIncludeFyse = userFyseSemesters.has(semester);

              // Add semester information to each course and apply FYSE filter
              const coursesWithSemester = courses
                .filter(course => shouldIncludeFyse || !course.code.startsWith('FYSE-'))
                .map(course => ({
                  ...course,
                  semester
                }));
              allCourses.push(...coursesWithSemester);

              // Accumulate unique course details using a Map for robustness
              courseDetails.forEach(cd => {
                if (cd.course_codes && Array.isArray(cd.course_codes)) {
                  cd.course_codes.forEach(code => {
                    // Apply FYSE filter to courseDetails as well
                    if (shouldIncludeFyse || !code.startsWith('FYSE-')) {
                      allCourseDetailsMap.set(code, cd);
                    }
                  });
                }
              });

              // Add semester information to each tsneCoord and apply FYSE filter
              const tsneCoordsWithSemester = tsneCoords
                .filter(coord => shouldIncludeFyse || !coord.codes.some(code => code.startsWith('FYSE-')))
                .map(coord => ({
                  ...coord,
                  semester
                }));
              allTsneCoords.push(...tsneCoordsWithSemester);
            }

            console.log("Final processed data:", {
              allCourses,
              courseDetails: Array.from(allCourseDetailsMap.values()),
              tsneCoords: allTsneCoords
            });

            setGraphData({ courses: allCourses, similarityMatrix: null });
            setCourseDetailsData(Array.from(allCourseDetailsMap.values()));
            setTsneCoords(allTsneCoords);

            // Store the semester information for display
            setHistoryData(coursesBySemester);
          }
        }

        setLoading(false);
      } catch (err) {
        console.error("Error loading data:", err);
        setError(err.message);
        setLoading(false);
      }
    }

    loadData();
  }, [selectedSemester, activeTab, backendOutputData, isPublicMode, userCourseCodes]);

  useEffect(() => {
    async function fetchUser() {
      // Skip authentication in public mode
      if (isPublicMode) {
        console.log("Public mode - skipping authentication");
        return;
      }
      
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
  }, [isPublicMode]);


  async function fetchBackendData() {

  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token;
  
  if (!token) {
    console.error("No valid session token found");
    return;
  }

    // Skip backend calls in public mode
    if (isPublicMode) {
      console.log("Public mode - skipping backend data fetch");
      setBackendOutputData([]);
      return;
    }
    
    try {
      console.log("Using backend URL:", backendUrl); // Add this for debugging!
      const response = await fetch(`${backendUrl}/retrieve_courses`, { // await fetch(`${API_BASE_URL}/retrieve_courses`
        method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify({}) // no user_id
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
    if (isPublicMode) {
      // In public mode, set empty backend data immediately
      setBackendOutputData([]);
      return;
    }
    
    if (!userId) return;
    fetchBackendData();
  }, [userId, isPublicMode]);

  // Add a function to check if there's any history data
  const hasHistoryData = () => {
    console.log("Checking history data:", backendOutputData); // <-- log the data check
    return backendOutputData && backendOutputData.length > 0;
  };

  // Add a function to get semesters with data
  const getSemestersWithData = () => {
    console.log("Getting semesters with data:", historyData); // <-- log the history data
    if (!historyData) return [];
    return Object.keys(historyData).sort();
  };

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
        precomputedTSNECoords.forEach(({ codes: tsneCoordCodes, x, y }) => {
          const currentTsneCodes = Array.isArray(tsneCoordCodes) ? tsneCoordCodes : [tsneCoordCodes]; // Ensure 'codes' is always an array
          currentTsneCodes.forEach(code => {
            const idx = codeToIndex.get(code);
            if (idx !== undefined) {
              coordinates[idx] = [x, y];
            }
          });
        });
      }

      const allMajors = Object.values(TRANCHES).flat();
      const colorPalette = d3.schemePastel1.slice(0, 8).concat(d3.schemePastel2);
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

      // Merge nodes with the same coordinates
      const mergedNodes = new Map();
      precomputedTSNECoords.forEach(({ codes: tsneCoordCodes, x, y, semester: coordSemester }) => {
        const currentTsneCodes = Array.isArray(tsneCoordCodes) ? tsneCoordCodes : [tsneCoordCodes]; // Ensure 'codes' is always an array
        // Filter out conflicted codes only if in 'thisSemester' tab AND showConflicts is true
        const filteredCodes = currentTsneCodes.filter(code => 
            code && (activeTab === 'yourHistory' || !showConflicts || !conflicted.includes(code))
        );
        
        if (filteredCodes.length === 0) return;

        const key = `${x},${y}`;
        if (!mergedNodes.has(key)) {
            // For new merged node, collect all course details at this coordinate
            const coursesAtPoint = [];
            filteredCodes.forEach(code => {
                const courseDetail = courseDetails.find(cd => cd.course_codes.includes(code));
                if (courseDetail) {
                    coursesAtPoint.push({ code, semester: coordSemester }); // Add code and its specific semester
                }
            });

            const firstCode = filteredCodes[0] || "TBD";
            const dept = firstCode.split('-')[0];
            
            mergedNodes.set(key, {
                id: firstCode,
                x,
                y,
                department: dept,
                codes: filteredCodes, // Still keep for general checks
                coursesAtPoint: coursesAtPoint, // New: list of {code, semester} for this point
                shape: getShapeForDept(dept),
                color: majorColorMap.get(dept) || "#999",
                // Separate highlighting for history vs search
                highlighted: filteredCodes.some(code => highlighted.includes(code)),
                historyHighlighted: coursesAtPoint.some(ca => 
                    userCourseCodes.some(uc => uc.code === ca.code && uc.semester === ca.semester)
                ),
                conflicted: false, // We already filtered conflicted codes
                semester: coordSemester, // This node represents a coordinate within this semester
            });
        } else {
            const node = mergedNodes.get(key);
            node.codes = [...new Set([...node.codes, ...filteredCodes])];
            const departments = node.codes.map(code => code.split('-')[0]);
            node.department = departments[0];
            node.shape = getShapeForDept(node.department);
            node.color = majorColorMap.get(node.department) || "#999";

            // Add new courses (with semester) to coursesAtPoint for existing node
            filteredCodes.forEach(code => {
                const courseDetail = courseDetails.find(cd => cd.course_codes.includes(code));
                if (courseDetail) {
                    const existingCourse = node.coursesAtPoint.find(ca => ca.code === code && ca.semester === coordSemester);
                    if (!existingCourse) {
                        node.coursesAtPoint.push({ code, semester: coordSemester });
                    }
                }
            });

            // Re-evaluate highlighting for existing node
            node.highlighted = filteredCodes.some(code => highlighted.includes(code));
            node.historyHighlighted = node.coursesAtPoint.some(ca => 
                userCourseCodes.some(uc => uc.code === ca.code && uc.semester === ca.semester)
            );
            node.conflicted = false; // We already filtered conflicted codes
        }
      });

      const finalNodes = Array.from(mergedNodes.values());

      // --- Z-ORDER: Render highlighted nodes last (on top) ---
      let nodesToRender = finalNodes;
      if (activeTab === 'yourHistory') {
        const highlightedNodes = finalNodes.filter(d => d.historyHighlighted);
        const otherNodes = finalNodes.filter(d => !d.historyHighlighted);
        nodesToRender = [...otherNodes, ...highlightedNodes];
      } else {
        const highlightedNodes = finalNodes.filter(d => d.highlighted);
        const otherNodes = finalNodes.filter(d => !d.highlighted);
        nodesToRender = [...otherNodes, ...highlightedNodes];
      }

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

      const getFontSize = (baseSize) => {
        // Scale font size based on width, with a minimum and maximum for readability
        const minWidth = 800; // Minimum width where baseSize is applied
        const maxWidth = 1920; // Maximum width where scaling stops
        const minFactor = 0.5; // Minimum scaling factor (was 0.8)
        const maxFactor = 1.0; // Maximum scaling factor (was 1.2)

        if (width <= minWidth) return `${baseSize * minFactor}px`;
        if (width >= maxWidth) return `${baseSize * maxFactor}px`;

        // Linear interpolation between min and max factor
        const factor = minFactor + (maxFactor - minFactor) * ((width - minWidth) / (maxWidth - minWidth));
        return `${baseSize * factor}px`;
      };

        const g = svg.append("g");

        g.append("rect")
          .attr("width", width)
          .attr("height", height)
          .attr("fill", "none");

      /*"""Add a reset zoom button
      const resetButton = svg.append("g")
        .attr("class", "reset-zoom")
        .attr("transform", `translate(${width}, 60)`)
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
        .style("font-size", getFontSize(12))
        .text("Reset View");

      resetButton.on("click", () => {
        svg.transition()
          .duration(750)
          .call(zoom.transform, d3.zoomIdentity);
      }); */


      
      // Calculate the legend space requirements
      const deptEntries = [...majorColorMap.entries()];
      const legendItemHeight = 25;
      
      // Conditional legend column and item width for Department Legend
      let legendItemWidth;
      let colCount;
      if (width > 1600) {
        legendItemWidth = 90; // Reduced width for fewer columns
        colCount = 2;
      } else {
        legendItemWidth = 100; // Original width for more columns
        colCount = 3;
      }
      
      // Left legend dimensions
      const leftLegendWidth = legendItemWidth * colCount + 0.02 * width;
      const leftLegendHeight = Math.ceil(deptEntries.length / colCount) * legendItemHeight + width * width * 0.00001;
      console.log('width', width * width * 0.00001)
      
      // Right legend dimensions (there is nothing now so set to 0)
      const rightLegendWidth = 0//leftLegendWidth; // Reduced width
      
      // Create padding for chart area
      const topPadding = 270 - width * 0.15; // Title space
      console.log('topPadding:', topPadding)
      const bottomPadding = 200 - width * 0.07; // Footer space
      const leftPadding = leftLegendWidth;
      const rightPadding = rightLegendWidth;
      
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


      // Use nodesToRender instead of finalNodes
      const nodeGroup = g
        .append("g")
        .selectAll("g")
        .data(nodesToRender)
        .enter()
        .append("g")
        .attr("transform", (d) => `translate(${xScale(d.x)},${yScale(d.y)})`);

      nodeGroup.each(function (d) {
        const group = d3.select(this);
        // Check if this node contains any of the user's courses in the correct semester
        // Now using d.coursesAtPoint for accurate check
        
        // Calculate highlighted codes count first (needed for both tabs)
        const highlightedCodes = d.codes.filter(code => 
          highlighted.some(highlightedCode => {
            // If the highlighted code contains a slash, split it and check each part
            if (highlightedCode.includes('/')) {
              return highlightedCode.split('/').includes(code);
            }
            return highlightedCode === code;
          })
        );
        const highlightedCount = highlightedCodes.length;
        
        // Adjust size and opacity based on whether it's a user's course and which tab we're in
        let baseSize, opacity;
        if (activeTab === 'yourHistory') {
          if (d.highlighted) { // If course is highlighted by search, give it the largest size
              baseSize = 15;
          } else if (d.historyHighlighted) { // If it's a historical user course (and not also highlighted by search), give it a medium size
              baseSize = 14;
          } else { // Default size for other courses
              baseSize = 7;
          }
          // Opacity: full for search-highlighted or historical courses, half for others
          opacity = (d.highlighted || d.historyHighlighted) ? 1 : 0.5;
        } else {
          // Single Semester View: Adjust base sizes for single vs multi-code courses
          if (d.codes.length === 1) {
            // Single code courses: slightly larger base size
            baseSize = highlightedCount > 0 ? 18 : 7;
          } else {
            // Multi-code courses: slightly smaller base size
            baseSize = highlightedCount > 0 ? 18 : 7;
          }
          opacity = 1;
        }

        // Get all departments for this course
        const departments = d.codes.map(code => code.split('-')[0]);
        const uniqueDepts = [...new Set(departments)];
        
        // Define scaling factor for non-circle shapes in single-code nodes
        const singleShapeScale = 0.7;

        // Handle single vs. multi-code nodes
        if (d.codes.length === 1) {
          // Single code: Draw a single, unclipped shape
          const dept = departments[0];
          let shape = getShapeForDept(dept);
          let color = majorColorMap.get(dept) || "#999";
          
          // Make colors more vibrant for user's courses in history tab or highlighted courses in single semester view
          if (activeTab === 'yourHistory') {
            if (d.historyHighlighted) {
              // Convert the color to a more vibrant version
              const vibrantColor = d3.color(color);
              if (vibrantColor) {
                vibrantColor.opacity = 1;
                // Increase saturation and brightness
                const hsl = d3.hsl(vibrantColor);
                hsl.s = Math.min(1, hsl.s * 1.5); // Increase saturation
                hsl.l = Math.min(0.7, hsl.l * 1.2); // Increase brightness but keep it dark enough
                color = hsl.toString();
              }
            }
          } else {
            // Single semester view highlighting
            if (highlightedCount > 0) {
              const vibrantColor = d3.color(color);
              if (vibrantColor) {
                vibrantColor.opacity = 1;
                const hsl = d3.hsl(vibrantColor);
                hsl.s = Math.min(1, hsl.s * 1.5); // Increase saturation
                hsl.l = Math.min(0.7, hsl.l * 1.2); // Increase brightness but keep it dark enough
                color = hsl.toString();
              }
            }
          }

          let size = baseSize;
          switch (shape) {
            case "circle":
              group.append("circle")
                .attr("r", size)
                .attr("fill", color)
                .attr("fill-opacity", opacity);
              break;
            case "doubleCircle":
              // Draw outer circle (unfilled)
              group.append("circle")
                .attr("r", size * 1.2)
                .attr("fill", "none")
                .attr("stroke", color)
                .attr("stroke-opacity", opacity)
                .attr("stroke-width", 1.5);
              // Draw inner circle (filled)
              group.append("circle")
                .attr("r", size * 0.8)
                .attr("fill", color)
                .attr("fill-opacity", opacity);
              break;
            case "square":
              size = baseSize * singleShapeScale;
              group.append("rect")
                .attr("x", -size)
                .attr("y", -size)
                .attr("width", size * 2.5)
                .attr("height", size * 2.5)
                .attr("fill", color)
                .attr("fill-opacity", opacity);
              break;
            case "triangle":
              size = baseSize * singleShapeScale;
              const triangleSymbolSize = size * size * 3;
              group.append("path")
                .attr("d", d3.symbol().type(d3.symbolTriangle).size(triangleSymbolSize)())
                .attr("fill", color)
                .attr("fill-opacity", opacity);
              break;
            case "star":
              size = baseSize * singleShapeScale;
              const starSymbolSize = size * size * 3;
              group.append("path")
                .attr("d", d3.symbol().type(d3.symbolStar).size(starSymbolSize)())
                .attr("fill", color)
                .attr("fill-opacity", opacity);
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
            let color = majorColorMap.get(dept) || "#999";
            
            // Make colors more vibrant based on tab and highlighting state
            if (activeTab === 'yourHistory') {
              if (d.historyHighlighted) {
                const vibrantColor = d3.color(color);
                if (vibrantColor) {
                  vibrantColor.opacity = 1;
                  const hsl = d3.hsl(vibrantColor);
                  hsl.s = Math.min(1, hsl.s * 1.5);
                  hsl.l = Math.min(0.7, hsl.l * 1.2);
                  color = hsl.toString();
                }
              }
            } else {
              // Single semester view highlighting
              if (highlightedCount > 0) {
                const vibrantColor = d3.color(color);
                if (vibrantColor) {
                  vibrantColor.opacity = 1;
                  const hsl = d3.hsl(vibrantColor);
                  // Increase vibrancy based on number of highlighted codes
                  hsl.s = Math.min(1, hsl.s * (1.5 + (highlightedCount * 0.2))); // More saturation for more highlighted codes
                  hsl.l = Math.min(0.7, hsl.l * (1.2 + (highlightedCount * 0.1))); // More brightness for more highlighted codes
                  color = hsl.toString();
                }
              }
            }
            
            // Create a clip path for this portion (pie slice)
            const clipPathId = `clip-${d.id}-${dept}-${startAngle}`;
            const clipPath = svg.append("defs").append("clipPath")
              .attr("id", clipPathId);
            
            const arc = d3.arc()
              .innerRadius(0)
              .outerRadius(baseSize)
              .startAngle(startAngle * Math.PI / 180)
              .endAngle(endAngle * Math.PI / 180);
            
            clipPath.append("path")
              .attr("d", arc());

            // Create a group for this segment and apply the clip path
            const shapeSegmentGroup = shapeContainer.append("g")
               .attr("clip-path", `url(#${clipPathId})`);

            // Draw the full shape within the clipped area with adjusted size for non-circles
            let currentShapeSize = baseSize; // Start with base size
             switch (shape) {
                case "circle":
                  // Circle size remains the same as single-code
                  shapeSegmentGroup.append("circle")
                    .attr("r", currentShapeSize)
                    .attr("fill", color)
                    .attr("fill-opacity", opacity);
                  break;
                case "doubleCircle":
                  // Draw outer circle (unfilled)
                  shapeSegmentGroup.append("circle")
                    .attr("r", currentShapeSize * 1.2)
                    .attr("fill", "none")
                    .attr("stroke", color)
                    .attr("stroke-opacity", opacity)
                    .attr("stroke-width", 1.5);
                  // Draw inner circle (filled)
                  shapeSegmentGroup.append("circle")
                    .attr("r", currentShapeSize * 0.8)
                    .attr("fill", color)
                    .attr("fill-opacity", opacity);
                  break;
                case "square":
                  // Scale down square size for multi-code
                  currentShapeSize = baseSize * multiShapeScale; // Apply multi-shape scale
                  shapeSegmentGroup.append("rect")
                    .attr("x", -currentShapeSize)
                    .attr("y", -currentShapeSize)
                    .attr("width", currentShapeSize * 2)
                    .attr("height", currentShapeSize * 2)
                    .attr("fill", color)
                    .attr("fill-opacity", opacity);
                  break;
                case "triangle":
                  // Scale down triangle size for multi-code, maintaining visual proportion
                  currentShapeSize = baseSize * multiShapeScale; // Apply multi-shape scale
                  const multiTriangleSymbolSize = currentShapeSize * currentShapeSize * 3; // Use same area multiplier as single-code
                   shapeSegmentGroup.append("path")
                    .attr("d", d3.symbol().type(d3.symbolTriangle).size(multiTriangleSymbolSize)())
                    .attr("fill", color)
                    .attr("fill-opacity", opacity);
                  break;
                case "star":
                  // Scale down star size for multi-code, maintaining visual proportion
                  currentShapeSize = baseSize * multiShapeScale; // Apply multi-shape scale
                  const multiStarSymbolSize = currentShapeSize * currentShapeSize * 2.7; // Use same area multiplier as single-code
                   shapeSegmentGroup.append("path")
                    .attr("d", d3.symbol().type(d3.symbolStar).size(multiStarSymbolSize)())
                    .attr("fill", color)
                    .attr("fill-opacity", opacity);
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

      // Only add labels for user's courses in the history tab
      if (activeTab === 'yourHistory') {
        nodeGroup
          .filter(d => d.historyHighlighted)
          .append("text")
          .attr("text-anchor", "middle")
          .attr("dy", -12)
          .attr("font-size", getFontSize(8))
          .attr("fill", "#000")
          .attr("class", "node-label")
          // For labels, if multiple user courses at the same point, show the first one or indicate multiple
          .text(d => {
            const userCoursesAtThisPoint = d.coursesAtPoint.filter(ca => 
              userCourseCodes.some(uc => uc.code === ca.code && uc.semester === ca.semester)
            );
            if (userCoursesAtThisPoint.length === 1) {
              return userCoursesAtThisPoint[0].code;
            } else if (userCoursesAtThisPoint.length > 1) {
              // If multiple user courses at this point, show the first code and an ellipsis
              return `${userCoursesAtThisPoint[0].code}...`;
            } else {
              return ''; // Should not happen with the filter above
            }
          });
      } else {
        // Add labels for all courses in the single semester tab
        nodeGroup
          .append("text")
          .attr("text-anchor", "middle")
          .attr("dy", d => d.highlighted ? -12 : -8)
          .attr("font-size", d => d.highlighted ? getFontSize(8) : getFontSize(7))
          .attr("fill", d => d.highlighted ? "#000" : "#333")
          .attr("class", "node-label")
          .text(d => d.codes.length > 1 ? `${d.codes[0]}...` : d.codes[0]);
      }

      if (!legendCollapsed) {
      // === DEPARTMENT LEGEND (2-COLUMN LAYOUT) ===
      const legendPaddingY = 290 - width * 0.15;
      const legendPaddingX = width * 0.01;
      console.log('legendPadding:', legendPaddingX)

      const legendItemCount = deptEntries.length;
      const legendRows = Math.ceil(legendItemCount / colCount);
      
      // Create background for legend
      svg.append("rect")
        .attr("x", legendPaddingX)
        .attr("y", legendPaddingY - 10)
        .attr("width", leftLegendWidth - 20)
        .attr("height", leftLegendHeight)
        .attr("fill", "rgba(249, 247, 251, 0.95)")
        .attr("rx", 5);
      
      // Add title to legend
      svg.append("text")
        .attr("x", legendPaddingX)
        .attr("y", legendPaddingY)
        .attr("text-anchor", "start")
        .style("font-weight", "bold")
        .style("font-size", getFontSize(14))
        .text("Departments");
        
      const legend = svg
        .append("g")
        .attr("transform", `translate(${legendPaddingX}, ${legendPaddingY + width * 0.01})`)
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
          .text(dept === "SWAG" ? "SWAG/WAGS" : dept)
          .style("font-size", getFontSize(12));
      });

      // === TRANCHE SHAPE LEGEND ===
      const shapeEntries = Object.entries(TRANCHE_SHAPES).filter(([tranche]) => tranche !== "First Year Seminar");
      const shapeLegendX = legendPaddingX;
      const shapeLegendY = legendPaddingY + leftLegendHeight;
      let shapeLegendHeight;
      if (width > 1600) {
        shapeLegendHeight = shapeEntries.length * legendItemHeight + width * 0.02; // Adjusted height for disclaimer text
      } else {
        shapeLegendHeight = shapeEntries.length * legendItemHeight;
      }
      
      // Define column count for shape legend (e.g., 2 columns)
      let shapeColCount;
      if (width > 1600) {
        shapeColCount = 1; // Single column for large screens
      } else {
        shapeColCount = 2; // Two columns for smaller screens
      }
      const shapeLegendRows = Math.ceil(shapeEntries.length / shapeColCount);

      // Background for shape legend
      svg.append("rect")
        .attr("x", shapeLegendX - 10)
        .attr("y", shapeLegendY - 10)
        .attr("width", leftLegendWidth - 20)
        .attr("height", shapeLegendHeight)
        .attr("fill", "rgba(249, 247, 251, 0.95)")
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
        .style("font-size", getFontSize(14));

      const shapeLegendItemVerticalOffset = 25;

      shapeEntries.forEach(([tranche, shapeType], i) => {
        const col = Math.floor(i / shapeLegendRows);
        const row = i % shapeLegendRows;

        const legendItem = shapeLegend
          .append("g")
          .attr("transform", `translate(${col * legendItemWidth}, ${row * legendItemHeight + shapeLegendItemVerticalOffset})`);

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
          .style("font-size", getFontSize(14));
      });

      // Add small text below the Department Groups legend
      const disclaimerText = shapeLegend
        .append("text")
        .attr("x", -3)
        .attr("y", shapeLegendHeight) // Adjusted Y position to be inside the background
        .style("font-size", getFontSize(14))
        .style("fill", "#666");

      disclaimerText.append("tspan")
        .text("Special topics and thesis");

      disclaimerText.append("tspan")
        .attr("x", -3) // Align with the x of the parent text element
        .attr("dy", "1.2em") // Move to the next line below the previous tspan
        .text("courses are not displayed.");

      // Optional: Add a visual separator between legends and graph
      svg.append("rect")
        .attr("x", leftPadding - 10)
        .attr("y", 0)
        .attr("width", 1)
        .attr("height", height)
        .attr("fill", "#e8e2f2");
    }

      // Main title with adjusted positioning
      svg
        .append("text")
        .attr("x", leftPadding + (width - leftPadding - rightPadding) / 2)
        .attr("y", 290 - width * 0.15)
        .attr("text-anchor", "middle")
        .style("font-size", getFontSize(18))
        .style("font-weight", "bold")
        .text(
          activeTab === 'thisSemester' 
            ? `Course Similarity Graph - ${selectedSemester}`
            : 'My Amherst Curriculum'
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
    highlighted,
    conflicted,
    graphData,
    courseDetailsData,
    tsneCoords,
    selectedSemester,
    activeTab,
    showConflicts,
    legendCollapsed,
  ]);

  const zoomRef = useRef(null);

useEffect(() => {
  const zoomBehavior = d3.zoom()
    .scaleExtent([0.5, 5])
    .on("zoom", (event) => {
      d3.select(svgRef.current).select("g").attr("transform", event.transform);
    });

  d3.select(svgRef.current).call(zoomBehavior);

  zoomRef.current = zoomBehavior;
}, []);

  // Function to handle image download
  const handleDownloadImage = async () => {
    const mapContainer = contentToCaptureRef.current; // Use the new ref to get the actual DOM element for capture
    if (mapContainer) {
      try {
        // Temporarily adjust scroll to top if needed, though html2canvas handles scrolling usually
        const originalScrollY = window.scrollY;
        window.scrollTo(0, 0);

        const canvas = await html2canvas(mapContainer, {
          useCORS: true, // If images/elements are loaded from different origins
          scale: 8, // Increase scale for higher resolution
          scrollY: -window.scrollY, // Correct scrolling issue
          width: mapContainer.offsetWidth, // Capture the element's actual width
          height: mapContainer.offsetHeight, // Capture the element's actual height
        });

        const image = canvas.toDataURL('image/jpeg', 1); // Convert to JPEG with quality 1
        const link = document.createElement('a');
        link.href = image;
        link.download = `my_open_curriculum.jpeg`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Restore original scroll position
        window.scrollTo(0, originalScrollY);

      } catch (err) {
        console.error('Error downloading map as image:', err);
        alert('Failed to download image.');
      }
    } else {
      alert('Map container not found.');
    }
  };

  // Add a function to get the title based on the active tab
  const getTitle = () => {
    if (activeTab === 'thisSemester') {
      return `Course Similarity Graph - ${selectedSemester}`;
    } else {
      return 'Your Course History';
    }
  };

  // Function to handle onboarding popup close
  const handleOnboardingClose = () => {
    setShowOnboarding(false);
    localStorage.setItem('hasSeenOnboarding', 'true');
  };

  // Function to handle adding a course to selected courses
  const handleAddSelectedCourse = async (course) => {
    if (!course.course_codes) return;
    
    const codes = Array.isArray(course.course_codes) 
      ? course.course_codes 
      : [course.course_codes];
    
    // If there are multiple codes, combine them with a slash
    const codeToAdd = codes.length > 1 ? codes.join('/') : codes[0];
    
    // Check if the course is already selected
    const isSelected = highlighted.some(code => {
      if (code.includes('/')) {
        return code === codeToAdd;
      }
      return codes.includes(code);
    });

    // Update highlighted courses and get the new state
    const newHighlighted = isSelected
      ? highlighted.filter(code => {
          if (code.includes('/')) {
            return code !== codeToAdd;
          }
          return !codes.includes(code);
        })
      : [...highlighted, codeToAdd];

    // Update highlighted courses
    onHighlight(newHighlighted);
    
    // Skip conflict checking in public mode
    if (isPublicMode) {
      return;
    }
    
    // Check for conflicts with the new selection
    const response = await fetch(`${backendUrl}/conflicted_courses`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ 
        taken_courses: newHighlighted, // Use the new state directly
        semester: selectedSemester 
      }),
    });

    const data = await response.json();
    onConflicted(data.conflicted_courses);
  };

  return (
    <div
      ref={mapContainerRef}
      className="relative w-full max-w-[1200px] mx-auto h-[80vh] bg-[#f9f7fb] shadow-md rounded-xl overflow-hidden border border-[#e8e2f2]"
    >
      {/* Tab Navigation */}
      <div className="absolute top-0 left-0 w-full bg-white/90 border-b border-[#e8e2f2] z-10">
        <div className="flex justify-between items-center">
          <div className="flex">
            <button
              className={`px-4 py-2 text-sm font-medium ${
                activeTab === 'thisSemester'
                  ? 'text-[#3f1f69] border-b-2 border-[#3f1f69]'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setActiveTab('thisSemester')}
            >
              Single Semester View
            </button>
            {!isPublicMode && (
              <button
                className={`px-4 py-2 text-sm font-medium ${
                  activeTab === 'yourHistory'
                    ? 'text-[#3f1f69] border-b-2 border-[#3f1f69]'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
                onClick={() => setActiveTab('yourHistory')}
              >
                My Course History
              </button>
            )}
          </div>
          

          
          {/* Download Map button moved to the right, alongside Eliminate Conflicts */}
          {activeTab === 'yourHistory' && !isPublicMode && (
            <button
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 ml-4 flex items-center"
              onClick={handleDownloadImage}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="w-4 h-4 mr-1"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
                />
              </svg>
              Download as Image
            </button>
          )}
          

          {activeTab === 'thisSemester' && (
            <div className="flex items-center px-4 py-2 ml-auto">
              <span className="text-sm font-medium text-gray-700 mr-2">Eliminate Conflicts:</span>
              <button
                className={`relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#3f1f69] ${showConflicts ? 'bg-[#3f1f69]' : 'bg-gray-300'}`}
                onClick={() => setShowConflicts(!showConflicts)}
              >
                <span className="sr-only">Eliminate Conflicts</span>
                <span
                  className={`pointer-events-none relative inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200 ${showConflicts ? 'translate-x-5' : 'translate-x-0'}`}
                ></span>
              </button>
            </div>
          )}
        </div>
      </div>

      {activeTab === 'yourHistory' && !hasHistoryData() && !isPublicMode ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center" style={{ top: '40px' }}>
          <div className="text-lg font-medium text-gray-600 mb-4">No History to Show</div>
          <button
            onClick={() => window.location.href = '/intake'}
            className="px-4 py-2 bg-[#3f1f69] text-white rounded-lg hover:bg-[#5c3d8a] transition-colors"
          >
            Add Courses
          </button>
        </div>
      ) : (
        <div className="relative w-full h-full">
          <div ref={contentToCaptureRef} className="relative w-full h-full bg-[#f9f7fb]" style={{ top: '0px' }}>
            <svg
              ref={setSvgRef}
              className="w-full h-full absolute top-0 left-0"
              style={{ top: '0px' }}
            ></svg>

            {/* Stack both buttons */}
          <div
            style={{
              position: "absolute",
              top: "10%",
              right: "2%",
              zIndex: 10,
              display: "flex",
              flexDirection: "column",
              gap: "10px"
            }}
          >
            <button
              style={{
                width: 80,
                height: 30,
                borderRadius: 5,
                backgroundColor: "rgba(249, 247, 251, 0.95)",
                border: "1px solid #e8e2f2",
                cursor: "pointer",
                fontSize: "12px",
                color: "#000",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              onClick={() => {
                if (svgRef.current) {
                  d3.select(svgRef.current)
                    .transition()
                    .duration(750)
                    .call(zoomRef.current.transform, d3.zoomIdentity);
                }
              }}
            >
              Reset View
            </button>

            <button
              style={{
                width: 80,
                height: 30,
                borderRadius: 5,
                backgroundColor: "rgba(249, 247, 251, 0.95)",
                border: "1px solid #e8e2f2",
                cursor: "pointer",
                fontSize: "12px",
                color: "#000",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              onClick={() => setLegendCollapsed(prev => !prev)}
            >
              {legendCollapsed ? "Show Legend" : "Hide Legend"}
            </button>
          </div>

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
              onHighlight={onHighlight}
              highlighted={highlighted}
              activeTab={activeTab}
              onSelect={handleAddSelectedCourse}
              courseDetailsData={courseDetailsData}
              setSelectedCourse={setSelectedCourse}
            />

            {/* Semester Display - Only show in My Course History tab */}
            {/* {activeTab === 'yourHistory' && historyData && (
              <div className="absolute bottom-0 left-0 w-full bg-white/90 p-4 border-t border-[#e8e2f2]">
                <div className="flex flex-wrap gap-4">
                  {getSemestersWithData().map(semester => (
                    <div key={semester} className="flex-1 min-w-[200px]">
                      <h3 className="text-sm font-medium text-gray-700 mb-2">{semester}</h3>
                      <div className="flex flex-wrap gap-2">
                        {historyData[semester].map(course => (
                          <span
                            key={course.code}
                            className="px-2 py-1 bg-[#f9f7fb] text-sm text-gray-600 rounded"
                          >
                            {course.code}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )} */}

            {/* Semester Slider - Only show in Single Semester View tab */}
            {activeTab === 'thisSemester' && (
              <div className="absolute bottom-0 left-0 w-full bg-white/90 p-4 border-t border-[#e8e2f2]">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">Semester:</span>
                    <span className="text-sm text-gray-600">{selectedSemester}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700">Selected Courses:</span>
                    <div className="flex gap-1">
                      {highlighted.length > 0 ? (
                        highlighted.map((code) => (
                          <div
                            key={code}
                            className="group relative px-2 py-0.5 bg-[#f4f0fa] text-sm text-[#3f1f69] rounded border border-[#eae6f4] hover:bg-[#eae6f4] transition-colors"
                          >
                            {code}
                            <button
                              onClick={() => handleAddSelectedCourse({ course_codes: [code] })}
                              className="absolute -top-1 -right-1 w-4 h-4 bg-white rounded-full border border-[#eae6f4] 
                                flex items-center justify-center text-[#3f1f69] opacity-0 group-hover:opacity-100 
                                transition-opacity hover:bg-[#f4f0fa]"
                              aria-label={`Remove ${code}`}
                            >
                              <svg
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 20 20"
                                fill="currentColor"
                                className="w-3 h-3"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            </button>
                          </div>
                        ))
                      ) : (
                        <span className="text-sm text-gray-500 italic">None</span>
                      )}
                    </div>
                  </div>
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
            )}
          </div>
        </div>
      )}

      {showSettings && (
        <Settings onClose={() => setShowSettings(false)} />
      )}

      <OnboardingPopup 
        isOpen={showOnboarding}
        onClose={handleOnboardingClose}
        isPublicMode={isPublicMode}
      />
    </div>
  );
}