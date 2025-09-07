import React, { useState, useEffect } from "react";
import { API_BASE_URL } from './config';
import { useSemester } from './SemesterContext';
import { supabase } from "./supabaseClient"; 
import CoursePopup from "./CoursePopup"; // Add this import

export default function CourseInput({ onHighlight, onConflicted, currentSemester, highlighted}) {
  const [input, setInput] = useState("");
  const [allCourses, setAllCourses] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const backendUrl=process.env.REACT_APP_BACKEND_URL;
  const [useSemanticSearch, setUseSemanticSearch] = useState(false); // toggle state
  const [useAllSemestersSearch,setAllSemestersSearch] = useState(false);
  const { selectedSemester } = useSemester();
  const [selectedCourse, setSelectedCourse] = useState(null); // Add this state


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

// Search function to find matching courses with all semesters listed
const searchCourses = (searchTerm) => {
  //console.log('Searching with term:', searchTerm);
  //console.log('Current semester:', currentSemester);
  //console.log('Number of courses available:', allCourses.length);
  
  if (!searchTerm.trim()) {
    setSuggestions([]);
    return;
  }

  const searchTermLower = searchTerm.toLowerCase();

  let allMatches;

  // First, find all matching courses across all semesters
  allMatches = allCourses
    .filter(course => {
      if (!course.semester) return false;

      //console.log("current semester is ", selectedSemester)
      if (!useAllSemestersSearch) {
        // Only include courses that match the selected semester
        if (course.semester !== selectedSemester) return false;
      }

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

  // Group courses by their primary course code
  const courseGroups = new Map();
  
  for (const course of allMatches) {
    const courseCodes = Array.isArray(course.course_codes) ? course.course_codes : [course.course_codes];
    const primaryCode = courseCodes[0];
    
    if (!courseGroups.has(primaryCode)) {
      courseGroups.set(primaryCode, {
        course_codes: course.course_codes,
        course_title: course.course_title,
        semesters: [],
        courses: [] // Store all course instances
      });
    }
    
    const group = courseGroups.get(primaryCode);
    group.semesters.push(course.semester);
    group.courses.push(course);
  }

  // Convert grouped courses back to array format with semester lists
  const groupedCourses = Array.from(courseGroups.values()).map(group => {
    // Sort semesters chronologically (you may need to adjust this based on your semester format)
    const sortedSemesters = group.semesters.sort((a, b) => {
      // Assuming semester format like "Fall 2023", "Spring 2024", etc.
      // You may need to adjust this sorting logic based on your actual semester format
      return a.localeCompare(b);
    });

    // Find the course instance from the closest semester for other properties
    const closestCourse = group.courses.reduce((closest, current) => {
      return current.semesterDistance < closest.semesterDistance ? current : closest;
    });

    return {
      ...closestCourse,
      semesters: sortedSemesters,
      semesterCount: sortedSemesters.length,
      // Add a display property for all semesters
      allSemestersText: sortedSemesters.join(', ')
    };
  });

  // Sort by relevance first, then by semester distance of the closest occurrence
  const sortedMatches = groupedCourses.sort((a, b) => {
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

  // Limit to 5 suggestions
  const matches = sortedMatches.slice(0, 5);

  //console.log('Found matches with all semesters:', matches);
  setSuggestions(matches);
};

  const handleInputChange = (e) => {
    const value = e.target.value;
    setInput(value);
    
    if (!useSemanticSearch) {
      // Default behavior: live search as usual
      searchCourses(value);
      setShowSuggestions(true);
    } else {
      // In semantic mode: no live search
      setShowSuggestions(false);
    }
  };

  const handleToggle = () => {
    setUseSemanticSearch(prev => !prev);
  };  
  
  useEffect(() => {
    //console.log("useSemanticSearch is now:", useSemanticSearch);
  }, [selectedSemester,useSemanticSearch]);

  
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
        body: JSON.stringify({ query: searchTerm, allSemesterSearch: useAllSemestersSearch, currentSemester: selectedSemester }),
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

    // Show the course popup
    setSelectedCourse(course);
    
    /* 
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
    } */
    
    //maybe the most logical thing to do when selecting a course is to bring up it's popup 
    //but not select - looking up a course doesn't mean that someone wants to take it
    //on the flip side - neither should it be highlighted!!!


    /* const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;
      
      if (!token) {
        console.error("No valid session token found");
        return;
      }

      const payload = {
        course_to_add: courseCodes[0],
        semester: course.semester
      };

      console.log("Added a course");
      console.log(courseCodes[0]);
        
      try {
        const response = await fetch(`${backendUrl}/add_course`, { // await fetch(`${API_BASE_URL}/retrieve_courses`
          method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        //for cross-listed courses, this will take the first course code - be aware of this as it COULD cause issues later-on depending on treatment of cross-listed courses
        body: JSON.stringify(payload) // no user_id
        });
    
        if (!response.ok) {
          throw new Error(`Backend error: ${response.status}`);
        }
    
      } catch (err) {
        console.log(err.message);
        console.error("Error fetching backend data:", err);
      } */

    setInput(""); // Clear the input after search
  };

  // Function to handle course selection (adding/removing from highlighted list)
  const handleAddSelectedCourse = async (course) => {
    const courseCodes = Array.isArray(course.course_codes) 
      ? course.course_codes 
      : [course.course_codes];
    
    const primaryCode = courseCodes[0];
    
    // Check if already highlighted
    const currentHighlighted = Array.isArray(highlighted) ? highlighted : [];
    const isAlreadyHighlighted = currentHighlighted.includes(primaryCode) ||
      courseCodes.some(code => currentHighlighted.includes(code)) ||
      currentHighlighted.includes(courseCodes.join('/'));
    
    let newHighlighted;
    if (isAlreadyHighlighted) {
      // Remove from highlighted
      newHighlighted = currentHighlighted.filter(code => 
        !courseCodes.includes(code) && code !== courseCodes.join('/')
      );
    } else {
      // Add to highlighted
      newHighlighted = [...currentHighlighted, primaryCode];
    }
    
    // Update highlighted courses
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
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (useSemanticSearch) {
      // Trigger semantic search on submit
      await searchSemanticCourse(input);
      setShowSuggestions(true); // Show semantic search results
      return;
    }

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
      <button
      type="button"
        onClick={() => setUseSemanticSearch(!useSemanticSearch)}
        className={`px-4 py-2 rounded-md font-semibold transition ${
          useSemanticSearch ? "bg-[#3f1f69] text-white" : "bg-gray-200 text-black"
        }`}
      >
        {useSemanticSearch ? "Semantic Search" : "Default Search"}
      </button>

      <button
      type="button"
        onClick={() => setAllSemestersSearch(!useAllSemestersSearch)}
        className={`px-4 py-2 rounded-md font-semibold transition ${
          useAllSemestersSearch ? "bg-[#3f1f69] text-white" : "bg-gray-200 text-black"
        }`}
      >
        {useAllSemestersSearch ? "All Semesters" : "Current Semester"}
      </button>

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
            placeholder={
              useSemanticSearch
                ? "Search semantically across all upcoming courses (e.g., find a math course on basic calculus and limits)"
                : "Search by course code or title across all semesters (e.g., MATH-111 or Introduction to Legal Theory)"
            }
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
                {/* Show all semesters if multiple semesters exist */}
                {course.semesters && course.semesters.length > 1 && (
                  <div className="text-xs text-gray-500 mt-1">
                    Taught in: {course.allSemestersText}
                  </div>
                )}
                {/* Show single semester for courses taught in only one semester */}
                {course.semesters && course.semesters.length === 1 && (
                  <div className="text-xs text-gray-500 mt-1">
                    {course.semester}
                  </div>
                )}
                {/* Fallback for courses without the new semesters array (backward compatibility) */}
                {!course.semesters && course.semester && (
                  <div className="text-xs text-gray-500 mt-1">
                    {course.semester}
                  </div>
                )}
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

      {/* CoursePopup is now part of CourseInput */}
      {selectedCourse && (
        <CoursePopup
          course={selectedCourse}
          onClose={() => setSelectedCourse(null)}
          onHighlight={onHighlight}
          highlighted={highlighted}
          activeTab="thisSemester"
          onSelect={handleAddSelectedCourse}
          courseDetailsData={allCourses}
          setSelectedCourse={setSelectedCourse}
        />
      )}

    </div>
  );
}
