import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "./supabaseClient";
import { AVAILABLE_SEMESTERS, API_BASE_URL } from "./config";

export default function Intake() {
  const [userId, setUserId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedCourses, setSelectedCourses] = useState({});
  const [selectedSemester, setSelectedSemester] = useState(null);
  const [backendOutput, setBackendOutput] = useState(null);

  const [error, setError] = useState(null);

  // Use AVAILABLE_SEMESTERS from config.js
  const semesters = AVAILABLE_SEMESTERS;

  const [selectedSemesters, setSelectedSemesters] = useState([]);
  const navigate = useNavigate();

  const handleCheckboxChange = (semester) => {
    setSelectedSemesters((prev) =>
      prev.includes(semester)
        ? prev.filter((s) => s !== semester)
        : [...prev, semester]
    );
  };

  const handleSubmit = () => {
    localStorage.setItem("selectedSemesters", JSON.stringify(selectedSemesters));
    // initialize empty selections dictionary
    localStorage.setItem("semesterCourses", JSON.stringify({}));
    navigate("/intake/courses/0"); // start course intake at first semester
  };

  return (
    <div className="max-w-xl mx-auto mt-12 p-6 bg-white shadow rounded space-y-6">
      <h2 className="text-2xl font-bold text-center text-[#3f1f69]">
        Select Completed Semesters
      </h2>

      <div className="space-y-2">
        {semesters.map((semester) => (
          <div key={semester} className="flex items-center">
            <input
              type="checkbox"
              id={semester}
              checked={selectedSemesters.includes(semester)}
              onChange={() => handleCheckboxChange(semester)}
              className="mr-2"
            />
            <label htmlFor={semester}>{semester}</label>
          </div>
        ))}
      </div>

      <button
        onClick={handleSubmit}
        disabled={selectedSemesters.length === 0}
        className="w-full bg-[#3f1f69] text-white py-2 rounded hover:bg-[#5b2ca0] transition"
      >
        Next
      </button>
    </div>
  );
}
