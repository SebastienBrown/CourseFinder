import React from "react";

export default function CoursePopup({ course, onClose }) {
  if (!course) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center px-4"
      onClick={onClose}
    >
      <div
        className="bg-white max-w-xl w-full max-h-[90vh] overflow-y-auto rounded-xl shadow-xl p-6 space-y-4 relative"
        onClick={(e) => e.stopPropagation()} // prevent closing when clicking inside modal
      >
        <button
          onClick={onClose}
          className="absolute top-3 right-4 text-gray-400 hover:text-black text-xl font-semibold"
        >
          ×
        </button>

        <h2 className="text-2xl font-semibold text-[#3f1f69]">
          {course.course_title || course.id}
        </h2>

        <p className="text-gray-700 whitespace-pre-line">
          {course.description || "No course description available."}
        </p>

        <p className="text-gray-600">
          <strong>Instructor:</strong>{" "}
          {course.faculty
            ? Object.values(course.faculty)?.[0]?.[0] || "Unavailable"
            : "Unavailable"}
        </p>

        <p className="text-gray-500">
          <strong>When:</strong>{" "}
          {course.times_and_locations
            ? Object.values(
                Object.values(course.times_and_locations)?.[0] || {}
              )[0]
                ?.map((s) => `${s.day} ${s.time}`)
                .join(", ") || "Unavailable"
            : "Unavailable"}
        </p>
      </div>
    </div>
  );
}
