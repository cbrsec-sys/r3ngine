import React from 'react';
import './api/axiosConfig';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// @ts-ignore
import '@fontsource/orbitron';
// @ts-ignore
import '@fontsource/inter';
// @ts-ignore
import '@fontsource/syncopate';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
