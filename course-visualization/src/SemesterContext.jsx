// SemesterContext.jsx
import React, { createContext, useState, useContext } from 'react';
import { AVAILABLE_SEMESTERS } from './config';

const SemesterContext = createContext();

export const SemesterProvider = ({ children }) => {
  const [selectedSemester, setSelectedSemester] = useState("2324S");
  return (
    <SemesterContext.Provider value={{ selectedSemester, setSelectedSemester }}>
      {children}
    </SemesterContext.Provider>
  );
};

export const useSemester = () => useContext(SemesterContext);
