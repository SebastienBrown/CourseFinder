import React, { useState } from "react";
import CourseSimilarityPrecomputedGraph from "./CourseSimilarityPrecomputedGraph";
import CourseInput from "./CourseInput";

export default function App() {
  const [mode] = useState("precomputed-tsne");
  const [highlighted, setHighlighted] = useState([]);
  const [conflicted, setConflicted] = useState([]);
  const [currentSemester, setCurrentSemester] = useState("Spring 2024"); // Default semester

  return (
    <div className="flex flex-col min-h-screen bg-[#f9f7fb]">
      {/* Title + Search Bar */}
      <div className="w-full max-w-[1200px] mx-auto space-y-6 mb-4 px-4">
        <h1 className="text-3xl font-bold text-[#3f1f69] text-center mt-6">
          The Visual Open Curriculum
        </h1>
        <CourseInput
          onHighlight={setHighlighted}
          onConflicted={setConflicted}
          currentSemester={currentSemester}
        />
      </div>

      {/* Graph Container */}
      <div className="flex-grow relative px-4">
        <CourseSimilarityPrecomputedGraph
          mode="tsne"
          highlighted={highlighted}
          conflicted={conflicted}
          onSemesterChange={setCurrentSemester}
        />
      </div>
    </div>
  );
}
