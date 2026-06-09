import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, Lock, Shield, ArrowRight, CheckCircle } from 'lucide-react';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [step, setStep] = useState(0); // 0: input, 1: authenticating, 2: success
  const [statusMsg, setStatusMsg] = useState('');
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    if (!email) return;

    setStep(1);
    const statuses = [
      'BOOTING SOVEREIGN HANDSHAKE PROTOCOL...',
      'CONNECTING TO NEURAL BUS ROUTER [PORT 5555]...',
      'VERIFYING HMAC ZERO-TRUST CRITERIA...',
      'FETCHING ENCRYPTED SQLITE MEMORY BLOCK...',
      'INITIALIZING NEO (ANTIGRAVITY) AGENT CLIENT...',
      'IDENTITY AUTHENTICATED successfully.'
    ];

    let currentStatusIdx = 0;
    const interval = setInterval(() => {
      if (currentStatusIdx < statuses.length) {
        setStatusMsg(statuses[currentStatusIdx]);
        currentStatusIdx++;
      } else {
        clearInterval(interval);
        setStep(2);
        localStorage.setItem('commander_email', email);
        setTimeout(() => {
          // Force page refresh to update App.jsx state
          window.location.href = '/';
        }, 1200);
      }
    }, 600);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020a17] text-[#00f3ff] relative overflow-hidden font-mono px-4">
      {/* Background Cyberpunk Grid/Glows */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#031024_1px,transparent_1px),linear-gradient(to_bottom,#031024_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-30"></div>
      <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-[rgba(0,243,255,0.08)] blur-3xl"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full bg-[rgba(0,243,255,0.05)] blur-3xl"></div>

      <div className="w-full max-w-lg glass-panel p-8 border border-[rgba(0,243,255,0.3)] shadow-[0_0_35px_rgba(0,243,255,0.2)] bg-[rgba(2,10,23,0.85)] relative z-10">
        
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex p-3 rounded-full bg-[rgba(0,243,255,0.1)] border border-[#00f3ff] mb-4 shadow-[0_0_15px_rgba(0,243,255,0.3)]">
            <Shield size={36} className="animate-pulse" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-widest uppercase hologram-text mb-2">
            Sovereign Matrix
          </h1>
          <p className="text-xs text-[#00f3ff]/75 tracking-wider uppercase">
            Authentication Required &bull; Node: Morpheus-Shield
          </p>
        </div>

        {step === 0 && (
          <form onSubmit={handleLogin} className="flex flex-col gap-5">
            {/* Email Field */}
            <div className="flex flex-col gap-2">
              <label className="text-xs uppercase tracking-widest text-[#00f3ff]/70 font-bold">
                Commander Email Address
              </label>
              <div className="flex items-center gap-3 bg-[rgba(2,10,23,0.9)] border border-[rgba(0,243,255,0.4)] rounded-lg px-4 py-3 shadow-[inner_0_0_10px_rgba(0,243,255,0.1)] focus-within:border-[#00f3ff] transition-colors">
                <Mail size={18} className="text-[#00f3ff]/60" />
                <input
                  type="email"
                  required
                  placeholder="name@sovereign.ai"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="flex-1 bg-transparent border-none outline-none text-[#00f3ff] placeholder:text-[#00f3ff]/30 text-sm font-mono"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="flex flex-col gap-2">
              <label className="text-xs uppercase tracking-widest text-[#00f3ff]/70 font-bold">
                Secure Command Passkey
              </label>
              <div className="flex items-center gap-3 bg-[rgba(2,10,23,0.9)] border border-[rgba(0,243,255,0.4)] rounded-lg px-4 py-3 shadow-[inner_0_0_10px_rgba(0,243,255,0.1)] focus-within:border-[#00f3ff] transition-colors">
                <Lock size={18} className="text-[#00f3ff]/60" />
                <input
                  type="password"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="flex-1 bg-transparent border-none outline-none text-[#00f3ff] placeholder:text-[#00f3ff]/30 text-sm font-mono"
                />
              </div>
            </div>

            {/* Disclaimer */}
            <p className="text-[10px] text-[#00f3ff]/40 text-center leading-relaxed">
              This terminal enforces zero-trust identity checks. All connection handshakes are cryptographically signed using HMAC-SHA256. Unauthorised attempts will trigger a Failsafe lockdown.
            </p>

            {/* Login Button */}
            <button
              type="submit"
              className="mt-2 py-3.5 rounded-lg flex items-center justify-center gap-2 font-bold tracking-widest uppercase transition-all duration-300 bg-[rgba(0,243,255,0.15)] border border-[#00f3ff] hover:bg-[rgba(0,243,255,0.3)] shadow-[0_0_15px_rgba(0,243,255,0.2)] hover:shadow-[0_0_25px_rgba(0,243,255,0.5)] cursor-pointer"
            >
              Ignite Command Node <ArrowRight size={18} />
            </button>
          </form>
        )}

        {step === 1 && (
          <div className="flex flex-col items-center justify-center py-8 gap-6 min-h-[250px]">
            <div className="w-16 h-16 border-4 border-[#00f3ff]/20 border-t-[#00f3ff] rounded-full animate-spin shadow-[0_0_15px_rgba(0,243,255,0.3)]"></div>
            <div className="flex flex-col gap-2 items-center text-center">
              <span className="text-xs uppercase tracking-widest text-[#00f3ff]/60">Handshake Status</span>
              <p className="text-sm font-bold animate-pulse text-[#00f3ff]">{statusMsg}</p>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="flex flex-col items-center justify-center py-8 gap-6 min-h-[250px]">
            <CheckCircle size={64} className="text-[#00f3ff] drop-shadow-[0_0_10px_#00f3ff]" />
            <div className="flex flex-col gap-2 items-center text-center">
              <span className="text-xs uppercase tracking-widest text-[#00f3ff]/60">Handshake Complete</span>
              <p className="text-lg font-bold text-[#00f3ff] hologram-text">WELCOME BACK, COMMANDER</p>
              <p className="text-xs text-[#00f3ff]/50">Redirecting to communication core...</p>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
