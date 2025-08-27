import React, { useState, useEffect } from "react";
import { API_BASE_URL } from './config';

export default function CourseInput({ onHighlight, onConflicted, currentSemester, highlighted }) {
  const [input, setInput] = useState("");
  const [allCourses, setAllCourses] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const backendUrl=process.env.REACT_APP_BACKEND_URL;
  const [useSemanticSearch, setUseSemanticSearch] = useState(false); // toggle state

  // Helper function to calculate semester distance
  const calculateSemesterDistance = (semester1, semester2) => {
    // Parse semester format: YYMMT (e.g., "2324S")
    const parseSemester = (sem) => {
      const year = parseInt(sem.substring(0, 2) + sem.substring(2, 4)); // Convert YYMM to full year
      const term = sem.charAt(4);
      const termOrder = { 'F': 0, 'J': 1, 'S': 2 }; // Fall, January, Spring
      return { year, termOrder: termOrder[term] || 0 };
    };

    const sem1 = parseSemester(semester1);
    const sem2 = parseSemester(semester2);

    // Calculate distance: (year difference * 3) + term difference
    const yearDiff = Math.abs(sem1.year - sem2.year);
    const termDiff = Math.abs(sem1.termOrder - sem2.termOrder);
    
    return (yearDiff * 3) + termDiff;
  };

  // Load course data on component mount
  useEffect(() => {
    const loadCourses = async () => {
      try {
        //console.log('Attempting to load courses...');
        const response = await fetch('/amherst_courses_all.json');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        //console.log('Loaded courses:', data.length);
        //console.log('First course:', data[0]);
        setAllCourses(data);
      } catch (error) {
        console.error('Error loading courses:', error);
        console.error('Error details:', {
          message: error.message,
          stack: error.stack
        });
      }
    };
    loadCourses();
  }, []);

  // Search function to find matching courses
  const searchCourses = (searchTerm) => {
    //console.log('Searching with term:', searchTerm);
    //console.log('Current semester:', currentSemester);
    //console.log('Number of courses available:', allCourses.length);
    
    if (!searchTerm.trim()) {
      setSuggestions([]);
      return;
    }

    const searchTermLower = searchTerm.toLowerCase();
    
    // First, find all matching courses across all semesters
    const allMatches = allCourses
      .filter(course => {
        if (!course.semester) return false;

        const courseCodes = Array.isArray(course.course_codes) 
          ? course.course_codes 
          : [course.course_codes];
        
        const codeMatch = courseCodes.some(code => 
          code.toLowerCase().includes(searchTermLower)
        );
        const titleMatch = course.course_title && 
          course.course_title.toLowerCase().includes(searchTermLower);
        
        return codeMatch || titleMatch;
      })
      .map(course => ({
        ...course,
        semesterDistance: calculateSemesterDistance(currentSemester, course.semester)
      }));

    // Sort by relevance first (exact matches, then partial matches), then by semester distance
    const sortedMatches = allMatches.sort((a, b) => {
      // First, prioritize exact matches in course codes
      const aCodes = Array.isArray(a.course_codes) ? a.course_codes : [a.course_codes];
      const bCodes = Array.isArray(b.course_codes) ? b.course_codes : [b.course_codes];
      
      const aExactMatch = aCodes.some(code => code.toLowerCase() === searchTermLower);
      const bExactMatch = bCodes.some(code => code.toLowerCase() === searchTermLower);
      
      if (aExactMatch && !bExactMatch) return -1;
      if (!aExactMatch && bExactMatch) return 1;
      
      // Then prioritize exact matches in titles
      const aTitleExact = a.course_title && a.course_title.toLowerCase() === searchTermLower;
      const bTitleExact = b.course_title && b.course_title.toLowerCase() === searchTermLower;
      
      if (aTitleExact && !bTitleExact) return -1;
      if (!aTitleExact && bTitleExact) return 1;
      
      // Then prioritize starts-with matches
      const aStartsWith = aCodes.some(code => code.toLowerCase().startsWith(searchTermLower)) ||
                         (a.course_title && a.course_title.toLowerCase().startsWith(searchTermLower));
      const bStartsWith = bCodes.some(code => code.toLowerCase().startsWith(searchTermLower)) ||
                         (b.course_title && b.course_title.toLowerCase().startsWith(searchTermLower));
      
      if (aStartsWith && !bStartsWith) return -1;
      if (!aStartsWith && bStartsWith) return 1;
      
      // Finally, sort by semester distance (closer semesters first)
      return a.semesterDistance - b.semesterDistance;
    });

    // Remove duplicates based on course code, keeping the first occurrence (which will be from the closest semester)
    const uniqueMatches = [];
    const seenCodes = new Set();
    
    for (const course of sortedMatches) {
      const courseCodes = Array.isArray(course.course_codes) ? course.course_codes : [course.course_codes];
      const primaryCode = courseCodes[0];
      
      if (!seenCodes.has(primaryCode)) {
        seenCodes.add(primaryCode);
        uniqueMatches.push(course);
      }
    }

    // Limit to 5 suggestions
    const matches = uniqueMatches.slice(0, 5);

    //console.log('Found matches:', matches);
    setSuggestions(matches);
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    setInput(value);
    if (useSemanticSearch) {
      searchSemanticCourse(value);
    } else {
      searchCourses(value);
    }
    setShowSuggestions(true);
  };

  const handleToggle = () => setUseSemanticSearch(!useSemanticSearch);

  const searchSemanticCourse = async (searchTerm) => {
    if (!searchTerm.trim()) {
      setSuggestions([]);
      return;
    }
    try {
      console.log("attempted semantic search");
      const response = await fetch(`${backendUrl}/semantic_course_search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchTerm, semester: currentSemester }),
      });
      const data = await response.json();
      setSuggestions(data.slice(0, 5)); // limit to top 5
    } catch (err) {
      console.error("Semantic search error:", err);
      setSuggestions([]);
    }
  };

  const handleSuggestionClick = async (course) => {
    const courseCodes = Array.isArray(course.course_codes) 
      ? course.course_codes 
      : [course.course_codes];
    
    setInput(courseCodes[0]); // Set the first course code as input
    setShowSuggestions(false);
    
    // Ensure highlighted is an array before spreading
    const currentHighlighted = Array.isArray(highlighted) ? highlighted : [];
    //('Current highlighted courses:', currentHighlighted);
    const newHighlighted = [...currentHighlighted, courseCodes[0]];
    //console.log('New highlighted courses after adding:', newHighlighted);
    onHighlight(newHighlighted);
    
    // Check for conflicts
    try {
      const response = await fetch(`${backendUrl}/conflicted_courses`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          taken_courses: newHighlighted,
          semester: currentSemester 
        }),
      });
      const data = await response.json();
      onConflicted(data.conflicted_courses);
    } catch (error) {
      console.error('Error checking conflicts:', error);
    }
    
    setInput(""); // Clear the input after search
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const codes = input
      .split(",")
      .map((code) => code.trim().toUpperCase())
      .filter((code) => code.length > 0);
    
  if (codes.length === 0) return; // nothing to process

    // Create a set of all valid course codes
  const allCourseCodes = new Set(
    allCourses.flatMap(course => 
      Array.isArray(course.course_codes) 
        ? course.course_codes 
        : [course.course_codes]
    )
  );

// Filter input codes to only keep valid ones
const validCodes = codes.filter(code => allCourseCodes.has(code));

if (validCodes.length === 0) return; // no valid codes, do nothing

    // Combine with current highlighted courses
  const currentHighlighted = Array.isArray(highlighted) ? highlighted : [];
  const newHighlighted = [...currentHighlighted, ...validCodes];
  onHighlight(newHighlighted);
    
    // Check for conflicts
    try {
      const response = await fetch(`${backendUrl}/conflicted_courses`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          taken_courses: newHighlighted,
          semester: currentSemester 
        }),
      });
      const data = await response.json();
      onConflicted(data.conflicted_courses);
    } catch (error) {
      console.error('Error checking conflicts:', error);
    }
    
    setInput(""); // Clear the input after search
  };

  // Update suggestions when semester changes
  useEffect(() => {
    if (input.trim()) {
      searchCourses(input);
    } else {
      // Clear suggestions when semester changes and there's no input
      setSuggestions([]);
    }
  }, [currentSemester, input]);

  return (
    <div className="relative w-full max-w-[1200px] mx-auto">
      
      

      <form
        onSubmit={handleSubmit}
        className="w-full flex flex-wrap items-center gap-4 bg-[#f9f7fb] border border-[#eae6f4] rounded-xl px-6 py-4 mb-6"
      >
        <div className="flex justify-end mb-4">
      <button
        onClick={() => setUseSemanticSearch(!useSemanticSearch)}
        className={`px-4 py-2 rounded-md font-semibold transition ${
          useSemanticSearch ? "bg-[#3f1f69] text-white" : "bg-gray-200 text-black"
        }`}
      >
        {useSemanticSearch ? "Semantic Search" : "Default Search"}
      </button>
    </div>

        <label
          htmlFor="course-input"
          className="font-semibold text-[#3f1f69] text-sm"
        >
          Search Courses:
        </label>

        <div className="flex-1 min-w-[200px] relative">
          <input
            id="course-input"
            type="text"
            value={input}
            onChange={handleInputChange}
            onFocus={() => {
              //console.log('Input focused');
              setShowSuggestions(true);
            }}
            placeholder={`Search by course code or title across all semesters (e.g. MATH-111 or Introduction to Legal Theory)`}
            className="w-full px-3 py-2 border border-[#5d3c85] bg-[#f4f0fa] text-sm rounded-md focus:outline-none focus:ring-2 focus:ring-[#3f1f69]"
          />
          
          {showSuggestions && suggestions.length > 0 && (
            <div className="absolute z-50 w-full mt-1 bg-white border border-[#eae6f4] rounded-md shadow-lg">
              {suggestions.map((course, index) => (
                <div
                  key={index}
                  onClick={() => handleSuggestionClick(course)}
                  className="px-3 py-2 hover:bg-[#f4f0fa] cursor-pointer text-sm"
                >
                  <div className="font-medium text-[#3f1f69]">
                    {Array.isArray(course.course_codes) 
                      ? course.course_codes.join(", ") 
                      : course.course_codes}
                  </div>
                  <div className="text-gray-600">
                    {course.course_title}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <button
          type="submit"
          className="px-4 py-2 text-sm font-semibold bg-[#3f1f69] text-white rounded-md hover:bg-[#311a4d] transition"
        >
          Search
        </button>
      </form>
    </div>
  );
}
