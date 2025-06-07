import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import CourseSimilarityPrecomputedGraph from "./CourseSimilarityPrecomputedGraph";
import CourseInput from "./CourseInput";
import { supabase } from "./supabaseClient";
import Auth from "./Auth";
import Intake from "./Intake"; // intake semester checklist
import SemesterCourseIntake from "./SemesterCourseIntake"; // per-semester course selector

export default function App() {
  const [user, setUser] = useState(null);
  const [highlighted, setHighlighted] = useState([]);
  const [conflicted, setConflicted] = useState([]);
  const [currentSemester, setCurrentSemester] = useState("Spring 2024");

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
            <div className="flex flex-col min-h-screen bg-[#f9f7fb]">
              <div className="w-full max-w-[1200px] mx-auto space-y-6 mb-4 px-4">
                <div className="flex justify-between items-center mt-6">
                  <h1 className="text-3xl font-bold text-[#3f1f69] text-center">
                    The Visual Open Curriculum
                  </h1>
                  <button
                    onClick={logout}
                    className="bg-red-500 text-white px-4 py-2 rounded"
                  >
                    Sign Out
                  </button>
                </div>
                <CourseInput
                  onHighlight={setHighlighted}
                  onConflicted={setConflicted}
                  currentSemester={currentSemester}
                />
              </div>
              <div className="flex-grow relative px-4">
                <CourseSimilarityPrecomputedGraph
                  mode="tsne"
                  highlighted={highlighted}
                  conflicted={conflicted}
                  onSemesterChange={setCurrentSemester}
                />
              </div>
            </div>
          }
        />
        <Route path="*" element={<Navigate to="/intake" replace />} />
      </Routes>
    </Router>
  );
}
