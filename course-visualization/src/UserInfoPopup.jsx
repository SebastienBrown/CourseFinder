import React, { useState } from 'react';
import { X, Save } from 'lucide-react';

export default function UserInfoPopup({ isOpen, onClose, onSave }) {
  const [classYear, setClassYear] = useState('');
  const [majors, setMajors] = useState([]);
  const [graduationMonth, setGraduationMonth] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Generate class years (current year + 4 to 2013, newer to older)
  const currentYear = new Date().getFullYear();
  const classYears = [];
  for (let year = currentYear + 4; year >= 2013; year--) {
    classYears.push(year);
  }

  // Amherst College department codes (four-character abbreviations)
  const availableMajors = [
    'Undecided', // Undecided
    'AAPI', // Asian American and Pacific Islander Studies
    'AMST', // American Studies
    'ANTH', // Anthropology
    'ARCH', // Architecture
    'ARHA', // Art and the History of Art
    'ASLC', // Asian Languages and Civilizations
    'ASTR', // Astronomy
    'BCBP', // Biochemistry and Biophysics
    'BIOL', // Biology
    'BLST', // Black Studies
    'CHEM', // Chemistry
    'CLAS', // Classics
    'COSC', // Computer Science
    'ECON', // Economics
    'EDST', // Education Studies
    'ENGL', // English
    'ENST', // Environmental Studies
    'EUST', // European Studies
    'FAMS', // Film and Media Studies
    'FREN', // French
    'FYSE', // First Year Seminar
    'GEOL', // Geology
    'GERM', // German
    'GREE', // Greek
    'HIST', // History
    'LATI', // Latin
    'LJST', // Law, Jurisprudence and Social Thought
    'LLAS', // Latin American and Latino Studies
    'MATH', // Mathematics
    'MUSI', // Music
    'NEUR', // Neuroscience
    'PHIL', // Philosophy
    'PHYS', // Physics
    'POSC', // Political Science
    'PSYC', // Psychology
    'RELI', // Religion
    'RUSS', // Russian
    'SOCI', // Sociology
    'SPAN', // Spanish
    'STAT', // Statistics
    'SWAG', // Sexuality, Women's and Gender Studies
    'THDA', // Theater and Dance
    'Interdisciplinary' // Interdisciplinary
  ];

  const handleSave = async () => {
    if (!classYear || majors.length === 0 || !graduationMonth) {
      alert('Please fill out all fields: class year, major(s), and graduation month.');
      return;
    }

    setIsLoading(true);
    try {
      await onSave({ classYear, majors, graduationMonth });
      onClose();
    } catch (error) {
      console.error('Error saving user info:', error);
      alert('Failed to save information. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    if (!isLoading) {
      onClose();
    }
  };

  const handleMajorChange = (majorCode) => {
    setMajors(prev => {
      if (prev.includes(majorCode)) {
        return prev.filter(m => m !== majorCode);
      } else {
        return [...prev, majorCode];
      }
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center px-4">
      <div className="bg-white max-w-md w-full rounded-xl shadow-xl p-6">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-[#3f1f69]">
            Tell us about yourself
          </h2>
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
            aria-label="Close"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="space-y-4">

          {/* Class Year Dropdown */}
          <div>
            <label htmlFor="class-year" className="block text-sm font-medium text-gray-700 mb-2">
              Class Year *
            </label>
            <select
              id="class-year"
              value={classYear}
              onChange={(e) => setClassYear(e.target.value)}
              disabled={isLoading}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#3f1f69] focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="">Select your class year</option>
              {classYears.map(year => (
                <option key={year} value={year}>
                  Class of {year}
                </option>
              ))}
            </select>
          </div>

          {/* Graduation Month */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              What month did/will you graduate? *
            </label>
            <div className="flex gap-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="graduationMonth"
                  value="May"
                  checked={graduationMonth === 'May'}
                  onChange={(e) => setGraduationMonth(e.target.value)}
                  disabled={isLoading}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">May</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="graduationMonth"
                  value="December"
                  checked={graduationMonth === 'December'}
                  onChange={(e) => setGraduationMonth(e.target.value)}
                  disabled={isLoading}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">December</span>
              </label>
            </div>
          </div>

          {/* Major Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Your (intended) Major(s) * (Select all that apply)
            </label>
            <div className="max-h-48 overflow-y-auto border border-gray-300 rounded-md p-3 space-y-2">
              {availableMajors.map(majorOption => (
                <label key={majorOption} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={majors.includes(majorOption)}
                    onChange={() => handleMajorChange(majorOption)}
                    disabled={isLoading}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">{majorOption}</span>
                </label>
              ))}
            </div>
            {majors.length > 0 && (
              <div className="mt-2 text-sm text-gray-600">
                Selected: {majors.join(', ')}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end mt-6">
          <button
            onClick={handleSave}
            disabled={isLoading || !classYear || majors.length === 0 || !graduationMonth}
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#3f1f69] text-white rounded-md font-medium hover:bg-[#311a4d] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
