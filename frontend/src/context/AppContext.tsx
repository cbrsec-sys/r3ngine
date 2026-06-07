import React, { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

interface AppContextType {
  version: string;
  projectName: string;
  setVersion: (v: string) => void;
  setProjectName: (n: string) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

const VERSION_KEY = 'r3ngine_version';

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [version, setVersionState] = useState(() => localStorage.getItem(VERSION_KEY) ?? '');
  const [projectName, setProjectName] = useState('RENGINE');

  const setVersion = (v: string) => {
    localStorage.setItem(VERSION_KEY, v);
    setVersionState(v);
  };

  return (
    <AppContext.Provider value={{ version, projectName, setVersion, setProjectName }}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};
