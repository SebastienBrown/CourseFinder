// src/IntakePrompt.jsx
import React from "react";
import { useNavigate } from "react-router-dom";

export default function IntakePrompt() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-6">
      <h1 className="text-2xl font-bold">What would you like to do?</h1>
      <div className="flex gap-4">
        <button
          onClick={() => navigate("/upload")}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Upload Transcript
        </button>
        <button
          onClick={() => navigate("/intake")}
          className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
        >
          Manual Course Intake
        </button>
      </div>
    </div>
  );
}
