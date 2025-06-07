import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

const fixedSemesters = [
  "2223F",
  "2223S",
  "2324F",
  "2324S",
  "2425F",
  "2425S",
  "2526F",
  "2526S",
];

export default function Intake() {
  const [selectedSemesters, setSelectedSemesters] = useState([]);
  const navigate = useNavigate();

  const handleCheckboxChange = (semester) => {
    setSelectedSemesters((prev) =>
      prev.includes(semester)
        ? prev.filter((s) => s !== semester)
        : [...prev, semester]
    );
  };

  // ... same as before, except
const handleSubmit = () => {
    localStorage.setItem("selectedSemesters", JSON.stringify(selectedSemesters));
    // initialize empty selections dictionary
    localStorage.setItem("semesterCourses", JSON.stringify({}));
    navigate("/intake/courses/0"); // start course intake at first semester
  };
  

  return (
    <div className="max-w-xl mx-auto mt-12 p-6 bg-white shadow rounded space-y-6">
      <h2 className="text-2xl font-bold text-center text-[#3f1f69]">
        Select Semesters
      </h2>

      <div className="space-y-2">
        {fixedSemesters.map((semester) => (
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
        Submit
      </button>
    </div>
  );
}
