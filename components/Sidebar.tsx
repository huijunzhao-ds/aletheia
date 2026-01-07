
import React from 'react';
import { ResearchMode, Message } from '../types';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  currentMode: ResearchMode;
  onModeChange: (mode: ResearchMode) => void;
  messages: Message[];
}

export const Sidebar: React.FC<SidebarProps> = ({ 
  isOpen, 
  onToggle, 
  currentMode, 
  onModeChange,
  messages 
}) => {
  return (
    <aside 
      className={`transition-all duration-300 border-r border-zinc-800 bg-zinc-900 flex flex-col ${
        isOpen ? 'w-72' : 'w-0'
      } overflow-hidden`}
    >
      <div className="p-4 flex flex-col border-b border-zinc-800">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 bg-indigo-500 rounded-md rotate-3 shadow-lg shadow-indigo-500/20"></div>
            <h1 className="font-bold text-lg text-white truncate tracking-tight">Aletheia</h1>
          </div>
          <button 
            onClick={onToggle}
            className="p-1 hover:bg-zinc-800 rounded transition-colors"
          >
            <svg className="w-6 h-6 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
          </button>
        </div>
        <p className="text-[10px] text-zinc-500 leading-tight font-medium uppercase tracking-wider">
          Your personal multi-media AI research assistant
        </p>
      </div>

      <div className="p-4 space-y-4 flex-1">
        <div>
          <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider block mb-2">Research Mode</label>
          <div className="space-y-2">
            {[ResearchMode.QUICK, ResearchMode.DEEP].map((mode) => (
              <button
                key={mode}
                onClick={() => onModeChange(mode)}
                className={`w-full flex items-center px-3 py-2 rounded-lg text-sm transition-all ${
                  currentMode === mode 
                    ? 'bg-zinc-100 text-zinc-900 font-medium' 
                    : 'text-zinc-400 hover:bg-zinc-800'
                }`}
              >
                <div className={`w-2 h-2 rounded-full mr-3 ${currentMode === mode ? 'bg-indigo-500' : 'bg-zinc-700'}`} />
                {mode}
              </button>
            ))}
          </div>
        </div>

        <div className="pt-6">
          <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider block mb-2">Recent Research</label>
          <div className="space-y-1">
            {messages.filter(m => m.role === 'user').slice(-5).map((m) => (
              <div 
                key={m.id} 
                className="px-3 py-2 text-sm text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded cursor-pointer truncate"
              >
                {m.content}
              </div>
            ))}
            {messages.filter(m => m.role === 'user').length === 0 && (
              <div className="px-3 py-2 text-sm text-zinc-600 italic">No recent queries</div>
            )}
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-zinc-800 bg-zinc-900/50">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-bold text-white">RA</div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">Researcher User</p>
            <p className="text-xs text-zinc-500 truncate">Academic Plan</p>
          </div>
        </div>
      </div>
    </aside>
  );
};
