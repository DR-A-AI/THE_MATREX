import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { registerLicense } from '@syncfusion/ej2-base'
import './index.css'
import App from './App.jsx'

// Register Syncfusion license
const syncfusionLicense = import.meta.env.VITE_SYNCFUSION_LICENSE_KEY;
if (syncfusionLicense) {
    registerLicense(syncfusionLicense);
} else {
    console.warn("⚠️ Syncfusion License Key is missing from .env!");
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
