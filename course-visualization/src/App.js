import React, { useState, useEffect, useCallback } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { supabase } from "./supabaseClient";
import CourseSimilarityPrecomputedGraph from "./CourseSimilarityPrecomputedGraph";
import Auth from "./Auth";
import Intake from "./Intake"; // intake semester checklist
import SemesterCourseIntake from "./SemesterCourseIntake"; // per-semester course selector
import { useNavigate } from "react-router-dom";
import CourseInput from "./CourseInput";
import { CURRENT_SEMESTER } from "./config";
import Upload from "./Upload";
import IntakePrompt from "./IntakePrompt";
import SurpriseButton from "./SurpriseButton";
import TermsModal from "./TermsModal"; // adjust path
import UserInfoPopup from "./UserInfoPopup";
import AccountDropdown from "./AccountDropdown";
import { SemesterProvider } from './SemesterContext';
import SubmissionPage from "./SubmissionPage";


//console.log("🟢 Using backend URL:", process.env.REACT_APP_BACKEND_URL);


// Layout component for shared UI elements
function Layout({ children, logout, onShowHelp, onShowUserInfo }) {
  const navigate = useNavigate();
  
  return (
    <div className="flex flex-col min-h-screen bg-[#f9f7fb]">
      <div className="w-full max-w-[1200px] mx-auto space-y-6 mb-4 px-4">
        <div className="flex justify-between items-center mt-6">
          <h1 className="text-3xl font-bold text-[#3f1f69] text-center">
            The Visual Open Curriculum
          </h1>
          <div className="flex space-x-2">
          <AccountDropdown 
            onSignOut={logout}
            onShowUserInfo={onShowUserInfo}
          />

          <button
            onClick={onShowHelp}
            className="px-4 py-2 bg-purple-500 text-white rounded-lg font-semibold shadow hover:bg-purple-200 transition-all duration-200 h-10"
          >
            Help
          </button>

          <button
            onClick={() => navigate("/question")}
            className="px-4 py-2 bg-purple-800 text-white rounded-lg font-semibold shadow hover:bg-purple-800 transition-all duration-200 h-10"
          >
            Ask a Question
          </button>

          <button
            onClick={() => navigate("/intake-prompt")}
            className="px-4 py-2 bg-[#3f1f69] text-white rounded-lg font-semibold shadow hover:bg-[#311a4d] transition-all duration-200 h-10"
          >
            Add Past Courses
          </button>
        </div>

        </div>
      </div>
      {children}
    </div>
  );
}

// Public layout component without authentication controls
function PublicLayout({ children, onShowHelp }) {
  const navigate = useNavigate();
  
  return (
    <div className="flex flex-col min-h-screen bg-[#f9f7fb]">
      <div className="w-full max-w-[1200px] mx-auto space-y-6 mb-4 px-4">
        <div className="flex justify-between items-center mt-6">
          <h1 className="text-3xl font-bold text-[#3f1f69] text-center">
            The Visual Open Curriculum
          </h1>
          <div className="flex space-x-2">
            <button
              onClick={onShowHelp}
              className="bg-gray-500 text-white px-4 py-2 rounded"
            >
              Help
            </button>
            <button
              onClick={() => navigate("/")}
              className="bg-blue-500 text-white px-4 py-2 rounded"
            >
              Sign In
            </button>
          </div>
        </div>
      </div>
      {children}
    </div>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [highlighted, setHighlighted] = useState([]);
  const [conflicted, setConflicted] = useState([]);
  const [currentSemester, setCurrentSemester] = useState(CURRENT_SEMESTER);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const backendUrl=process.env.REACT_APP_BACKEND_URL;
  const [showTerms, setShowTerms] = useState(false);
  const [showUserInfoPopup, setShowUserInfoPopup] = useState(false);
  const [pendingUser, setPendingUser] = useState(null);

  const handleHighlight = useCallback((newHighlighted) => {
    // Check if newHighlighted is a function
    if (typeof newHighlighted === 'function') {
      // If it is, call it with the current state
      setHighlighted(newHighlighted);
    } else {
      // If not, use it directly as the new state
      setHighlighted(newHighlighted);
    }
  }, []);

  // Function to check conflicts with the backend
  const checkConflicts = useCallback(async (courses, semester) => {
    try {
      const response = await fetch(`${backendUrl}/conflicted_courses`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          taken_courses: courses,
          semester: semester 
        }),
      });
      const data = await response.json();
      setConflicted(data.conflicted_courses);
    } catch (error) {
      console.error('Error checking conflicts:', error);
      setConflicted([]);
    }
  }, [backendUrl]);

  // Handler for surprise recommendation
  const handleSurpriseRecommendation = useCallback((courseCodes) => {
    // Highlight the recommended course on the graph
    setHighlighted(courseCodes);
    // Check for conflicts with the recommended course
    checkConflicts(courseCodes, currentSemester);
  }, [checkConflicts, currentSemester]);

  // Effect to handle semester changes
  useEffect(() => {
    // When semester changes, check conflicts with current highlighted list
    checkConflicts(highlighted, currentSemester);
  }, [currentSemester, highlighted, checkConflicts]);

  // Helper function to check if user has provided their info
  const checkUserInfo = async (user) => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      
      if (!token) {
        console.error("No valid session token found");
        return false;
      }

      const response = await fetch(`${backendUrl}/check_user_info`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        console.error("Failed to check user info");
        return false;
      }

      const data = await response.json();
      return data.has_info;
    } catch (error) {
      console.error("Error checking user info:", error);
      return false;
    }
  };

  const showUserInfoPopupForUser = (user) => {
    setPendingUser(user);
    setShowUserInfoPopup(true);
  };

  useEffect(() => {
    supabase.auth.getUser().then(async ({ data: { user } }) => {
      if (user) {
        const hasUserInfo = await checkUserInfo(user);
        if (!hasUserInfo) {
          showUserInfoPopupForUser(user);
        } else {
          setUser(user);
        }
      } else {
        setUser(null);
      }
    });
    
    supabase.auth.onAuthStateChange(async (_, session) => {
      if (session?.user) {
        const hasUserInfo = await checkUserInfo(session.user);
        if (!hasUserInfo) {
          showUserInfoPopupForUser(session.user);
        } else {
          setUser(session.user);
        }
      } else {
        setUser(null);
      }
    });
  }, []);

  const logout = async () => {
    await supabase.auth.signOut();
    setUser(null);
  };

  // UserInfoPopup handlers
  const handleUserInfoSave = async (userInfo) => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      
      if (!token) {
        throw new Error("No valid session token found");
      }

      const response = await fetch(`${backendUrl}/save_user_info`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify(userInfo),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to save user information");
      }

      setShowUserInfoPopup(false);
      setPendingUser(null);
      
      // Proceed with login if there's a pending user
      if (pendingUser) {
        setUser(pendingUser);
      }
    } catch (error) {
      console.error("Error saving user info:", error);
      throw error;
    }
  };

  const handleUserInfoClose = () => {
    setShowUserInfoPopup(false);
    setPendingUser(null);
    
    // Still proceed with login even if they close the popup
    if (pendingUser) {
      setUser(pendingUser);
    }
  };

  // Only show Auth component if no user and not on public routes
  const isPublicRoute = window.location.pathname === '/public-graph';
  
  if (!user && !isPublicRoute) return <Auth onLogin={setUser} onShowUserInfo={showUserInfoPopupForUser} />;

  return (
    <SemesterProvider>
    <Router>
  <Routes>
    {/* ✅ Default landing page is now Graph */}
            <Route
              path="/"
              element={
                <Layout logout={logout} onShowHelp={() => setShowOnboarding(true)} onShowUserInfo={() => showUserInfoPopupForUser(user)}>
                  <CourseInput
            onHighlight={handleHighlight}
            onConflicted={setConflicted}
            currentSemester={currentSemester}
            highlighted={highlighted}
          />
          <CourseSimilarityPrecomputedGraph
            highlighted={highlighted}
            conflicted={conflicted}
            setHighlighted={setHighlighted}
            setConflicted={setConflicted}
            currentSemester={currentSemester}
            onSemesterChange={setCurrentSemester}
            onConflicted={setConflicted}
            onHighlight={handleHighlight}
            showOnboarding={showOnboarding}
            setShowOnboarding={setShowOnboarding}
          />
          <SurpriseButton onSurpriseRecommendation={handleSurpriseRecommendation} />
        </Layout>
      }
    />

    {/* ✅ IntakePrompt moved to its own route */}
    <Route path="/intake-prompt" element={<IntakePrompt />} />
    <Route path="question" element={<SubmissionPage />} />

    <Route path="/upload" element={<Upload />} />
    <Route path="/intake" element={<Intake />} />
    <Route path="/intake/courses/:index" element={<SemesterCourseIntake />} />

    {/* Public route */}
    <Route
      path="/public-graph"
      element={
        <PublicLayout onShowHelp={() => setShowOnboarding(true)}>
          <CourseSimilarityPrecomputedGraph
            highlighted={[]}
            conflicted={[]}
            setHighlighted={() => {}}
            setConflicted={() => {}}
            currentSemester={CURRENT_SEMESTER}
            onSemesterChange={() => {}}
            onConflicted={() => {}}
            onHighlight={() => {}}
            isPublicMode={true}
            showOnboarding={showOnboarding}
            setShowOnboarding={setShowOnboarding}
          />
        </PublicLayout>
      }
    />

    {/* ✅ catch-all redirects to graph */}
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
  <TermsModal />
  <UserInfoPopup
    isOpen={showUserInfoPopup}
    onClose={handleUserInfoClose}
    onSave={handleUserInfoSave}
  />
</Router>
</SemesterProvider>
  );
}

export default App;