import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { AVAILABLE_SEMESTERS } from "./config";

export default function Intake() {
  const [selectedSemesters, setSelectedSemesters] = useState([]);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const navigate = useNavigate();
  const semesters = AVAILABLE_SEMESTERS;
  const dropdownRef = useRef(null);

  const handleCheckboxChange = (semester) => {
    setSelectedSemesters((prev) =>
      prev.includes(semester)
        ? prev.filter((s) => s !== semester)
        : [...prev, semester]
    );
  };

  const handleSubmit = () => {
    localStorage.setItem("selectedSemesters", JSON.stringify(selectedSemesters));
    localStorage.setItem("semesterCourses", JSON.stringify({}));
    navigate("/intake/courses/0");
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      // Check if the click target is not inside the dropdown
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    };
  
    const handleEscape = (event) => {
      if (event.key === "Escape") {
        setDropdownOpen(false);
      }
    };
  
    // Use 'click' instead of 'mousedown'
    document.addEventListener("click", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
  
    return () => {
      document.removeEventListener("click", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);
  

  return (
    <div className="max-w-xl mx-auto mt-12 p-6 bg-white shadow rounded space-y-6">
      <h2 className="text-2xl font-bold text-center text-[#3f1f69]">
        Select Completed Semesters
      </h2>

      <div className="relative" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="w-full bg-[#f4f0fa] border border-[#5d3c85] rounded px-4 py-2 text-left focus:outline-none focus:ring-2 focus:ring-[#3f1f69]"
        >
          {selectedSemesters.length > 0
            ? selectedSemesters.join(", ")
            : "Select semesters..."}
        </button>

        {dropdownOpen && (
          <div className="absolute z-50 mt-1 w-full max-h-60 overflow-y-auto bg-white border border-[#eae6f4] rounded shadow-lg">
            {semesters.map((semester) => (
              <label
                key={semester}
                className="flex items-center px-4 py-2 hover:bg-[#f4f0fa] cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedSemesters.includes(semester)}
                  onChange={() => handleCheckboxChange(semester)}
                  className="mr-2"
                />
                {semester}
              </label>
            ))}
          </div>
        )}
      </div>

      <button
        onClick={handleSubmit}
        disabled={selectedSemesters.length === 0}
        className="w-full bg-[#3f1f69] text-white py-2 rounded hover:bg-[#5b2ca0] transition disabled:opacity-50"
      >
        Next
      </button>
    </div>
  );
}
