import React from "react";

export default function CoursePopup({ course, onClose, onHighlight, highlighted, activeTab, onSelect }) {
  if (!course) return null;

  // Check if any of the course codes are already highlighted
  const isSelected = course.course_codes && 
    (Array.isArray(course.course_codes) 
      ? course.course_codes.some(code => highlighted.includes(code)) ||
        highlighted.includes(course.course_codes.join('/'))
      : highlighted.includes(course.course_codes));

  const handleSelect = () => {
    if (!course.course_codes) return;
    
    // Use onSelect (handleAddSelectedCourse) instead of onHighlight
    onSelect(course);
    onClose();
  };

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

        <p className="text-gray-600">
          <strong>Semester:</strong> {course.semester || 'Unavailable'}
        </p>

        <p className="text-gray-600">
          <strong>Course Code(s):</strong> {course.course_codes ? course.course_codes.join(', ') : 'Unavailable'}
        </p>

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

        {activeTab === 'thisSemester' && (
          <div className="flex justify-end pt-4">
            <button
              onClick={handleSelect}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${
                isSelected
                  ? 'bg-red-100 text-red-700 hover:bg-red-200'
                  : 'bg-[#3f1f69] text-white hover:bg-[#311a4d]'
              }`}
            >
              {isSelected ? 'Deselect Course' : 'Select Course'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
