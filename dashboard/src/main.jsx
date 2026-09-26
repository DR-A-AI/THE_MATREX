import { StrictMode, Component } from 'react'
import { createRoot } from 'react-dom/client'
import { registerLicense } from '@syncfusion/ej2-base'
import { SovereignAuthProvider } from './auth/SovereignAuth'
import './index.css'
import App from './App.jsx'

// Register Syncfusion license if configured
const syncfusionLicense = import.meta.env.VITE_SYNCFUSION_LICENSE_KEY;
if (syncfusionLicense) {
    registerLicense(syncfusionLicense);
} else {
    console.warn('[Syncfusion] VITE_SYNCFUSION_LICENSE_KEY is missing — running without registered license.');
}

class RootErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[RootErrorBoundary] Unhandled UI error caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          width: '100%',
          backgroundColor: '#020a17',
          color: '#00f3ff',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'monospace',
          padding: '2rem',
          boxSizing: 'border-box'
        }}>
          <div style={{
            maxWidth: '600px',
            border: '1px solid rgba(0,243,255,0.4)',
            padding: '2rem',
            borderRadius: '12px',
            backgroundColor: 'rgba(2,10,23,0.9)',
            boxShadow: '0 0 25px rgba(0,243,255,0.2)',
            textAlign: 'center'
          }}>
            <h1 style={{ fontSize: '1.5rem', marginBottom: '1rem', letterSpacing: '0.1em' }}>
              ⚠️ SOVEREIGN MATRIX FAILSAFE
            </h1>
            <p style={{ fontSize: '0.875rem', opacity: 0.8, marginBottom: '1.5rem' }}>
              The UI encountered an unexpected exception: {this.state.error?.message || 'Unknown error'}
            </p>
            <button 
              onClick={() => window.location.reload()}
              style={{
                backgroundColor: 'rgba(0,243,255,0.15)',
                border: '1px solid #00f3ff',
                color: '#00f3ff',
                padding: '0.75rem 1.5rem',
                borderRadius: '8px',
                cursor: 'pointer',
                fontFamily: 'monospace',
                fontSize: '0.875rem',
                textTransform: 'uppercase'
              }}
            >
              Restart Matrix Terminal
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RootErrorBoundary>
      <SovereignAuthProvider>
        <App />
      </SovereignAuthProvider>
    </RootErrorBoundary>
  </StrictMode>,
)
