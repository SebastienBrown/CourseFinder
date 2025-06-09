import React, { useState, useEffect } from "react";
import { API_BASE_URL } from './config';

export default function CourseInput({ onHighlight, onConflicted, currentSemester }) {
  const [input, setInput] = useState("");
  const [allCourses, setAllCourses] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Load course data on component mount
  useEffect(() => {
    const loadCourses = async () => {
      try {
        console.log('Attempting to load courses...');
        const response = await fetch('/amherst_courses_all.json');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        console.log('Loaded courses:', data.length);
        console.log('First course:', data[0]);
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
    console.log('Searching with term:', searchTerm);
    console.log('Current semester:', currentSemester);
    console.log('Number of courses available:', allCourses.length);
    
    if (!searchTerm.trim()) {
      setSuggestions([]);
      return;
    }

    const searchTermLower = searchTerm.toLowerCase();
    const matches = allCourses
      .filter(course => {
        // Filter by current semester first
        if (!course.semester) return false;
        if (!course.semester.includes(currentSemester)) {
          return false;
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
      .slice(0, 5); // Limit to 5 suggestions

    console.log('Found matches:', matches);
    setSuggestions(matches);
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    setInput(value);
    searchCourses(value);
    setShowSuggestions(true);
    console.log('Input changed:', value);
    console.log('Suggestions:', suggestions);
    console.log('Show suggestions:', showSuggestions);
  };

  const handleSuggestionClick = (course) => {
    const courseCodes = Array.isArray(course.course_codes) 
      ? course.course_codes 
      : [course.course_codes];
    
    setInput(courseCodes[0]); // Set the first course code as input
    setShowSuggestions(false);
    
    // Trigger the search with the selected course code
    onHighlight([courseCodes[0]]);
    setInput(""); // Clear the input after search
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const codes = input
      .split(",")
      .map((code) => code.trim().toUpperCase())
      .filter((code) => code.length > 0);

    onHighlight(codes); // Only highlight the searched courses
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
              console.log('Input focused');
              setShowSuggestions(true);
            }}
            placeholder={`Search by course code or title for ${currentSemester} (e.g. MATH-111 or Introduction to Legal Theory)`}
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
