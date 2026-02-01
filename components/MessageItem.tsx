import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Message, GeneratedFile } from '../types';

interface MessageItemProps {
  message: Message;
  onFileClick?: (file: GeneratedFile) => void;
  userPhoto?: string | null;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message, onFileClick, userPhoto }) => {
  const isAssistant = message.role === 'assistant';
  const isSystem = message.role === 'system';
  const isTool = message.role === 'tool';
  const isUser = message.role === 'user';

  if (isSystem || isTool) {
    return (
      <div className="flex items-start w-full mb-6 px-4 animate-in fade-in slide-in-from-left-2 duration-300">
        <div className="mr-3 mt-1 flex-shrink-0">
          <div className="w-6 h-6 rounded-md bg-zinc-800/50 flex items-center justify-center border border-zinc-700/50">
            {isSystem ? (
              <svg className="w-3.5 h-3.5 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            ) : (
              <svg className="w-3.5 h-3.5 text-zinc-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            )}
          </div>
        </div>
        <div className="flex-1 pb-2 border-l-2 border-zinc-800/30 pl-4">
          <div className="text-[10px] uppercase tracking-widest text-zinc-600 font-bold mb-1">
            {isSystem ? 'System Logic' : 'Agent Action'}
          </div>
          <div className="text-sm text-zinc-500 leading-relaxed font-mono opacity-80 line-clamp-6 hover:line-clamp-none transition-all cursor-pointer">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col ${isAssistant ? 'items-start' : 'items-end'} animate-in fade-in slide-in-from-bottom-4 duration-500 w-full mb-6`}>
      <div className={`flex items-start max-w-[90%] md:max-w-[85%] space-x-4 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center shadow-lg transition-transform hover:scale-110 overflow-hidden ${isAssistant ? 'bg-indigo-600 text-white' : 'bg-zinc-700 text-zinc-200'
          }`}>
          {isAssistant ? (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
          ) : (
            userPhoto ? (
              <img src={userPhoto} alt="User" className="w-full h-full object-cover" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            )
          )}
        </div>

        {/* Message Content Container */}
        <div className={`space-y-4 overflow-hidden flex-1 flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
          <div className={`px-5 py-4 rounded-2xl shadow-sm leading-relaxed text-[15px] border w-full ${isAssistant
            ? 'bg-zinc-900 border-zinc-800 text-zinc-200 rounded-tl-none'
            : 'bg-indigo-600 border-indigo-500 text-white rounded-tr-none'
            }`}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ node, inline, className, children, ...props }: any) {
                  const match = /language-(\w+)/.exec(className || '');
                  return !inline && match ? (
                    <div className="rounded-lg overflow-hidden my-4 border border-zinc-800 shadow-xl text-left">
                      <div className="bg-zinc-800 px-4 py-1.5 flex justify-between items-center text-[10px] font-mono text-zinc-400">
                        <span>{match[1].toUpperCase()}</span>
                        <div className="flex space-x-1.5">
                          <div className="w-2.5 h-2.5 rounded-full bg-zinc-700"></div>
                          <div className="w-2.5 h-2.5 rounded-full bg-zinc-700"></div>
                          <div className="w-2.5 h-2.5 rounded-full bg-zinc-700"></div>
                        </div>
                      </div>
                      <SyntaxHighlighter
                        style={vscDarkPlus}
                        language={match[1]}
                        PreTag="div"
                        className="!m-0 !bg-zinc-950 !p-4 !text-sm scrollbar-thin scrollbar-thumb-zinc-800"
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    </div>
                  ) : (
                    <code className={`px-1.5 py-0.5 rounded font-mono text-sm ${isAssistant ? 'bg-zinc-800 text-indigo-300' : 'bg-indigo-500 text-white'}`} {...props}>
                      {children}
                    </code>
                  );
                },
                p: ({ children }) => <p className="mb-3 last:mb-0 text-left">{children}</p>,
                ul: ({ children }) => <ul className="list-disc ml-5 mb-3 space-y-1 text-left">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal ml-5 mb-3 space-y-1 text-left">{children}</ol>,
                li: ({ children }) => <li className="pl-1 text-left">{children}</li>,
                h1: ({ children }) => <h1 className="text-xl font-bold mb-4 mt-2 text-white border-b border-zinc-800 pb-2 text-left">{children}</h1>,
                h2: ({ children }) => <h2 className="text-lg font-bold mb-3 mt-4 text-zinc-100 text-left">{children}</h2>,
                h3: ({ children }) => <h3 className="text-base font-bold mb-2 mt-3 text-zinc-200 text-left">{children}</h3>,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-indigo-500 pl-4 py-1 italic bg-indigo-500/5 rounded-r my-4 text-left">
                    {children}
                  </blockquote>
                ),
                table: ({ children }) => (
                  <div className="overflow-x-auto my-4 shadow-lg rounded-lg border border-zinc-800 text-left">
                    <table className="min-w-full divide-y divide-zinc-800">
                      {children}
                    </table>
                  </div>
                ),
                thead: ({ children }) => <thead className="bg-zinc-800/50 text-left">{children}</thead>,
                th: ({ children }) => <th className="px-4 py-2 text-left text-xs font-bold text-zinc-400 uppercase tracking-wider border-r border-zinc-800 last:border-0">{children}</th>,
                td: ({ children }) => <td className="px-4 py-2 text-sm border-r border-zinc-800 last:border-0 text-left">{children}</td>,
                tr: ({ children }) => <tr className="divide-x divide-zinc-800 border-b border-zinc-800 last:border-0 hover:bg-zinc-800/30 transition-colors">{children}</tr>,
                a: ({ node, ...props }) => <a className="text-indigo-400 hover:text-indigo-300 underline underline-offset-4 decoration-indigo-400/50" target="_blank" rel="noopener noreferrer" {...props} />
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>

          {/* Message Files */}
          {message.files && message.files.length > 0 && (
            <div className={`grid grid-cols-1 gap-4 mt-4 w-full max-w-xl ${!isAssistant ? 'ml-auto' : ''}`}>
              {message.files.map((file, idx) => (
                <MediaRenderer key={idx} file={file} onFileClick={onFileClick} isAssistant={isAssistant} />
              ))}
            </div>
          )}

          {/* Timestamp */}
          <div className="text-[10px] text-zinc-600 font-medium uppercase tracking-tight px-1">
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      </div>
    </div>
  );
};

const MediaRenderer: React.FC<{
  file: GeneratedFile,
  onFileClick?: (file: GeneratedFile) => void,
  isAssistant: boolean
}> = ({ file, onFileClick, isAssistant }) => {
  switch (file.type) {
    case 'pdf':
      return (
        <button
          onClick={() => onFileClick?.(file)}
          className={`group flex items-center p-4 bg-zinc-900 border rounded-xl transition-all shadow-md animate-in zoom-in-95 duration-300 w-full text-left ${isAssistant ? 'border-zinc-800 hover:border-indigo-500' : 'border-indigo-500/30 hover:bg-zinc-800'
            }`}
        >
          <div className="p-3 bg-red-500/10 group-hover:bg-red-500/20 rounded-lg transition-colors mr-4">
            <svg className="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-zinc-200 group-hover:text-indigo-400 transition-colors truncate">{file.name}</div>
            <div className="text-[10px] text-zinc-500 uppercase font-bold tracking-widest mt-0.5">PDF Document • Click to View</div>
          </div>
          <div className="p-2 text-zinc-500 group-hover:text-indigo-400 transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          </div>
        </button>
      );
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
