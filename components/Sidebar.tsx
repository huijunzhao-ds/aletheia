
import React from 'react';
import { Message } from '../types';

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  messages: Message[];
  userName?: string | null;
  userPhoto?: string | null;
  onNewConversation?: () => void;
  threads?: { id: string, title: string }[];
  onSelectThread?: (id: string) => void;
  documents?: { name: string, url: string }[];
  onSelectDocument?: (doc: { name: string, url: string }) => void;
  activeDocumentUrl?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onToggle,
  messages,
  userName,
  userPhoto,
  onNewConversation,
  threads = [],
  onSelectThread,
  documents = [],
  onSelectDocument,
  activeDocumentUrl
}) => {
  return (
    <aside
      className={`transition-all duration-300 border-r border-zinc-800 bg-zinc-900 flex flex-col ${isOpen ? 'w-72' : 'w-0'
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

      <div className="p-4">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-zinc-800 hover:bg-zinc-700 text-zinc-100 rounded-xl transition-all border border-zinc-700/50 group"
        >
          <svg className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span className="text-sm font-semibold">New Research</span>
        </button>
      </div>

      <div className="p-4 space-y-4 flex-1 overflow-y-auto">
        {documents.length > 0 && (
          <div className="pt-2">
            <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider block mb-2">Research Documents</label>
            <div className="space-y-1">
              {documents.map((doc, idx) => (
                <div
                  key={idx}
                  onClick={() => onSelectDocument?.(doc)}
                  className={`px-3 py-2 text-sm rounded cursor-pointer truncate flex items-center gap-2 group transition-colors ${activeDocumentUrl === doc.url
                      ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 border border-transparent'
                    }`}
                >
                  <svg className={`w-3.5 h-3.5 ${activeDocumentUrl === doc.url ? 'text-indigo-400' : 'text-red-500 opacity-70 group-hover:opacity-100'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  {doc.name}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="pt-6">
          <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider block mb-2">Recent Research</label>
          <div className="space-y-1">
            {threads.map((thread) => (
              <div
                key={thread.id}
                onClick={() => onSelectThread?.(thread.id)}
                className="px-3 py-2 text-sm text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded cursor-pointer truncate flex items-center gap-2 group"
              >
                <svg className="w-3.5 h-3.5 text-zinc-600 group-hover:text-indigo-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                {thread.title}
              </div>
            ))}
            {threads.length === 0 && (
              <div className="px-3 py-2 text-sm text-zinc-600 italic">No recent threads</div>
            )}
          </div>
        </div>
      </div>

      <div className="p-4 border-t border-zinc-800 bg-zinc-900/50">
        <div className="flex items-center space-x-3">
          {userPhoto ? (
            <img src={userPhoto} alt="User" className="w-8 h-8 rounded-full border border-zinc-700" />
          ) : (
            <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-xs font-bold text-white uppercase">
              {userName ? userName.substring(0, 2) : 'RA'}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{userName || 'Researcher User'}</p>
            <p className="text-xs text-zinc-500 truncate">Academic Plan</p>
          </div>
        </div>
      </div>
    </aside>
  );
};
