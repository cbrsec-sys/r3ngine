import React, { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

interface AppContextType {
  version: string;
  projectName: string;
  setVersion: (v: string) => void;
  setProjectName: (n: string) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [version, setVersion] = useState('');
  const [projectName, setProjectName] = useState('RENGINE');

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
