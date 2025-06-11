import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { supabase } from "./supabaseClient";
import CourseSimilarityPrecomputedGraph from "./CourseSimilarityPrecomputedGraph";
import Auth from "./Auth";
import Intake from "./Intake"; // intake semester checklist
import SemesterCourseIntake from "./SemesterCourseIntake"; // per-semester course selector
import { useNavigate } from "react-router-dom";
import CourseInput from "./CourseInput";
import { CURRENT_SEMESTER, API_BASE_URL } from "./config";


//console.log("🟢 Using backend URL:", process.env.REACT_APP_BACKEND_URL);


// Layout component for shared UI elements
function Layout({ children, logout }) {
  const navigate = useNavigate();
  
  return (
    <div className="flex flex-col min-h-screen bg-[#f9f7fb]">
      <div className="w-full max-w-[1200px] mx-auto space-y-6 mb-4 px-4">
        <div className="flex justify-between items-center mt-6">
          <h1 className="text-3xl font-bold text-[#3f1f69] text-center">
            The Visual Open Curriculum
          </h1>
          <div className="flex space-x-2">
            <button
              onClick={logout}
              className="bg-red-500 text-white px-4 py-2 rounded"
            >
              Sign Out
            </button>
            <button
              onClick={() => navigate("/intake")}
              className="bg-blue-500 text-white px-4 py-2 rounded"
            >
              Add Courses
            </button>
          </div>
        </div>
      </div>
      {children}
    </div>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [highlighted, setHighlighted] = useState([]);
  const [conflicted, setConflicted] = useState([]);
  const [currentSemester, setCurrentSemester] = useState(CURRENT_SEMESTER);
  const backendUrl=process.env.REACT_APP_BACKEND_URL;

  const handleHighlight = (newHighlighted) => {
    // Check if newHighlighted is a function
    if (typeof newHighlighted === 'function') {
      // If it is, call it with the current state
      setHighlighted(newHighlighted);
    } else {
      // If not, use it directly as the new state
      setHighlighted(newHighlighted);
    }
  };

  // Function to check conflicts with the backend
  const checkConflicts = async (courses, semester) => {
    try {
      const response = await fetch(`${backendUrl}/conflicted_courses`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          taken_courses: courses,
          semester: semester 
        }),
      });
      const data = await response.json();
      setConflicted(data.conflicted_courses);
    } catch (error) {
      console.error('Error checking conflicts:', error);
      setConflicted([]);
    }
  };

  // Effect to handle semester changes
  useEffect(() => {
    // When semester changes, check conflicts with empty highlighted list
    checkConflicts(highlighted, currentSemester);
  }, [currentSemester]);

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => setUser(user));
    supabase.auth.onAuthStateChange((_, session) => {
      setUser(session?.user || null);
    });
  }, []);

  const logout = async () => {
    await supabase.auth.signOut();
    setUser(null);
  };

  if (!user) return <Auth onLogin={setUser} />;

  return (
    <Router>
      <Routes>
        <Route path="/intake" element={<Intake />} />
        <Route path="/intake/courses/:index" element={<SemesterCourseIntake />} />
        <Route
          path="/graph"
          element={
            <Layout logout={logout}>
              <CourseInput
                onHighlight={handleHighlight}
                onConflicted={setConflicted}
                currentSemester={currentSemester}
                highlighted={highlighted}
              />
              <CourseSimilarityPrecomputedGraph
                highlighted={highlighted}
                conflicted={conflicted}
                setHighlighted={setHighlighted}
                setConflicted={setConflicted}
                currentSemester={currentSemester}
                onSemesterChange={setCurrentSemester}
                onConflicted={setConflicted}
                onHighlight={handleHighlight}
              />
            </Layout>
          }
        />
        <Route path="*" element={<Navigate to="/intake" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
