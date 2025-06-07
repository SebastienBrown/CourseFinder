import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { supabase } from "./supabaseClient"; // make sure this points to your initialized Supabase client

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

  // Load courses JSON dynamically on mount or semester change
  useEffect(() => {
    if (!semester) {
      navigate("/graph");
      return;
    }

    async function fetchCourses() {
      try {
        const res = await fetch(`/llm_cleaned/amherst_courses_${semester}.json`);
        const data = await res.json();
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
  
    // You can decide if you want OR (either match) or just codesMatch
    return codesMatch;
  });

  const toggleCourse = (courseCode) => {
    setSelectedCourses((prev) =>
      prev.includes(courseCode) ? prev.filter((c) => c !== courseCode) : [...prev, courseCode]
    );
  };

  const handleSubmit = async () => {
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
        const response = await fetch("http://127.0.0.1:8000/submit_courses", {
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

  if (!semester) return null;


  const uniqueCoursesMap = new Map();

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

const uniqueCourses = Array.from(uniqueCoursesMap.values());

  return (
    <div className="max-w-xl mx-auto mt-12 p-6 bg-white shadow rounded space-y-6">
      <h2 className="text-2xl font-bold text-center text-[#3f1f69]">
        Select Courses for Semester {semester}
      </h2>

      <input
        type="text"
        placeholder="Search courses..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        className="w-full border rounded px-3 py-2"
      />

      <div className="max-h-96 overflow-y-auto border rounded p-2 space-y-2">
        {uniqueCourses.map((course) => {
          const courseCodesArray = Array.isArray(course.course_codes)
            ? course.course_codes
            : [course.course_codes];
          const courseCode = courseCodesArray[0]; // used for selection logic
          const courseCodesDisplay = courseCodesArray.join(", "); // display all codes comma-separated

          return (
            <div key={courseCode} className="flex items-center">
              <input
                type="checkbox"
                id={courseCode}
                checked={selectedCourses.includes(courseCode)}
                onChange={() => toggleCourse(courseCode)}
                className="mr-2"
              />
              <label htmlFor={courseCode}>{courseCodesDisplay}</label>
            </div>
          );
        })}

        {filteredCourses.length === 0 && (
          <p className="text-center text-gray-500">No courses found.</p>
        )}
      </div>

      <button
        onClick={handleSubmit}
        className="w-full bg-[#3f1f69] text-white py-2 rounded hover:bg-[#5b2ca0] transition"
      >
        {parseInt(index) + 1 < selectedSemesters.length ? "Next Semester" : "Finish"}
      </button>
    </div>
  );
}
