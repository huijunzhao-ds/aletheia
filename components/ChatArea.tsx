
import React, { useRef, useEffect, useState } from 'react';
import { Message, GeneratedFile } from '../types';
import { MessageItem } from './MessageItem';

interface ChatAreaProps {
  messages: Message[];
  onSendMessage: (content: string, files?: File[]) => void;
  isProcessing: boolean;
  currentStatus: string;
  onFileClick?: (file: GeneratedFile) => void;
  userPhoto?: string | null;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  onSendMessage,
  isProcessing,
  currentStatus,
  onFileClick,
  userPhoto
}) => {
  const [input, setInput] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isProcessing, currentStatus]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if ((input.trim() || selectedFiles.length > 0) && !isProcessing) {
      onSendMessage(input, selectedFiles);
      setInput('');
      setSelectedFiles([]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(prev => [...prev, ...Array.from(e.target.files!)]);
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleVoiceInput = () => {
    if (!('webkitSpeechRecognition' in window)) {
      alert("Speech recognition not supported in this browser.");
      return;
    }

    const SpeechRecognition = (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => setIsRecording(true);
    recognition.onend = () => setIsRecording(false);
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInput(prev => prev + (prev ? ' ' : '') + transcript);
    };

    recognition.start();
  };

  return (
    <div className="flex flex-col flex-1 h-full max-w-5xl mx-auto w-full relative">
      {/* Top fade/mask for smooth transition under absolute NavBar */}
      <div className="absolute top-0 left-0 right-0 h-20 bg-gradient-to-b from-zinc-950 to-transparent z-40 pointer-events-none" />

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 md:px-8 pt-24 pb-8 space-y-8 scroll-smooth"
      >
        {messages.map((message) => (
          <MessageItem key={message.id} message={message} onFileClick={onFileClick} userPhoto={userPhoto} />
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
        {selectedFiles.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2 animate-in slide-in-from-bottom-2">
            {selectedFiles.map((file, i) => (
              <div key={i} className="flex items-center gap-2 bg-zinc-800 border border-zinc-700 rounded-full px-3 py-1.5 text-xs text-zinc-300">
                <svg className="w-3.5 h-3.5 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
                <span className="truncate max-w-[150px]">{file.name}</span>
                <button onClick={() => removeFile(i)} className="text-zinc-500 hover:text-red-400">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="relative group">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            multiple
            className="hidden"
          />
          <div className="absolute left-3 flex items-center h-full z-10">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-2 text-zinc-500 hover:text-indigo-400 transition-colors"
              title="Attach files"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
            </button>
            <button
              onClick={handleVoiceInput}
              className={`p-2 transition-colors ${isRecording ? 'text-red-500 animate-pulse' : 'text-zinc-500 hover:text-indigo-400'}`}
              title="Voice input"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </button>
          </div>
          <form onSubmit={handleSubmit}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isRecording ? "Listening..." : "Ask Aletheia about papers, generate a lecture, or summarize an area..."}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-2xl py-4 pl-24 pr-16 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all shadow-xl text-zinc-100 placeholder-zinc-500"
              disabled={isProcessing}
            />
            <button
              type="submit"
              disabled={isProcessing || (!input.trim() && selectedFiles.length === 0)}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-xl bg-indigo-600 text-white disabled:bg-zinc-800 disabled:text-zinc-600 transition-all hover:bg-indigo-500"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
              </svg>
            </button>
          </form>
        </div>
        <p className="text-center text-[10px] text-zinc-600 mt-3 font-medium uppercase tracking-widest">
          Aletheia Research Agent • Local Service :8000
        </p>
      </div>
    </div>
  );
};
