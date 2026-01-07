
import React, { useRef, useEffect, useState } from 'react';
import { Message, GeneratedFile } from '../types';
import { MessageItem } from './MessageItem';

interface ChatAreaProps {
  messages: Message[];
  onSendMessage: (content: string) => void;
  isProcessing: boolean;
  currentStatus: string;
}

export const ChatArea: React.FC<ChatAreaProps> = ({ 
  messages, 
  onSendMessage, 
  isProcessing,
  currentStatus 
}) => {
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isProcessing, currentStatus]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isProcessing) {
      onSendMessage(input);
      setInput('');
    }
  };

  return (
    <div className="flex flex-col flex-1 h-full max-w-5xl mx-auto w-full">
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 md:px-8 py-8 space-y-8 scroll-smooth"
      >
        {messages.map((message) => (
          <MessageItem key={message.id} message={message} />
        ))}
        
        {isProcessing && (
          <div className="flex flex-col space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div className="flex items-start space-x-4">
              <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center animate-pulse">
                <svg className="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                </svg>
              </div>
              <div className="flex-1 space-y-3">
                <div className="h-4 bg-zinc-800 rounded w-1/4 animate-pulse"></div>
                <div className="h-4 bg-zinc-800 rounded w-3/4 animate-pulse"></div>
                <div className="flex items-center space-x-2 text-indigo-400 text-sm font-medium italic">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span>{currentStatus || 'Processing...'}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 md:p-8 bg-gradient-to-t from-zinc-950 via-zinc-950 to-transparent sticky bottom-0">
        <form 
          onSubmit={handleSubmit}
          className="relative group flex items-center"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Aletheia about papers, generate a lecture, or summarize an area..."
            className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl py-4 pl-6 pr-16 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all shadow-xl text-zinc-100 placeholder-zinc-500"
            disabled={isProcessing}
          />
          <button
            type="submit"
            disabled={isProcessing || !input.trim()}
            className="absolute right-3 p-2 rounded-xl bg-indigo-600 text-white disabled:bg-zinc-800 disabled:text-zinc-600 transition-all hover:bg-indigo-500"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
          </button>
        </form>
        <p className="text-center text-[10px] text-zinc-600 mt-3 font-medium uppercase tracking-widest">
          Aletheia Research Agent • Local Service :8000
        </p>
      </div>
    </div>
  );
};
