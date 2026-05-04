import axios from 'axios';
import { containsSqlInjection } from '../utils/securityUtils';

// Get CSRF token from cookies
const getCsrfToken = () => {
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
};

// Configure Axios defaults
axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';
axios.defaults.withCredentials = true;

// Add a request interceptor
axios.interceptors.request.use((config) => {
  // Automatic SQLi prevention for POST/PUT data
  if (config.data && typeof config.data === 'string') {
    if (containsSqlInjection(config.data)) {
      console.error('Potential SQL Injection detected in request data. Blocking request.');
      return Promise.reject(new Error('Security violation: Suspicious input detected.'));
    }
  } else if (config.data && typeof config.data === 'object' && !(config.data instanceof FormData)) {
    const dataStr = JSON.stringify(config.data);
    if (containsSqlInjection(dataStr)) {
      console.error('Potential SQL Injection detected in request data. Blocking request.');
      return Promise.reject(new Error('Security violation: Suspicious input detected.'));
    }
  }

  const token = getCsrfToken();
  if (token && config.headers) {
    config.headers['X-CSRFToken'] = token;
  }
  
  // Anti-clickjacking/MIME sniffing hint for modern browsers
  if (config.headers) {
    config.headers['X-Content-Type-Options'] = 'nosniff';
  }

  return config;
});

export default axios;
export { getCsrfToken };
