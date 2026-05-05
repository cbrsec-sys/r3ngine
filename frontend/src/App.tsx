import React from 'react';
import { RouterProvider } from '@tanstack/react-router';
import { AppProvider } from './context/AppContext';
import { router } from './router';

function App() {
  return (
    <AppProvider>
      <RouterProvider router={router} />
    </AppProvider>
  );
}

export default App;
