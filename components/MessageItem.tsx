
import React from 'react';
import { Message, GeneratedFile } from '../types';

interface MessageItemProps {
  message: Message;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
  const isAssistant = message.role === 'assistant';

  // Helper to format citations as badges
  const renderContentWithCitations = (text: string) => {
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, i) => {
      if (part.match(/\[\d+\]/)) {
        return (
          <span 
            key={i} 
            className="inline-flex items-center justify-center px-1.5 py-0.5 mx-0.5 text-[10px] font-bold text-indigo-400 bg-indigo-400/10 border border-indigo-400/20 rounded cursor-pointer hover:bg-indigo-400/20 transition-colors"
          >
            {part.replace(/[\[\]]/g, '')}
          </span>
        );
      }
      return part;
    });
  };

  return (
    <div className={`flex flex-col ${isAssistant ? 'items-start' : 'items-end'} animate-in fade-in slide-in-from-bottom-4 duration-500`}>
      <div className={`flex items-start max-w-[85%] space-x-4 ${!isAssistant && 'flex-row-reverse space-x-reverse'}`}>
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow-lg ${
          isAssistant ? 'bg-indigo-600 text-white' : 'bg-zinc-700 text-zinc-200'
        }`}>
          {isAssistant ? (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          )}
        </div>

        <div className={`space-y-4 ${!isAssistant && 'text-right'}`}>
          <div className={`px-5 py-3 rounded-2xl shadow-sm leading-relaxed text-sm md:text-base border ${
            isAssistant 
              ? 'bg-zinc-900 border-zinc-800 text-zinc-200 rounded-tl-none' 
              : 'bg-indigo-600 border-indigo-500 text-white rounded-tr-none'
          }`}>
            {isAssistant ? renderContentWithCitations(message.content) : message.content}
          </div>

          {isAssistant && message.files && message.files.length > 0 && (
            <div className="grid grid-cols-1 gap-4 mt-4 w-full">
              {message.files.map((file, idx) => (
                <MediaRenderer key={idx} file={file} />
              ))}
            </div>
          )}
          
          <div className="text-[10px] text-zinc-600 font-medium uppercase tracking-tight px-1">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </div>
    </div>
  );
};

const MediaRenderer: React.FC<{ file: GeneratedFile }> = ({ file }) => {
  switch (file.type) {
    case 'mp3':
      return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 space-y-3 shadow-md animate-in zoom-in-95 duration-300">
          <div className="flex items-center space-x-3 mb-1">
            <div className="p-2 bg-indigo-500/20 rounded-lg">
              <svg className="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
            </div>
            <span className="text-xs font-bold text-zinc-300 uppercase tracking-wider">{file.name}</span>
          </div>
          <audio controls className="w-full h-10 accent-indigo-500">
            <source src={file.path} type="audio/mpeg" />
            Your browser does not support the audio element.
          </audio>
        </div>
      );
    case 'mp4':
      return (
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden shadow-md animate-in zoom-in-95 duration-300">
          <div className="p-4 border-b border-zinc-800 flex items-center space-x-3">
            <div className="p-2 bg-rose-500/20 rounded-lg">
              <svg className="w-5 h-5 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </div>
            <span className="text-xs font-bold text-zinc-300 uppercase tracking-wider">{file.name}</span>
          </div>
          <video controls className="w-full bg-black aspect-video">
            <source src={file.path} type="video/mp4" />
            Your browser does not support the video tag.
          </video>
        </div>
      );
    case 'pptx':
      return (
        <a 
          href={file.path} 
          download 
          className="group flex items-center p-4 bg-zinc-900 border border-zinc-800 hover:border-indigo-500 rounded-xl transition-all shadow-md animate-in zoom-in-95 duration-300"
        >
          <div className="p-3 bg-amber-500/20 group-hover:bg-amber-500/30 rounded-lg transition-colors mr-4">
            <svg className="w-6 h-6 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
            </svg>
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold text-zinc-200 group-hover:text-indigo-400 transition-colors">{file.name}</div>
            <div className="text-[10px] text-zinc-500 uppercase font-bold tracking-widest mt-0.5">PowerPoint Presentation • PPTX</div>
          </div>
          <div className="p-2 text-zinc-500 group-hover:text-indigo-400 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </div>
        </a>
      );
    default:
      return null;
  }
};
