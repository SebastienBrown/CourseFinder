import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, CheckCircle, X, Edit2, Save, Plus, Trash2 } from 'lucide-react';
import { supabase } from "./supabaseClient";

export default function TranscriptUpload() {
  const navigate = useNavigate();
  const [uploadedFile, setUploadedFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPopup, setShowPopup] = useState(false);
  const [transcriptData, setTranscriptData] = useState(null);
  const [editingSemester, setEditingSemester] = useState(null);
  const [editingCourses, setEditingCourses] = useState([]);
  const fileInputRef = useRef(null);
  const backendUrl=process.env.REACT_APP_BACKEND_URL; // Replace with your actual backend URL

  // Check if returning from edit mode
  React.useEffect(() => {
    const editingTranscriptData = localStorage.getItem('editingTranscriptData');
    const returnFromEdit = localStorage.getItem('returnFromTranscriptEdit');
    
    if (editingTranscriptData && returnFromEdit === 'true') {
      setTranscriptData(JSON.parse(editingTranscriptData));
      setShowPopup(true);
      
      // Clean up localStorage
      localStorage.removeItem('returnFromTranscriptEdit');
    }
  }, []);

  // Update transcript data when returning from edit
  React.useEffect(() => {
    const handleStorageChange = () => {
      const editingTranscriptData = localStorage.getItem('editingTranscriptData');
      const returnFromEdit = localStorage.getItem('returnFromTranscriptEdit');
      
      if (editingTranscriptData && returnFromEdit === 'true') {
        const updatedData = JSON.parse(editingTranscriptData);
        setTranscriptData(updatedData);
        
        // Clean up the return flag
        localStorage.removeItem('returnFromTranscriptEdit');
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const handleFileSelect = (file) => {
    if (file && (file.type.startsWith('image/') || file.type === 'application/pdf')) {
      setUploadedFile(file);
      
      // Create preview for image files
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
          setImagePreview(e.target.result);
        };
        reader.readAsDataURL(file);
      } else {
        // For PDF files, show a document icon
        setImagePreview(null);
      }
    } else {
      alert('Please upload an image file (PNG, JPG, JPEG) or PDF document.');
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileInputChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleSubmit = async () => {
    if (!uploadedFile) {
      alert('Please upload a transcript file first.');
      return;
    }
  
    console.log("[handleSubmit] File ready to upload:", uploadedFile);
    setIsSubmitting(true);
  
    try {
      const formData = new FormData();
      formData.append('transcript', uploadedFile);
  
      console.log("[handleSubmit] Sending request to backend:", `${backendUrl}/transcript_parsing`);
  
      const response = await fetch(`${backendUrl}/transcript_parsing`, {
        method: 'POST',
        body: formData,
      });
  
      console.log("[handleSubmit] Response received:", response.status);
  
      if (response.ok) {
        const data = await response.json();
        console.log("[handleSubmit] Parsed transcript data:", data);
  
        if (!data || Object.keys(data).length === 0) {
          console.warn("[handleSubmit] Backend returned empty or invalid data.");
          alert("No data was extracted from the transcript.");
          return;
        }
  
        setTranscriptData(data);
        setShowPopup(true);
        console.log("[handleSubmit] Popup should now be visible. showPopup =", true);
      } else {
        const errText = await response.text();
        console.error("[handleSubmit] Upload failed. Response text:", errText);
        throw new Error("Upload failed");
      }
    } catch (error) {
      console.error("[handleSubmit] Error uploading transcript:", error);
      alert("Failed to upload transcript. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleEditSemester = (semesterIndex) => {
    // Store the current transcript data and editing state in localStorage
    localStorage.setItem('editingTranscriptData', JSON.stringify(transcriptData));
    localStorage.setItem('editingSemesterIndex', semesterIndex.toString());
    localStorage.setItem('fromTranscriptUpload', 'true');
    
    // Set up the semester courses data for the intake page
    const semesterCourses = {};
    const selectedSemesters = [];
    
    transcriptData.semesters.forEach((semester, index) => {
      selectedSemesters.push(semester.name);
      semesterCourses[semester.name] = semester.courses || [];
    });
    
    localStorage.setItem('selectedSemesters', JSON.stringify(selectedSemesters));
    localStorage.setItem('semesterCourses', JSON.stringify(semesterCourses));
    
    // Navigate to the specific semester intake page
    navigate(`/intake/courses/${semesterIndex}`);
  };

  const handleSaveEdit = () => {
    if (!transcriptData?.semesters?.[editingSemester]) return;
    
    const updatedData = { ...transcriptData };
    updatedData.semesters[editingSemester].courses = [...editingCourses];
    setTranscriptData(updatedData);
    setEditingSemester(null);
    setEditingCourses([]);
  };

  const handleCancelEdit = () => {
    setEditingSemester(null);
    setEditingCourses([]);
  };

  const handleAddCourse = () => {
    setEditingCourses([...editingCourses, '']);
  };

  const handleRemoveCourse = (courseIndex) => {
    const newCourses = editingCourses.filter((_, index) => index !== courseIndex);
    setEditingCourses(newCourses);
  };

  const handleCourseChange = (courseIndex, value) => {
    const newCourses = [...editingCourses];
    newCourses[courseIndex] = value;
    setEditingCourses(newCourses);
  };

  const handleFinalSubmit = async () => {
      try {
        console.log('Starting final submit...');
        console.log('Backend URL:', backendUrl);
        console.log('Transcript data:', transcriptData);
    
        // Get user ID from Supabase (similar to your working code)
        const { data: { user }, error } = await supabase.auth.getUser();
        
        if (error) {
          console.error("Error fetching user:", error);
          throw new Error("Failed to get user information");
        }
    
        if (!user) {
          throw new Error("No user logged in");
        }
    
        // Build the payload similar to your working code
        const payload = {
          user_id: user.id,
          semester_courses: {}
        };
    
        // Convert transcriptData to the format your backend expects
        if (transcriptData?.semesters) {
          transcriptData.semesters.forEach(semester => {
            payload.semester_courses[semester.name] = semester.courses || [];
          });
        }
    
        console.log('Payload being sent:', payload);
    
        // Use the same endpoint as your working code
        const response = await fetch(`${backendUrl}/submit_courses`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });
    
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
    
        console.log('Successfully sent data to backend!');
        alert('Transcript validated and saved successfully!');
        
        // Clean up localStorage
        localStorage.removeItem('editingTranscriptData');
        localStorage.removeItem('editingSemesterIndex');
        localStorage.removeItem('fromTranscriptUpload');
        localStorage.removeItem('selectedSemesters');
        localStorage.removeItem('semesterCourses');
        
        setShowPopup(false);
        setTranscriptData(null);
        setUploadedFile(null);
        setImagePreview(null);

        navigate("/graph");
    } catch (error) {
      console.error('Error validating transcript:', error);
      alert('Failed to validate transcript. Please try again.');
    }
  };

 
  React.useEffect(() => {
    console.log("[useEffect] showPopup:", showPopup);
    console.log("[useEffect] transcriptData:", transcriptData);

    if (showPopup && transcriptData && !transcriptData.semesters) {
      const transformedData = {
        semesters: Object.entries(transcriptData).map(([semesterKey, semesterData]) => ({
          name: semesterKey,
          courses: semesterData.courses || []
        }))
      };
      console.log("[useEffect] Transformed transcriptData:", transformedData);
      setTranscriptData(transformedData);
    }
  }, [showPopup, transcriptData]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            Automatically Input Your Course History with Transcript
          </h1>
          <p className="text-sm text-gray-500 mt-2">
            Both official and unofficial transcripts of Amherst College are accepted.
          </p>
          <p className="text-sm text-gray-500">
            Only course codes are parsed, and no grade information will be collected.
          </p>
        </div>

        {/* Upload Area */}
        <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
          <div
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-all duration-200 ${
              isDragOver 
                ? 'border-blue-500 bg-blue-50' 
                : uploadedFile 
                ? 'border-green-500 bg-green-50' 
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            {uploadedFile ? (
              <div className="space-y-4">
                {imagePreview ? (
                  <div className="max-w-md mx-auto">
                    <img
                      src={imagePreview}
                      alt="Transcript preview"
                      className="w-full h-auto rounded-lg shadow-md border"
                    />
                  </div>
                ) : (
                  <div className="flex flex-col items-center">
                    <FileText className="w-16 h-16 text-blue-600 mb-2" />
                    <p className="text-sm text-gray-600">PDF Document</p>
                  </div>
                )}
                <div className="flex items-center justify-center space-x-2 text-green-600">
                  <CheckCircle className="w-5 h-5" />
                  <span className="font-medium">{uploadedFile.name}</span>
                </div>
                <p className="text-sm text-gray-500">
                  File size: {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <Upload className="w-16 h-16 text-gray-400 mx-auto" />
                <div>
                  <p className="text-xl font-medium text-gray-700 mb-2">
                    Drop your transcript here
                  </p>
                  <p className="text-gray-500">
                    or click the upload button below
                  </p>
                </div>
                <p className="text-sm text-gray-400">
                  Supports: PNG, JPG, JPEG, PDF
                </p>
              </div>
            )}
          </div>

          {/* Upload Button */}
          <div className="text-center mt-6">
            <button
              onClick={handleUploadClick}
              className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-8 rounded-lg transition-colors duration-200 shadow-md hover:shadow-lg"
            >
              <Upload className="w-5 h-5 inline-block mr-2" />
              Upload from Device
            </button>
            <p className="text-sm text-gray-500 mt-2">
              Choose from local storage or Google Drive
            </p>
          </div>

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,.pdf"
            onChange={handleFileInputChange}
            className="hidden"
          />
        </div>

        {/* Submit Button */}
        {uploadedFile && (
          <div className="text-center">
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className={`font-medium py-4 px-12 rounded-lg transition-all duration-200 shadow-lg ${
                isSubmitting
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-green-600 hover:bg-green-700 hover:shadow-xl'
              } text-white text-lg`}
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Processing...
                </span>
              ) : (
                'Submit Transcript for Processing'
              )}
            </button>
          </div>
        )}
      </div>

      {/* Review Popup */}
      {showPopup && (
        console.log("[TranscriptUpload] Component rendered. showPopup =", showPopup, "transcriptData =", transcriptData),
        console.log("[Popup Render] showPopup is X and semesters exist:", transcriptData.semesters),
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
            {/* Popup Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-2xl font-bold text-gray-800">Review Your Transcript</h2>
              <button
                onClick={() => setShowPopup(false)}
                className="text-gray-500 hover:text-gray-700 transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Popup Content */}
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <p className="text-gray-600 mb-6">Please review and edit your course information if needed:</p>
              
              <div className="space-y-6">
                {transcriptData?.semesters?.map((semester, semesterIndex) => (
                  <div key={semesterIndex} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-lg font-semibold text-gray-800">{semester.name}</h3>
                      {editingSemester === semesterIndex ? (
                        <div className="flex space-x-2">
                          <button
                            onClick={handleSaveEdit}
                            className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm flex items-center"
                          >
                            <Save className="w-4 h-4 mr-1" />
                            Save
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="bg-gray-500 hover:bg-gray-600 text-white px-3 py-1 rounded text-sm"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => handleEditSemester(semesterIndex)}
                          className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm flex items-center"
                        >
                          <Edit2 className="w-4 h-4 mr-1" />
                          Edit
                        </button>
                      )}
                    </div>
                    
                    {editingSemester === semesterIndex ? (
                      <div className="space-y-2">
                        {editingCourses.map((course, courseIndex) => (
                          <div key={courseIndex} className="flex items-center space-x-2">
                            <input
                              type="text"
                              value={course}
                              onChange={(e) => handleCourseChange(courseIndex, e.target.value)}
                              className="flex-1 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="Course code (e.g., COSC 111)"
                            />
                            <button
                              onClick={() => handleRemoveCourse(courseIndex)}
                              className="text-red-600 hover:text-red-700 p-1"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                        <button
                          onClick={handleAddCourse}
                          className="text-blue-600 hover:text-blue-700 text-sm flex items-center mt-2"
                        >
                          <Plus className="w-4 h-4 mr-1" />
                          Add Course
                        </button>
                      </div>
                    ) : (
                      <div className="grid grid-cols-2 gap-2">
                        {semester.courses?.map((course, courseIndex) => (
                          <div key={courseIndex} className="bg-gray-100 px-3 py-2 rounded text-sm font-medium">
                            {course}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Popup Footer */}
            <div className="border-t border-gray-200 p-6">
              <button
                onClick={handleFinalSubmit}
                className="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-3 px-6 rounded-lg transition-colors duration-200"
              >
                Submit Course History
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}