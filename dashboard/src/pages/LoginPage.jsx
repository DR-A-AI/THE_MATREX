import React from 'react';
import { SignIn } from '@clerk/clerk-react';
import { Shield } from 'lucide-react';

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#020a17] text-[#00f3ff] relative overflow-hidden font-mono px-4">
      {/* Background Cyberpunk Grid/Glows */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#031024_1px,transparent_1px),linear-gradient(to_bottom,#031024_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-30"></div>
      <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-[rgba(0,243,255,0.08)] blur-3xl"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 rounded-full bg-[rgba(0,243,255,0.05)] blur-3xl"></div>

      <div className="w-full max-w-lg glass-panel p-8 border border-[rgba(0,243,255,0.3)] shadow-[0_0_35px_rgba(0,243,255,0.2)] bg-[rgba(2,10,23,0.85)] relative z-10 flex flex-col items-center">
        
        {/* Header */}
        <div className="text-center mb-8 w-full">
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

        <div className="w-full">
          <SignIn 
            routing="hash" 
            appearance={{
              variables: {
                colorPrimary: '#00f3ff',
                colorBackground: 'transparent',
                colorText: '#00f3ff',
                colorInputBackground: 'rgba(2,10,23,0.9)',
                colorInputText: '#00f3ff',
              },
              elements: {
                card: "bg-transparent shadow-none w-full p-0 flex flex-col gap-4",
                headerTitle: "hidden",
                headerSubtitle: "hidden",
                logoBox: "hidden",
                socialButtonsBlockButton: "border border-[#00f3ff]/40 text-[#00f3ff] hover:bg-[#00f3ff]/10 bg-transparent rounded-lg py-3",
                formButtonPrimary: "bg-[rgba(0,243,255,0.15)] border border-[#00f3ff] hover:bg-[rgba(0,243,255,0.3)] text-[#00f3ff] shadow-[0_0_15px_rgba(0,243,255,0.2)] transition-all uppercase tracking-widest font-bold py-3.5 rounded-lg mt-2",
                footer: "hidden",
                formFieldLabel: "text-xs uppercase tracking-widest text-[#00f3ff]/70 font-bold mb-2",
                formFieldInput: "bg-[rgba(2,10,23,0.9)] border border-[rgba(0,243,255,0.4)] text-[#00f3ff] shadow-[inner_0_0_10px_rgba(0,243,255,0.1)] focus:border-[#00f3ff] font-mono px-4 py-3 rounded-lg outline-none",
                dividerLine: "bg-[#00f3ff]/30",
                dividerText: "text-[#00f3ff]/50 text-xs font-mono tracking-widest",
                formFieldInputShowPasswordButton: "text-[#00f3ff]/60 hover:text-[#00f3ff]",
                identityPreviewText: "text-[#00f3ff]",
                identityPreviewEditButtonIcon: "text-[#00f3ff]",
              }
            }} 
          />
        </div>

        {/* Disclaimer */}
        <p className="text-[10px] text-[#00f3ff]/40 text-center leading-relaxed mt-8">
          This terminal enforces zero-trust identity checks. All connection handshakes are cryptographically secured. Unauthorised attempts will trigger a Failsafe lockdown.
        </p>

      </div>
    </div>
  );
}
