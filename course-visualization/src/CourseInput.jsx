import React, { useState } from "react";

export default function CourseInput({ onHighlight }) {
  const [input, setInput] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    const codes = input
      .split(",")
      .map((code) => code.trim().toUpperCase())
      .filter((code) => code.length > 0);
    onHighlight(codes);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full max-w-[1200px] mx-auto flex flex-wrap items-center gap-4 bg-[#f9f7fb] border border-[#eae6f4] rounded-xl px-6 py-4 mb-6"
    >
      <label
        htmlFor="course-input"
        className="font-semibold text-[#3f1f69] text-sm"
      >
        Enter Your Current Courses:
      </label>

      <input
        id="course-input"
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="e.g. AMST-117, EDST-200"
        className="flex-1 min-w-[200px] px-3 py-2 border border-[#5d3c85] bg-[#f4f0fa] text-sm rounded-md focus:outline-none focus:ring-2 focus:ring-[#3f1f69]"
      />

      <button
        type="submit"
        className="px-4 py-2 text-sm font-semibold bg-[#3f1f69] text-white rounded-md hover:bg-[#311a4d] transition"
      >
        Submit
      </button>
    </form>
  );
}
