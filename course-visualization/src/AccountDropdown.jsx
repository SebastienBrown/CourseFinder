import React, { useState, useRef, useEffect } from 'react';
import { User, ChevronDown } from 'lucide-react';

export default function AccountDropdown({ onSignOut, onShowUserInfo }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleUserInfoClick = () => {
    setIsOpen(false);
    onShowUserInfo();
  };

  const handleSignOutClick = () => {
    setIsOpen(false);
    onSignOut();
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-purple-400 text-white rounded-lg font-semibold shadow hover:bg-purple-500 transition-all duration-200 h-10"
      >
        <User className="w-5 h-5 text-purple-800" />
        <ChevronDown className="w-4 h-4" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
          <button
            onClick={handleUserInfoClick}
            className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
          >
            User Info
          </button>
          <button
            onClick={handleSignOutClick}
            className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
          >
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
}
