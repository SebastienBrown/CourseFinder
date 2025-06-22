import React, { useState, useEffect, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { supabase } from "./supabaseClient"; // make sure this points to your initialized Supabase client
import { API_BASE_URL } from './config';

export default function SemesterCourseIntake() {
  const navigate = useNavigate();
  const { index } = useParams(); // index of current semester in selectedSemesters
  const [selectedCourses, setSelectedCourses] = useState([]);
  const [allCourses, setAllCourses] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [userId, setUserId] = useState(null); // Store user ID

  // Load selected semesters from localStorage
  const selectedSemesters = JSON.parse(localStorage.getItem("selectedSemesters") || "[]");
  const semesterCourses = JSON.parse(localStorage.getItem("semesterCourses") || "{}");
  const semester = selectedSemesters[parseInt(index)];

  // Check if we came from transcript upload
  const fromTranscriptUpload = localStorage.getItem('fromTranscriptUpload') === 'true';
  const editingSemesterIndex = localStorage.getItem('editingSemesterIndex');

  const backendUrl=process.env.REACT_APP_BACKEND_URL;

  // Load courses JSON dynamically on mount or semester change
  useEffect(() => {
    if (!semester) {
      navigate("/graph");
      return;
    }

    async function fetchCourses() {
      try {
        const res = await fetch(`/amherst_courses_all.json`);
        const allData = await res.json();
        // Filter courses by the current semester
        const data = allData.filter(course => 
          course.semester && course.semester.includes(semester)
        );
        setAllCourses(data);
        setSelectedCourses(semesterCourses[semester] || []);
      } catch (error) {
        console.error("Failed to load courses JSON", error);
        setAllCourses([]);
      }
    }

    async function fetchUserId() {
      try {
        const { data: { user }, error } = await supabase.auth.getUser();

        if (error) {
          console.error("Error fetching user:", error);
          return;
        }

        if (user) {
          setUserId(user.id);
        } else {
          console.warn("No user logged in.");
        }
      } catch (err) {
        console.error("Unexpected error fetching user:", err);
      }
    }

    fetchCourses();
    fetchUserId(); // Fetch user ID when component mounts
  }, [semester, navigate]);

  const filteredCourses = allCourses.filter((course) => {
    const codesArray = Array.isArray(course.course_codes)
      ? course.course_codes
      : [course.course_codes];
  
    const codesMatch = codesArray.some((code) =>
      code.toLowerCase().includes(searchTerm.toLowerCase())
    );
  
    const titleMatch = course.course_title && 
      course.course_title.toLowerCase().includes(searchTerm.toLowerCase());
  
    return codesMatch || titleMatch;
  });

  // Separate selected and unselected courses
  const { selectedCoursesData, unselectedCourses } = useMemo(() => {
    const uniqueCoursesMap = new Map();

    // First, add all courses that match the search filter
    filteredCourses.forEach((course) => {
      const courseCodesArray = Array.isArray(course.course_codes)
        ? course.course_codes
        : [course.course_codes];
      const courseCode = courseCodesArray[0];

      // Only add first occurrence of this courseCode
      if (!uniqueCoursesMap.has(courseCode)) {
        uniqueCoursesMap.set(courseCode, course);
      }
    });

    // Then, ensure ALL selected courses are included, even if they don't match search
    allCourses.forEach((course) => {
      const courseCodesArray = Array.isArray(course.course_codes)
        ? course.course_codes
        : [course.course_codes];
      const courseCode = courseCodesArray[0];

      // If this course is selected but not already in the map, add it
      if (selectedCourses.includes(courseCode) && !uniqueCoursesMap.has(courseCode)) {
        uniqueCoursesMap.set(courseCode, course);
      }
    });

    const coursesArray = Array.from(uniqueCoursesMap.values());
    
    // Separate into selected and unselected
    const selected = [];
    const unselected = [];
    
    coursesArray.forEach(course => {
      const courseCode = Array.isArray(course.course_codes) ? course.course_codes[0] : course.course_codes;
      if (selectedCourses.includes(courseCode)) {
        selected.push(course);
      } else {
        unselected.push(course);
      }
    });
    
    // Sort both arrays alphabetically
    const sortFn = (a, b) => {
      const aCode = Array.isArray(a.course_codes) ? a.course_codes[0] : a.course_codes;
      const bCode = Array.isArray(b.course_codes) ? b.course_codes[0] : b.course_codes;
      return aCode.localeCompare(bCode);
    };
    
    return {
      selectedCoursesData: selected.sort(sortFn),
      unselectedCourses: unselected.sort(sortFn)
    };
  }, [allCourses, selectedCourses, filteredCourses]);

  const toggleCourse = (courseCode) => {
    setSelectedCourses((prev) =>
      prev.includes(courseCode) ? prev.filter((c) => c !== courseCode) : [...prev, courseCode]
    );
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && unselectedCourses.length > 0) {
      e.preventDefault(); // Prevent form submission if this input is in a form
      const topCourse = unselectedCourses[0];
      const courseCode = Array.isArray(topCourse.course_codes) 
        ? topCourse.course_codes[0] 
        : topCourse.course_codes;
      toggleCourse(courseCode);
    }
  };

  const handleReturnToTranscriptUpload = () => {
    // Update the semester courses with current selection
    const updatedSemesterCourses = { ...semesterCourses };
    updatedSemesterCourses[semester] = selectedCourses;
    localStorage.setItem("semesterCourses", JSON.stringify(updatedSemesterCourses));

    // Update the transcript data structure
    const editingTranscriptData = JSON.parse(localStorage.getItem('editingTranscriptData') || '{}');
    if (editingTranscriptData.semesters && editingTranscriptData.semesters[parseInt(editingSemesterIndex)]) {
      editingTranscriptData.semesters[parseInt(editingSemesterIndex)].courses = selectedCourses;
      localStorage.setItem('editingTranscriptData', JSON.stringify(editingTranscriptData));
    }

    // Set flag to indicate return from edit
    localStorage.setItem('returnFromTranscriptEdit', 'true');
    
    // Navigate back to transcript upload
    navigate('/upload');
  };

  const handleSubmit = async () => {
    // If we came from transcript upload, handle return differently
    if (fromTranscriptUpload) {
      handleReturnToTranscriptUpload();
      return;
    }

    // Original submit logic for normal flow
    semesterCourses[semester] = selectedCourses;
    localStorage.setItem("semesterCourses", JSON.stringify(semesterCourses));

    const isLastSemester = parseInt(index) + 1 >= selectedSemesters.length;

    if (isLastSemester) {
      // Build the dictionary payload
      const payload = {
        user_id: userId,
        semester_courses: {}
      };

      for (const [sem, courses] of Object.entries(semesterCourses)) {
        payload.semester_courses[sem] = courses;
      }

      try {
        const response = await fetch(`${backendUrl}/submit_courses`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }

        console.log("Successfully sent data to backend!");
      } catch (error) {
        console.error("Error sending data to backend:", error);
      }

      navigate("/graph");
    } else {
      navigate(`/intake/courses/${parseInt(index) + 1}`);
    }
  };

  const handleBack = () => {
    if (fromTranscriptUpload) {
      // If we came from transcript upload, go back to transcript upload
      handleReturnToTranscriptUpload();
    } else {
      // Original back logic
      if (parseInt(index) === 0) {
        navigate('/intake');
      } else {
        navigate(`/intake/courses/${parseInt(index) - 1}`);
      }
    }
  };

  if (!semester) return null;

  return (
    <div className="max-w-3xl mx-auto mt-12 p-6 bg-white shadow rounded space-y-6">
      <h2 className="text-2xl font-bold text-center text-[#3f1f69]">
        {fromTranscriptUpload ? `Edit Courses for ${semester}` : `Select Courses for Semester ${semester}`}
      </h2>

      {fromTranscriptUpload && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
          <p className="text-blue-800 text-sm">
            You are editing courses from your transcript. Click "Save Changes" when done to return to the validation page.
          </p>
        </div>
      )}

      <input
        type="text"
        placeholder="Search courses..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        onKeyDown={handleKeyDown}
        className="w-full border rounded px-3 py-2"
      />

      {/* Fixed Selected Courses Section */}
      {selectedCoursesData.length > 0 && (
        <div className="bg-[#f9f7fb] border border-[#3f1f69] rounded-lg p-4 mb-4">
          <div className="text-sm text-[#3f1f69] font-bold mb-3">
            Selected Courses ({selectedCoursesData.length})
          </div>
          <div className="space-y-2">
            {selectedCoursesData.map((course) => {
              const courseCodesArray = Array.isArray(course.course_codes)
                ? course.course_codes
                : [course.course_codes];
              const courseCode = courseCodesArray[0];
              const courseCodesDisplay = courseCodesArray.join(", ");

              return (
                <div 
                  key={`selected-${courseCode}`}
                  className="flex items-center p-2 bg-white rounded border border-[#3f1f69]"
                >
                  <input
                    type="checkbox"
                    id={`selected-${courseCode}`}
                    checked={true}
                    onChange={(e) => {
                      e.preventDefault();
                      toggleCourse(courseCode);
                    }}
                    className="mr-3 h-4 w-4 text-[#3f1f69] focus:ring-[#3f1f69] border-gray-300 rounded"
                  />
                  <label 
                    htmlFor={`selected-${courseCode}`}
                    className="flex-1 cursor-pointer font-medium text-[#3f1f69]"
                  >
                    <span className="font-bold">{courseCodesDisplay}</span>
                    {course.course_title && (
                      <span className="font-normal">: {course.course_title}</span>
                    )}
                  </label>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Searchable/Scrollable Unselected Courses */}
      <div className="max-h-96 overflow-y-auto border rounded p-4 space-y-2">
        {unselectedCourses.length === 0 && selectedCoursesData.length === 0 && (
          <p className="text-center text-gray-500">No courses found.</p>
        )}
        
        {unselectedCourses.length === 0 && selectedCoursesData.length > 0 && searchTerm && (
          <p className="text-center text-gray-500">No additional courses found matching "{searchTerm}".</p>
        )}
        
        {unselectedCourses.map((course) => {
          const courseCodesArray = Array.isArray(course.course_codes)
            ? course.course_codes
            : [course.course_codes];
          const courseCode = courseCodesArray[0];
          const courseCodesDisplay = courseCodesArray.join(", ");

          return (
            <div 
              key={`unselected-${courseCode}`}
              className="flex items-center p-2 rounded hover:bg-gray-50"
            >
              <input
                type="checkbox"
                id={`unselected-${courseCode}`}
                checked={false}
                onChange={(e) => {
                  e.preventDefault();
                  toggleCourse(courseCode);
                }}
                className="mr-3 h-4 w-4 text-[#3f1f69] focus:ring-[#3f1f69] border-gray-300 rounded"
              />
              <label 
                htmlFor={`unselected-${courseCode}`}
                className="flex-1 cursor-pointer"
              >
                <span className="font-medium">{courseCodesDisplay}</span>
                {course.course_title && (
                  <span className="text-gray-600">: {course.course_title}</span>
                )}
              </label>
            </div>
          );
        })}
      </div>

      <div className="flex gap-4">
        <button
          onClick={handleBack}
          className="flex-1 bg-gray-500 text-white py-2 rounded hover:bg-gray-600 transition"
        >
          {fromTranscriptUpload ? "Cancel" : "Back"}
        </button>
        <button
          onClick={handleSubmit}
          className="flex-1 bg-[#3f1f69] text-white py-2 rounded hover:bg-[#5b2ca0] transition"
        >
          {fromTranscriptUpload 
            ? "Save Changes" 
            : (parseInt(index) + 1 < selectedSemesters.length ? "Next Semester" : "Finish")
          }
        </button>
      </div>
    </div>
  );
}