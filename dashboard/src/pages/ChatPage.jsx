import React, { useState, useRef, useEffect } from 'react';
import { Mic, Paperclip, Send, Folder, Image as ImageIcon, FileText, Video } from 'lucide-react';

const agents = [
  { id: 'neo', name: 'Neo (Coordinator)', status: 'online' },
  { id: 'trinity', name: 'Trinity (Extractor)', status: 'online' },
  { id: 'smith', name: 'Agent Smith (Executor)', status: 'idle' },
  { id: 'morpheus', name: 'Morpheus (Architect)', status: 'online' },
  { id: 'critic', name: 'Dictatorial Critic', status: 'online' }
];

export default function ChatPage() {
  const [activeAgent, setActiveAgent] = useState('neo');
  const [message, setMessage] = useState('');
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const wsRef = useRef(null);
  const [messages, setMessages] = useState([
    { id: 1, sender: 'system', text: 'Awaiting your command, Sovereign Commander.' }
  ]);

  useEffect(() => {
    wsRef.current = new WebSocket('ws://127.0.0.1:8000/ws');
    
    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages(prev => [...prev, { id: Date.now(), sender: data.sender, text: data.text }]);
    };

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const handleSend = () => {
    if (!message.trim()) return;
    
    // Add command to local UI immediately
    setMessages(prev => [...prev, { id: Date.now(), sender: 'user', text: message }]);
    
    // Send to Python bridge
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ agent: activeAgent, text: message }));
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

  return (
    <div className="flex h-[calc(100vh-80px)] gap-6">
      {/* Agents Sidebar */}
      <div className="w-72 glass-panel p-4 flex flex-col gap-4">
        <h2 className="text-xl font-bold hologram-text mb-4 uppercase tracking-widest border-b border-[rgba(0,243,255,0.3)] pb-2">
          Comm Channels
        </h2>
        <div className="flex flex-col gap-2 overflow-y-auto">
          {agents.map(agent => (
            <button
              key={agent.id}
              onClick={() => setActiveAgent(agent.id)}
              className={`p-3 rounded flex items-center gap-3 transition-all duration-300 ${
                activeAgent === agent.id 
                  ? 'bg-[rgba(0,243,255,0.2)] border-l-4 border-[#00f3ff] shadow-[0_0_15px_rgba(0,243,255,0.3)]' 
                  : 'hover:bg-[rgba(0,243,255,0.1)] border-l-4 border-transparent'
              }`}
            >
              <div className={`w-3 h-3 rounded-full ${agent.status === 'online' ? 'bg-[#00f3ff] shadow-[0_0_8px_#00f3ff]' : 'bg-gray-500'}`} />
              <span className="text-sm font-medium tracking-wide">{agent.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 glass-panel flex flex-col relative">
        <div className="p-4 border-b border-[rgba(0,243,255,0.3)]">
          <h3 className="text-2xl font-bold hologram-text">
            {agents.find(a => a.id === activeAgent)?.name}
          </h3>
          <p className="text-xs text-[#00f3ff] opacity-70">Encrypted ZMQ Channel Active</p>
        </div>

        {/* Chat History */}
        <div className="flex-1 p-6 overflow-y-auto flex flex-col gap-4">
          {messages.map(msg => (
            <div key={msg.id} className={`${msg.sender === 'user' ? 'self-end bg-[rgba(0,243,255,0.15)] border border-[#00f3ff]' : 'self-start bg-[rgba(2,10,23,0.8)] border border-[rgba(0,243,255,0.2)]'} p-3 rounded-lg max-w-[70%]`}>
              <p className="text-sm">{msg.text}</p>
            </div>
          ))}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-[rgba(0,243,255,0.3)] relative">
          
          {/* Hidden File Inputs */}
          <input type="file" className="hidden" ref={fileInputRef} multiple />
          <input type="file" className="hidden" ref={folderInputRef} webkitdirectory="true" directory="true" multiple />

          {/* Attachment Menu */}
          {showAttachMenu && (
            <div className="absolute bottom-20 left-4 glass-panel p-2 flex flex-col gap-2 rounded-lg z-10 w-48 animate-fade-in">
              <button onClick={() => triggerFileInput('*/*')} className="flex items-center gap-3 p-2 hover:bg-[rgba(0,243,255,0.2)] rounded text-sm text-left">
                <FileText size={16} /> Files
              </button>
              <button onClick={() => triggerFileInput('*/*', true)} className="flex items-center gap-3 p-2 hover:bg-[rgba(0,243,255,0.2)] rounded text-sm text-left">
                <Folder size={16} /> Folders
              </button>
              <button onClick={() => triggerFileInput('image/*')} className="flex items-center gap-3 p-2 hover:bg-[rgba(0,243,255,0.2)] rounded text-sm text-left">
                <ImageIcon size={16} /> Images
              </button>
              <button onClick={() => triggerFileInput('video/*')} className="flex items-center gap-3 p-2 hover:bg-[rgba(0,243,255,0.2)] rounded text-sm text-left">
                <Video size={16} /> Videos
              </button>
            </div>
          )}

          <div className="flex gap-3 items-center bg-[rgba(2,10,23,0.8)] border border-[rgba(0,243,255,0.4)] rounded-full px-4 py-2 shadow-[0_0_15px_rgba(0,243,255,0.1)]">
            <button 
              onClick={() => setShowAttachMenu(!showAttachMenu)}
              className="text-[#00f3ff] hover:text-white transition-colors p-2"
              title="Attach File/Folder/Media"
            >
              <Paperclip size={20} />
            </button>
            
            <input 
              type="text" 
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Transmit command..."
              className="flex-1 bg-transparent border-none outline-none text-[#00f3ff] placeholder:text-[#00f3ff]/40 text-sm"
            />
            
            <button 
              className="text-[#00f3ff] hover:text-white transition-colors p-2 neon-btn rounded-full border-none"
              title="Voice Command"
            >
              <Mic size={20} />
            </button>
            
            <button 
              onClick={handleSend}
              className="bg-[rgba(0,243,255,0.1)] text-[#00f3ff] p-2 rounded-full hover:bg-[rgba(0,243,255,0.3)] transition-all shadow-[0_0_10px_rgba(0,243,255,0.2)]"
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
