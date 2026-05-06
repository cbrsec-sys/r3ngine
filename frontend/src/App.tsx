import React from 'react';
import { RouterProvider } from '@tanstack/react-router';
import { AppProvider } from './context/AppContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { router } from './router';

function InnerApp() {
  const auth = useAuth();
  return <RouterProvider router={router} context={{ auth }} />;
}

function App() {
  return (
    <AuthProvider>
      <AppProvider>
        <InnerApp />
      </AppProvider>
    </AuthProvider>
  );
}

export default App;
