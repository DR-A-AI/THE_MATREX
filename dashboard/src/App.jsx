import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { MessageSquare, Activity } from 'lucide-react';
import { UserButton, SignedIn, SignedOut, useUser } from '@clerk/clerk-react';
import ChatPage from './pages/ChatPage';
import MetricsPage from './pages/MetricsPage';
import LoginPage from './pages/LoginPage';

function TopNav() {
  const location = useLocation();
  const { user } = useUser();
  const email = user?.primaryEmailAddress?.emailAddress || 'commander@sovereign.ai';
  
  return (
    <nav className="h-20 glass-panel mb-6 flex items-center justify-between px-8 border-b border-[rgba(0,243,255,0.3)]">
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 rounded-full bg-[rgba(0,243,255,0.2)] border border-[#00f3ff] flex items-center justify-center shadow-[0_0_15px_rgba(0,243,255,0.4)]">
          <span className="text-[#00f3ff] font-bold text-xl">SM</span>
        </div>
        <div>
          <h1 className="text-xl font-bold hologram-text tracking-widest uppercase">Sovereign Matrix</h1>
          <p className="text-xs text-[#00f3ff] opacity-80">Commander: {email}</p>
        </div>
      </div>
      
      <div className="flex gap-4 items-center">
        <Link to="/" 
          className={`flex items-center gap-2 px-6 py-2 rounded-full transition-all duration-300 ${
            location.pathname === '/' 
            ? 'bg-[rgba(0,243,255,0.2)] border border-[#00f3ff] shadow-[0_0_15px_rgba(0,243,255,0.3)]' 
            : 'border border-transparent hover:border-[rgba(0,243,255,0.3)]'
          }`}>
          <MessageSquare size={18} />
          <span className="tracking-wide text-sm font-medium">COMMUNICATION</span>
        </Link>
        <Link to="/metrics" 
          className={`flex items-center gap-2 px-6 py-2 rounded-full transition-all duration-300 ${
            location.pathname === '/metrics' 
            ? 'bg-[rgba(0,243,255,0.2)] border border-[#00f3ff] shadow-[0_0_15px_rgba(0,243,255,0.3)]' 
            : 'border border-transparent hover:border-[rgba(0,243,255,0.3)]'
          }`}>
          <Activity size={18} />
          <span className="tracking-wide text-sm font-medium">TELEMETRY</span>
        </Link>
        <UserButton />
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <Router basename="/THE_MATREX/">
      <div className="min-h-screen p-4">
        <SignedIn>
          <TopNav />
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/metrics" element={<MetricsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </SignedIn>
        <SignedOut>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </SignedOut>
      </div>
    </Router>
  );
}
