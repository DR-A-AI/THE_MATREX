import { HashRouter as Router, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { MessageSquare, Activity } from 'lucide-react';
import { UserButton, SignedIn, SignedOut, useUser } from './auth/SovereignAuth';
import ChatPage from './pages/ChatPage';
import MetricsPage from './pages/MetricsPage';
import LoginPage from './pages/LoginPage';

function TopNav() {
  const location = useLocation();
  const { user } = useUser();
  const email = user?.primaryEmailAddress?.emailAddress || 'commander@sovereign.ai';
  
  return (
    <nav className="h-20 glass-panel mb-6 flex items-center justify-between px-8 border-b border-[rgba(0,243,255,0.3)] shadow-[0_0_20px_rgba(0,243,255,0.08)]">
      <div className="flex items-center gap-4">
        <div className="w-11 h-11 rounded-xl bg-[rgba(0,243,255,0.15)] border border-[#00f3ff] flex items-center justify-center shadow-[0_0_15px_rgba(0,243,255,0.3)]">
          <span className="text-[#00f3ff] font-bold text-xl tracking-tighter">SM</span>
        </div>
        <div>
          <h1 className="text-xl font-extrabold hologram-text tracking-widest uppercase">Sovereign Matrix</h1>
          <p className="text-[11px] text-[#00f3ff]/70 font-mono tracking-wide">Commander: {email}</p>
        </div>
      </div>

      {/* Central Node Telemetry Badge */}
      <div className="hidden lg:flex items-center gap-4 px-4 py-1.5 rounded-full bg-[rgba(2,10,23,0.85)] border border-[rgba(0,243,255,0.25)] font-mono text-[11px] text-[#00f3ff]">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#00ff88] shadow-[0_0_8px_#00ff88] animate-pulse" />
          <span className="tracking-wider">ZMQ: 5555</span>
        </div>
        <span className="text-[#00f3ff]/30">|</span>
        <span className="text-[#00f3ff]/80">OLLAMA 11434</span>
        <span className="text-[#00f3ff]/30">|</span>
        <span className="text-[#00ff88]">GROQ FLEX POOL</span>
      </div>
      
      <div className="flex gap-4 items-center font-mono">
        <Link to="/" 
          className={`flex items-center gap-2 px-5 py-2 rounded-xl transition-all duration-300 text-xs font-bold tracking-wider ${
            location.pathname === '/' 
            ? 'bg-[rgba(0,243,255,0.2)] border border-[#00f3ff] shadow-[0_0_15px_rgba(0,243,255,0.3)] text-white' 
            : 'border border-transparent hover:border-[rgba(0,243,255,0.3)] text-[#00f3ff]/80 hover:text-[#00f3ff]'
          }`}>
          <MessageSquare size={16} />
          <span>COMMUNICATION</span>
        </Link>
        <Link to="/metrics" 
          className={`flex items-center gap-2 px-5 py-2 rounded-xl transition-all duration-300 text-xs font-bold tracking-wider ${
            location.pathname === '/metrics' 
            ? 'bg-[rgba(0,243,255,0.2)] border border-[#00f3ff] shadow-[0_0_15px_rgba(0,243,255,0.3)] text-white' 
            : 'border border-transparent hover:border-[rgba(0,243,255,0.3)] text-[#00f3ff]/80 hover:text-[#00f3ff]'
          }`}>
          <Activity size={16} />
          <span>TELEMETRY</span>
        </Link>
        <UserButton />
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <Router>
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
