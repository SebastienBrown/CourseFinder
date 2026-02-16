// SemesterContext.jsx
import React, { createContext, useState, useContext } from 'react';
import { AVAILABLE_SEMESTERS, CURRENT_SEMESTER } from './config';

const SemesterContext = createContext();

export const SemesterProvider = ({ children }) => {
  const [selectedSemester, setSelectedSemester] = useState(CURRENT_SEMESTER);
  return (
    <SemesterContext.Provider value={{ selectedSemester, setSelectedSemester }}>
      {children}
    </SemesterContext.Provider>
  );
};

export const useSemester = () => useContext(SemesterContext);
