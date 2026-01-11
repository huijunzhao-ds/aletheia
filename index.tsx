import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { isFirebaseConfigured } from './firebaseConfig';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Could not find root element to mount to");
}

const root = ReactDOM.createRoot(rootElement);

if (!isFirebaseConfigured) {
  root.render(
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#09090b',
      color: '#f4f4f5',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      <div style={{ maxWidth: '500px', textAlign: 'center', padding: '2rem' }}>
        <h1 style={{ color: '#ef4444' }}>Configuration Link Missing</h1>
        <p>Aletheia's UI cannot start because Firebase environment variables are missing from the build.</p>
        <p style={{ color: '#a1a1aa', fontSize: '0.9rem' }}>
          Please ensure <code>VITE_FIREBASE_*</code> build arguments are passed during the Docker build process or set in your environment.
        </p>
      </div>
    </div>
  );
} else {
  try {
    root.render(
      <React.StrictMode>
        <App />
      </React.StrictMode>
    );
  } catch (err) {
    console.error("Critical Render Error:", err);
    root.render(
      <div style={{ background: '#09090b', color: '#ef4444', padding: '2rem', height: '100vh' }}>
        <h2>Critical Render Error</h2>
        <pre>{String(err)}</pre>
      </div>
    );
  }
}
