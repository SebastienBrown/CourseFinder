// src/IntakePrompt.jsx
import React from "react";
import { useNavigate } from "react-router-dom";

export default function IntakePrompt() {
  const navigate = useNavigate();

  return (
    <div className="flex items-center justify-center min-h-screen bg-[#f9f7fb] px-4">
      <div className="bg-white rounded-2xl shadow-lg p-10 max-w-lg w-full flex flex-col gap-6">
        <h1 className="text-3xl font-bold text-[#3f1f69] text-center">
          What would you like to do?
        </h1>
        <p className="text-center text-gray-600">
          First, let us know what courses you have taken at Amherst. You can upload
          your transcript to auto-populate your courses, or manually input them
          yourself.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          {/* <button
            onClick={() => navigate("/upload")}
            className="flex-1 px-6 py-3 bg-[#3f1f69] text-white rounded-xl font-semibold shadow hover:bg-[#311a4d] transition"
          >
            Upload Transcript
          </button> */}
          <button
            onClick={() => navigate("/intake")}
            className="flex-1 px-6 py-3 bg-[#5d3c85] text-white rounded-xl font-semibold shadow hover:bg-[#4b2f72] transition"
          >
            Manually Input Courses
          </button>
        </div>
      </div>
    </div>
  );
}
