import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { registerLicense } from '@syncfusion/ej2-base'
import { ClerkProvider } from '@clerk/clerk-react'
import './index.css'
import App from './App.jsx'

// Register Syncfusion license
const syncfusionLicense = import.meta.env.VITE_SYNCFUSION_LICENSE_KEY;
if (syncfusionLicense) {
    registerLicense(syncfusionLicense);
} else {
    console.warn("⚠️ Syncfusion License Key is missing from .env!");
}

const clerkPubKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!clerkPubKey) {
    console.warn("⚠️ Clerk Publishable Key is missing from .env! Matrix UI will show an error screen.");
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {clerkPubKey ? (
      <ClerkProvider publishableKey={clerkPubKey}>
        <App />
      </ClerkProvider>
    ) : (
      <div style={{ backgroundColor: 'black', color: '#00f3ff', height: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: 'monospace' }}>
        <h1>[ SYSTEM HALT ]</h1>
        <p>VITE_CLERK_PUBLISHABLE_KEY is missing in J:\THE_MATRIX\dashboard\.env</p>
        <p>Please add your Clerk key to boot the UI.</p>
      </div>
    )}
  </StrictMode>,
)
