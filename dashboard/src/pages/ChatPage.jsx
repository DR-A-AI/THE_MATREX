import { useState, useRef, useEffect } from 'react';
import { 
  Mic, Paperclip, Send, Folder, Image as ImageIcon, FileText, Video, 
  Terminal, Shield, Zap, Sparkles, Cpu, Radio, CheckCircle2 
} from 'lucide-react';
import { useAuth } from '../auth/SovereignAuth';

const agents = [
  { id: 'neo', name: 'Neo (Coordinator)', role: 'Execution & Synthesis', icon: Terminal, status: 'online' },
  { id: 'trinity', name: 'Trinity (Extractor)', role: 'Network & Key Sensors', icon: Zap, status: 'online' },
  { id: 'morpheus', name: 'Morpheus (Architect)', role: 'Defense & Node Topology', icon: Shield, status: 'online' },
  { id: 'smith', name: 'Agent Smith (Auditor)', role: 'Policy & Aegis Enforcement', icon: CheckCircle2, status: 'online' },
  { id: 'oracle', name: 'Oracle (Synthesizer)', role: 'Intuition & Deep Reasoning', icon: Sparkles, status: 'online' },
  { id: 'base', name: 'Base Node (Foundation)', role: 'ZMQ Infrastructure', icon: Cpu, status: 'online' }
];

const QUICK_COMMANDS = [
  { label: 'STATUS SCAN', cmd: 'Run a full system status audit on all agents and the neural bus.' },
  { label: 'OLLAMA TELEMETRY', cmd: 'Check local Ollama tensor health and latency.' },
  { label: 'GROQ LPU POOL', cmd: 'Verify active cloud accounts and Flex Processing state.' },
  { label: 'MEMORY AUDIT', cmd: 'Query local memory databases for active context.' },
];

const defaultInitMsg = [
  { 
    id: 1, 
    sender: 'system', 
    text: 'Sovereign Matrix Node initialized. Neural bus connected on port 5555. Dual-inference engine (Ollama + Groq Flex) ready. Awaiting directive, Commander.',
    time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
];

// Helper to parse safely and clean any corrupted historical messages
const getInitialMessages = () => {
  try {
    const saved = localStorage.getItem('matrixMessages');
    if (!saved) return defaultInitMsg;
    const parsed = JSON.parse(saved);
    if (Array.isArray(parsed)) {
      const sanitized = parsed
        .filter(m => m && typeof m === 'object')
        .map((m, idx) => ({
          id: m.id || Date.now() + idx,
          sender: m.sender || 'system',
          text: typeof m.text === 'string' ? m.text : (m.message ? String(m.message) : ''),
          time: m.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }))
        .filter(m => m.text.trim().length > 0);
      return sanitized.length > 0 ? sanitized : defaultInitMsg;
    }
    return defaultInitMsg;
  } catch {
    return defaultInitMsg;
  }
};

let globalMessages = getInitialMessages();
let globalStatuses = {};

export default function ChatPage() {
  const { getToken } = useAuth();
  const [activeAgent, setActiveAgent] = useState('neo');
  const [message, setMessage] = useState('');
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const [isWsConnected, setIsWsConnected] = useState(false);
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const [messages, setMessages] = useState(globalMessages);
  const [agentStatuses, setAgentStatuses] = useState(globalStatuses);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, agentStatuses]);

  useEffect(() => {
    let reconnectTimer = null;
    let isMounted = true;

    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = import.meta.env.VITE_WS_URL || `${protocol}//${window.location.host}/ws`;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = async () => {
        setIsWsConnected(true);
        try {
          const token = await getToken();
          ws.send(JSON.stringify({ clerk_token: token }));
        } catch (err) {
          console.error("Failed to authenticate WebSocket session", err);
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // 1. Ignore authentication control frames
          if (data.type === 'auth') {
            return;
          }

          // 2. Handle agent status updates
          if (data.type === 'status') {
            const sender = data.sender ? String(data.sender).toLowerCase() : 'system';
            const statusText = data.text !== undefined ? data.text : (data.message !== undefined ? data.message : '');
            setAgentStatuses(prev => {
              const next = { ...prev, [sender]: String(statusText) };
              globalStatuses = next;
              return next;
            });
            return;
          }

          // 3. Handle incoming chat messages
          const rawText = data.text !== undefined ? data.text : (data.message !== undefined ? data.message : '');
          const text = typeof rawText === 'string' ? rawText : (rawText ? JSON.stringify(rawText) : '');

          if (!text.trim()) {
            return;
          }

          const sender = data.sender || 'neo';
          const newMsg = { 
            id: Date.now(), 
            sender, 
            text,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          };

          setMessages(prev => {
            // UI-layer duplicate guard (StrictMode double-delivery / reconnect
            // replay): skip if the last message has identical sender+text.
            const last = prev[prev.length - 1];
            if (last && last.sender === sender && last.text === text) {
              return prev;
            }
            const next = [...prev, newMsg];
            globalMessages = next;
            try {
              localStorage.setItem('matrixMessages', JSON.stringify(next));
            } catch {
              // Ignore localStorage quota
            }
            return next;
          });

          setAgentStatuses(prev => {
            const next = { ...prev, [sender.toLowerCase()]: '' };
            globalStatuses = next;
            return next;
          });
        } catch (err) {
          console.error('[WebSocket] Error processing message:', err);
        }
      };

      ws.onclose = () => {
        setIsWsConnected(false);
        if (isMounted) {
          reconnectTimer = setTimeout(connect, 3000);
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket connection error:', err);
        ws.close();
      };
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (wsRef.current) wsRef.current.close();
    };
  }, [getToken]);

  const handleSend = (textToSend) => {
    const content = (typeof textToSend === 'string' ? textToSend : message).trim();
    if (!content) return;
    
    const userMsg = { 
      id: Date.now(), 
      sender: 'user', 
      text: content,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => {
      const next = [...prev, userMsg];
      globalMessages = next;
      try {
        localStorage.setItem('matrixMessages', JSON.stringify(next));
      } catch {
        // quota
      }
      return next;
    });
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ agent: activeAgent, text: content }));
    }
    
    setMessage('');
  };

  const triggerFileInput = (accept, isFolder = false) => {
    if (isFolder) {
      folderInputRef.current.click();
    } else {
      fileInputRef.current.accept = accept;
      fileInputRef.current.click();
    }
    setShowAttachMenu(false);
  };

  const activeAgentData = agents.find(a => a.id === activeAgent) || agents[0];

  return (
    <div className="flex h-[calc(100vh-100px)] gap-6 font-mono text-[#00f3ff]">
      {/* Agents Sidebar */}
      <div className="w-80 glass-panel p-4 flex flex-col gap-4 border border-[rgba(0,243,255,0.25)] shadow-[0_0_20px_rgba(0,243,255,0.08)]">
        <div className="flex items-center justify-between border-b border-[rgba(0,243,255,0.3)] pb-3">
          <div className="flex items-center gap-2">
            <Radio size={16} className={`animate-pulse ${isWsConnected ? 'text-[#00ff88]' : 'text-amber-400'}`} />
            <h2 className="text-sm font-bold uppercase tracking-widest hologram-text">
              Neural Agents
            </h2>
          </div>
          <span className={`text-[10px] px-2 py-0.5 rounded-full border ${isWsConnected ? 'border-[#00ff88]/40 bg-[#00ff88]/10 text-[#00ff88]' : 'border-amber-400/40 bg-amber-400/10 text-amber-400'}`}>
            {isWsConnected ? 'BUS LIVE' : 'RECONNECTING'}
          </span>
        </div>

        <div className="flex flex-col gap-2 overflow-y-auto pr-1">
          {agents.map(agent => {
            const AgentIcon = agent.icon;
            const statusText = agentStatuses[agent.id] || agentStatuses[agent.name.toLowerCase()];
            const isSelected = activeAgent === agent.id;

            return (
              <div key={agent.id} className="flex flex-col gap-1">
                <button
                  onClick={() => setActiveAgent(agent.id)}
                  className={`p-3 rounded-lg flex items-center justify-between transition-all duration-300 text-left border ${
                    isSelected 
                      ? 'bg-[rgba(0,243,255,0.18)] border-[#00f3ff] shadow-[0_0_15px_rgba(0,243,255,0.25)] translate-x-1' 
                      : 'hover:bg-[rgba(0,243,255,0.06)] border-transparent hover:border-[rgba(0,243,255,0.2)]'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-md ${isSelected ? 'bg-[#00f3ff]/20 text-[#00f3ff]' : 'bg-black/40 text-[#00f3ff]/60'}`}>
                      <AgentIcon size={18} />
                    </div>
                    <div>
                      <div className="text-sm font-bold tracking-wide">{agent.name}</div>
                      <div className="text-[10px] text-[#00f3ff]/60">{agent.role}</div>
                    </div>
                  </div>
                  <div className={`w-2 h-2 rounded-full ${isSelected ? 'bg-[#00ff88] shadow-[0_0_8px_#00ff88]' : 'bg-[#00f3ff]/40'}`} />
                </button>
                {statusText && (
                  <div className="ml-4 mr-2 p-2 rounded bg-[rgba(2,10,23,0.85)] border border-[#00f3ff]/40 text-xs text-[#00f3ff] animate-pulse">
                    &gt; {statusText}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Tactical Chat Area */}
      <div className="flex-1 glass-panel flex flex-col relative border border-[rgba(0,243,255,0.25)] shadow-[0_0_25px_rgba(0,243,255,0.1)]">
        {/* Chat Header */}
        <div className="p-4 border-b border-[rgba(0,243,255,0.3)] flex justify-between items-center bg-[rgba(2,10,23,0.7)]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#00f3ff]/15 border border-[#00f3ff]/50">
              <activeAgentData.icon size={22} className="text-[#00f3ff] animate-pulse" />
            </div>
            <div>
              <h3 className="text-lg font-bold hologram-text tracking-wider uppercase">
                {activeAgentData.name}
              </h3>
              <p className="text-xs text-[#00f3ff]/70">{activeAgentData.role} &bull; Channel: {activeAgent.toUpperCase()}_ZMQ</p>
            </div>
          </div>
          <button 
            onClick={() => {
              const initMsg = [{ 
                id: Date.now(), 
                sender: 'system', 
                text: 'Conversation cleared. Awaiting new directive.',
                time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
              }];
              setMessages(initMsg);
              globalMessages = initMsg;
              localStorage.setItem('matrixMessages', JSON.stringify(initMsg));
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ agent: activeAgent, text: '/clear' }));
              }
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#00f3ff]/40 text-[#00f3ff] hover:bg-[#00f3ff]/20 text-xs transition-all tracking-wider uppercase"
          >
            Clear Log
          </button>
        </div>

        {/* Message Feed */}
        <div className="flex-1 p-6 overflow-y-auto flex flex-col gap-4">
          {messages.map(msg => {
            const isUser = msg.sender === 'user';
            const safeText = typeof msg?.text === 'string' ? msg.text : '';
            const isImage = safeText.includes('![') && safeText.includes('](');

            return (
              <div 
                key={msg.id} 
                className={`flex flex-col gap-1 max-w-[75%] ${isUser ? 'self-end items-end' : 'self-start items-start'}`}
              >
                <div className="flex items-center gap-2 text-[10px] text-[#00f3ff]/50 tracking-wider">
                  <span className="font-bold uppercase text-[#00f3ff]/80">
                    {isUser ? 'COMMANDER' : (msg.sender || 'AGENT').toUpperCase()}
                  </span>
                  <span>&bull;</span>
                  <span>{msg.time || ''}</span>
                </div>

                <div 
                  className={`p-3.5 rounded-xl border leading-relaxed ${
                    isUser 
                      ? 'bg-[rgba(0,243,255,0.18)] border-[#00f3ff] text-white shadow-[0_0_15px_rgba(0,243,255,0.15)]' 
                      : 'bg-[rgba(2,10,23,0.85)] border-[rgba(0,243,255,0.3)] text-[#00f3ff] shadow-[0_0_15px_rgba(2,10,23,0.6)]'
                  }`}
                >
                  {isImage ? (
                    <div>
                      <p className="text-sm">{safeText.split('![')[0]}</p>
                      <img 
                        src={safeText.split('](')[1]?.split(')')[0] || ''} 
                        alt="Vision Capture" 
                        className="max-w-full rounded-lg mt-2 border border-[#00f3ff]/30 shadow-[0_0_15px_rgba(0,243,255,0.2)]" 
                      />
                      <p className="text-sm mt-2">{safeText.split(')')[1] || ''}</p>
                    </div>
                  ) : (
                    <p className="text-sm whitespace-pre-wrap">{safeText}</p>
                  )}
                </div>
              </div>
            );
          })}

          {/* Working Status Pulse */}
          {agentStatuses[activeAgent.toLowerCase()] && (
            <div className="self-start w-full bg-[rgba(2,10,23,0.9)] border border-[#00f3ff]/60 rounded-xl p-4 mt-2 animate-pulse shadow-[0_0_20px_rgba(0,243,255,0.2)]">
              <div className="flex items-center gap-3 mb-1">
                <div className="w-2 h-2 rounded-full bg-[#00f3ff] shadow-[0_0_8px_#00f3ff]" />
                <span className="text-[#00f3ff] font-bold text-xs tracking-widest uppercase">
                  {activeAgent.toUpperCase()} PROCESSING TENSOR DIRECTIVE...
                </span>
              </div>
              <p className="text-[#00f3ff]/90 text-sm font-mono pl-5">&gt; {agentStatuses[activeAgent.toLowerCase()]}</p>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Command Chips */}
        <div className="px-4 py-2 border-t border-[rgba(0,243,255,0.15)] bg-[rgba(2,10,23,0.4)] flex gap-2 overflow-x-auto text-xs">
          {QUICK_COMMANDS.map((chip, i) => (
            <button
              key={i}
              onClick={() => handleSend(chip.cmd)}
              className="px-3 py-1 rounded-full border border-[#00f3ff]/30 bg-[#00f3ff]/5 hover:bg-[#00f3ff]/20 text-[#00f3ff] transition-all whitespace-nowrap text-[11px] tracking-wider uppercase"
            >
              &gt; {chip.label}
            </button>
          ))}
        </div>

        {/* Input Dock */}
        <div className="p-4 border-t border-[rgba(0,243,255,0.3)] relative bg-[rgba(2,10,23,0.8)]">
          {/* Hidden File Inputs */}
          <input type="file" className="hidden" ref={fileInputRef} multiple />
          <input type="file" className="hidden" ref={folderInputRef} webkitdirectory="true" directory="true" multiple />

          {/* Attachment Menu */}
          {showAttachMenu && (
            <div className="absolute bottom-20 left-4 glass-panel p-2 flex flex-col gap-1.5 rounded-xl z-10 w-48 border border-[#00f3ff]/50 shadow-[0_0_20px_rgba(0,243,255,0.25)]">
              <button onClick={() => triggerFileInput('*/*')} className="flex items-center gap-3 p-2 hover:bg-[#00f3ff]/20 rounded-lg text-xs text-left">
                <FileText size={15} /> Attach Files
              </button>
              <button onClick={() => triggerFileInput('*/*', true)} className="flex items-center gap-3 p-2 hover:bg-[#00f3ff]/20 rounded-lg text-xs text-left">
                <Folder size={15} /> Scan Folder
              </button>
              <button onClick={() => triggerFileInput('image/*')} className="flex items-center gap-3 p-2 hover:bg-[#00f3ff]/20 rounded-lg text-xs text-left">
                <ImageIcon size={15} /> Visual OCR
              </button>
              <button onClick={() => triggerFileInput('video/*')} className="flex items-center gap-3 p-2 hover:bg-[#00f3ff]/20 rounded-lg text-xs text-left">
                <Video size={15} /> Media Feed
              </button>
            </div>
          )}

          <div className="flex gap-3 items-center bg-[rgba(2,10,23,0.9)] border border-[rgba(0,243,255,0.4)] rounded-2xl px-4 py-2.5 shadow-[0_0_20px_rgba(0,243,255,0.12)] focus-within:border-[#00f3ff] transition-all">
            <button 
              onClick={() => setShowAttachMenu(!showAttachMenu)}
              className="text-[#00f3ff]/80 hover:text-white transition-colors p-1.5"
              title="Attach File/Media"
            >
              <Paperclip size={18} />
            </button>
            
            <input 
              type="text" 
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder={`Transmit instruction to ${activeAgentData.name}...`}
              className="flex-1 bg-transparent border-none outline-none text-[#00f3ff] placeholder:text-[#00f3ff]/40 text-sm font-mono"
            />
            
            <button 
              className="text-[#00f3ff]/80 hover:text-white transition-colors p-1.5"
              title="Voice Protocol"
            >
              <Mic size={18} />
            </button>
            
            <button 
              onClick={() => handleSend()}
              disabled={!message.trim()}
              className={`p-2 rounded-xl transition-all shadow-[0_0_12px_rgba(0,243,255,0.2)] ${
                message.trim() 
                  ? 'bg-[#00f3ff] text-black hover:bg-white cursor-pointer' 
                  : 'bg-[rgba(0,243,255,0.1)] text-[#00f3ff]/40 cursor-not-allowed'
              }`}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
