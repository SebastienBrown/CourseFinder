import React, { useState } from 'react';

export default function OnboardingPopup({ isOpen, onClose, isPublicMode = false }) {
  const [currentStep, setCurrentStep] = useState(0);
  
  if (!isOpen) return null;

  const steps = [
    {
      title: "Welcome to The Visual Open Curriculum!",
      content: (
        <div className="space-y-4">
          <p className="text-gray-700">
            This interactive visualization helps you explore course relationships and plan your academic journey at Amherst College.
          </p>
          <p className="text-gray-700">
            Let's walk through the key features to help you get started.
          </p>
        </div>
      ),
      image: "🎓"
    },
    {
      title: "Two Main Views",
      content: (
        <div className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-start space-x-3">
              <div className="bg-[#3f1f69] text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold">1</div>
              <div>
                <h4 className="font-semibold text-[#3f1f69]">Single Semester View</h4>
                <p className="text-gray-700 text-sm">
                  Explore courses for a specific semester. Use the semester slider at the bottom to switch between different terms.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <div className="bg-[#3f1f69] text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold">2</div>
              <div>
                <h4 className="font-semibold text-[#3f1f69]">My Course History</h4>
                <p className="text-gray-700 text-sm">
                  {isPublicMode 
                    ? "View your complete academic journey across all semesters (available when signed in)."
                    : "View your complete academic journey across all semesters. Your courses will be highlighted on the graph."
                  }
                </p>
              </div>
            </div>
          </div>
        </div>
      ),
      image: "📊"
    },
    {
      title: "Course Search & Selection",
      content: (
        <div className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-start space-x-3">
              <div className="bg-[#3f1f69] text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold">1</div>
              <div>
                <h4 className="font-semibold text-[#3f1f69]">Search Bar</h4>
                <p className="text-gray-700 text-sm">
                  Type course codes (like "MATH-111") or course titles to find specific courses. Matching courses will appear as suggestions.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <div className="bg-[#3f1f69] text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold">2</div>
              <div>
                <h4 className="font-semibold text-[#3f1f69]">Course Selection</h4>
                <p className="text-gray-700 text-sm">
                  Click on any course node on the graph to view details and select/deselect it. Selected courses appear in the bottom panel.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <div className="bg-[#3f1f69] text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold">3</div>
              <div>
                <h4 className="font-semibold text-[#3f1f69]">Similar Courses</h4>
                <p className="text-gray-700 text-sm">
                  When you click on a course, you'll see a list of similar courses based on content and requirements.
                </p>
              </div>
            </div>
          </div>
        </div>
      ),
      image: "🔍"
    },
    {
      title: "Graph Features & Controls",
      content: (
        <div className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-start space-x-3">
              <div className="bg-[#3f1f69] text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold">1</div>
              <div>
                <h4 className="font-semibold text-[#3f1f69]">Zoom & Pan</h4>
                <p className="text-gray-700 text-sm">
                  Use your mouse wheel to zoom in/out. Click and drag to pan around the graph. Use the "Reset View" button to return to the original view.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <div className="bg-[#3f1f69] text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold">2</div>
              <div>
                <h4 className="font-semibold text-[#3f1f69]">Department Legend</h4>
                <p className="text-gray-700 text-sm">
                  The left panel shows department colors and shapes. Courses are grouped by academic divisions (Arts, Humanities, Sciences, Social Sciences).
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <div className="bg-[#3f1f69] text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold">3</div>
              <div>
                <h4 className="font-semibold text-[#3f1f69]">Course Shapes</h4>
                <p className="text-gray-700 text-sm">
                  Different shapes represent different academic divisions: circles (Arts), squares (Humanities), triangles (Sciences), stars (Social Sciences), and double circles (First Year Seminars).
                </p>
              </div>
            </div>
          </div>
        </div>
      ),
      image: "🎯"
    },
    {
      title: "Special Features",
      content: (
        <div className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-start space-x-3">
              <div className="bg-[#3f1f69] text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold">1</div>
              <div>
                <h4 className="font-semibold text-[#3f1f69]">Conflict Detection</h4>
                <p className="text-gray-700 text-sm">
                  In Single Semester View, toggle "Eliminate Conflicts" to hide courses that conflict with your selected courses.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <div className="bg-[#3f1f69] text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold">2</div>
              <div>
                <h4 className="font-semibold text-[#3f1f69]">Download Image</h4>
                <p className="text-gray-700 text-sm">
                  In My Course History view, use the "Download as Image" button to save your academic journey as a high-resolution image.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <div className="bg-[#3f1f69] text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold">3</div>
              <div>
                <h4 className="font-semibold text-[#3f1f69]">Add Courses</h4>
                <p className="text-gray-700 text-sm">
                  {isPublicMode 
                    ? "Sign in to add your course history and see your personalized academic journey."
                    : "Use the 'Add Courses' button to input your course history and see your personalized academic journey."
                  }
                </p>
              </div>
            </div>
          </div>
        </div>
      ),
      image: "⚙️"
    },
    {
      title: "You're All Set!",
      content: (
        <div className="space-y-4">
          <p className="text-gray-700">
            You now know how to navigate the Visual Open Curriculum. Start exploring by:
          </p>
          <ul className="list-disc list-inside space-y-2 text-gray-700 text-sm">
            <li>Searching for specific courses using the search bar</li>
            <li>Clicking on course nodes to see details and similar courses</li>
            <li>Switching between Single Semester View and My Course History</li>
            <li>Using the semester slider to explore different terms</li>
            <li>Zooming and panning to explore the course landscape</li>
          </ul>
          <p className="text-gray-700">
            Happy course planning! 🎓
          </p>
        </div>
      ),
      image: "🎉"
    }
  ];

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      onClose();
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSkip = () => {
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center px-4">
      <div className="bg-white max-w-2xl w-full max-h-[90vh] overflow-y-auto rounded-xl shadow-xl p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="text-3xl">{steps[currentStep].image}</div>
            <h2 className="text-2xl font-bold text-[#3f1f69]">
              {steps[currentStep].title}
            </h2>
          </div>
          <button
            onClick={handleSkip}
            className="text-gray-400 hover:text-gray-600 text-xl font-semibold"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="mb-6">
          {steps[currentStep].content}
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-[#3f1f69] h-2 rounded-full transition-all duration-300"
              style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
            ></div>
          </div>
          <div className="text-center text-sm text-gray-500 mt-2">
            Step {currentStep + 1} of {steps.length}
          </div>
        </div>

        {/* Navigation Buttons */}
        <div className="flex justify-between items-center">
          <button
            onClick={handlePrevious}
            disabled={currentStep === 0}
            className={`px-4 py-2 rounded-md font-medium transition-colors ${
              currentStep === 0
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Previous
          </button>
          
          <button
            onClick={handleNext}
            className="px-6 py-2 bg-[#3f1f69] text-white rounded-md font-medium hover:bg-[#311a4d] transition-colors"
          >
            {currentStep === steps.length - 1 ? 'Get Started!' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  );
} 