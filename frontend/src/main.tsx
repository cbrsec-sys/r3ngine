import React from 'react';
import './api/axiosConfig';
import ReactDOM from 'react-dom';
import * as ReactDOMClient from 'react-dom/client';
import * as MaterialUI from '@mui/material';
import * as MaterialUIStyles from '@mui/material/styles';
import * as MaterialUIIcons from '@mui/icons-material';
import * as LucideReact from 'lucide-react';
import cytoscape from 'cytoscape';
import App from './App';
import './index.css';

// Bind React and dependencies to window for dynamic plugins loading
(window as any).React = React;
(window as any).ReactDOM = { ...ReactDOM, ...ReactDOMClient };
(window as any).MaterialUI = MaterialUI;
(window as any).MaterialUIStyles = MaterialUIStyles;
(window as any).MaterialUIIcons = MaterialUIIcons;
(window as any).LucideReact = LucideReact;
(window as any).Cytoscape = cytoscape;



// @ts-ignore
import '@fontsource/orbitron';
// @ts-ignore
import '@fontsource/inter';
// @ts-ignore
import '@fontsource/bangers';

ReactDOMClient.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
