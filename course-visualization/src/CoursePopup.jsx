import React from "react";

export default function CoursePopup({ course, onClose, onHighlight, highlighted, activeTab, onSelect, courseDetailsData, setSelectedCourse }) {
  if (!course) return null;

  // Ensure highlighted is an array
  const highlightedArray = Array.isArray(highlighted) ? highlighted : [];

  // Check if any of the course codes are already highlighted
  const isSelected = course.course_codes && 
    (Array.isArray(course.course_codes) 
      ? course.course_codes.some(code => highlightedArray.includes(code)) ||
        highlightedArray.includes(course.course_codes.join('/'))
      : highlightedArray.includes(course.course_codes));

  const handleSelect = () => {
    if (!course.course_codes) return;
    
    // Use onSelect (handleAddSelectedCourse) instead of onHighlight
    onSelect(course);
    console.log("Added a course");
    
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

        {course.similar_courses && course.similar_courses.length > 0 && (
          <div className="border-t pt-4">
            <h3 className="text-lg font-semibold text-[#3f1f69] mb-2">Similar Courses</h3>
            <div className="space-y-2">
              {course.similar_courses.map((similar, index) => {
                // Determine if similar.code is an array or string
                const similarCodes = Array.isArray(similar.code) ? similar.code : [similar.code];
                // Find the course data for this similar course code(s)
                const similarCourse = courseDetailsData.find(c => {
                  const courseCodes = Array.isArray(c.course_codes) ? c.course_codes : [c.course_codes];
                  return courseCodes.some(code => similarCodes.includes(code));
                });
                return (
                  <button
                    key={index}
                    onClick={() => {
                      onClose();
                      if (similarCourse) {
                        setSelectedCourse(similarCourse);
                      }
                    }}
                    className="block w-full text-left px-3 py-2 rounded-md hover:bg-gray-100 transition-colors"
                  >
                    <span className="font-medium text-[#3f1f69]">
                      {similarCourse?.course_codes?.join(', ') || 
                       (Array.isArray(similar.code) ? similar.code.join(', ') : similar.code)}
                    </span>
                    <span className="text-gray-600 ml-2">
                      {similarCourse?.course_title || 'Course Title Unavailable'}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

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
