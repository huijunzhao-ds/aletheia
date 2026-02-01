import React, { useState, useEffect } from 'react';
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
  documents?: { id?: string, name: string, url: string, isRadarAsset?: boolean }[];
  onSelectDocument?: (doc: { id?: string, name: string, url: string, isRadarAsset?: boolean }) => void;
  onDeleteDocument?: (id: string) => void;
  onDownloadDocument?: (doc: { name: string, url: string }) => void;
  activeDocumentUrl?: string;
}

type SectionKey = 'articles' | 'multimedia' | 'archived' | 'history';

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
  onDeleteDocument,
  onDownloadDocument,
  activeDocumentUrl
}) => {
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);

  useEffect(() => {
    const handleOutsideClick = () => setActiveMenuId(null);
    if (activeMenuId) window.addEventListener('click', handleOutsideClick);
    return () => window.removeEventListener('click', handleOutsideClick);
  }, [activeMenuId]);

  const [expandedSections, setExpandedSections] = useState<Record<SectionKey, boolean>>({
    articles: false,
    multimedia: false,
    archived: false,
    history: false
  });

  // Helper to filter documents based on extension for demo purposes
  const articleDocs = documents.filter(d => !d.isRadarAsset && !d.name.match(/\.(mp4|mp3|wav|mov)$/i));
  const mediaDocs = documents.filter(d => d.isRadarAsset || d.name.match(/\.(mp4|mp3|wav|mov)$/i));

  // Auto-collapse/expand based on content presence
  useEffect(() => {
    setExpandedSections(prev => ({
      ...prev,
      articles: articleDocs.length > 0,
      multimedia: mediaDocs.length > 0,
      history: threads.length > 0 && !prev.history ? true : prev.history
    }));
  }, [articleDocs.length, mediaDocs.length, threads.length]);

  // Specific "show as closed if empty" global rule
  useEffect(() => {
    if (articleDocs.length === 0) setExpandedSections(p => ({ ...p, articles: false }));
    if (mediaDocs.length === 0) setExpandedSections(p => ({ ...p, multimedia: false }));
    if (threads.length === 0) setExpandedSections(p => ({ ...p, history: false }));
  }, [articleDocs.length, mediaDocs.length, threads.length]);

  const toggleSection = (section: SectionKey) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  // Helper to filter documents based on extension for demo purposes
  // In a real app, 'documents' should have a 'type' field.

  return (
    <aside
      className={`transition-all duration-300 border-r border-zinc-800 bg-zinc-900 flex flex-col ${isOpen ? 'w-72' : 'w-0'
        } overflow-hidden`}
    >
      {/* Header */}
      <div className="p-4 flex flex-col border-b border-zinc-800">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 bg-indigo-500 rounded-md rotate-3 shadow-lg shadow-indigo-500/20"></div>
            <h1 className="text-xl italic font-medium bg-gradient-to-br from-blue-300 via-blue-500 to-blue-600 bg-clip-text text-transparent" style={{ fontFamily: "'Playfair Display', serif" }}>Aletheia</h1>
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
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">

        {/* Material Articles Section */}
        <div className="border-b border-zinc-800/50 pb-1">
          <button
            onClick={() => toggleSection('articles')}
            className="w-full flex items-center justify-between p-2 text-xs font-semibold text-blue-400 uppercase tracking-wider hover:text-blue-300 transition-colors"
          >
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
              </svg>
              <span>Material Articles</span>
            </div>
            <svg className={`w-3 h-3 transition-transform ${expandedSections.articles ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {expandedSections.articles && (
            <div className="pl-4 pr-2 space-y-0.5 mt-1">
              {articleDocs.map((doc, idx) => (
                <div
                  key={idx}
                  onClick={() => onSelectDocument?.(doc)}
                  className={`px-3 py-2 text-sm rounded cursor-pointer truncate flex items-center gap-2 group transition-colors ${activeDocumentUrl === doc.url
                    ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 border border-transparent'
                    }`}
                  title={doc.name}
                >
                  <svg className={`w-3.5 h-3.5 flex-shrink-0 ${activeDocumentUrl === doc.url ? 'text-indigo-400' : 'text-zinc-600 group-hover:text-zinc-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="truncate">{doc.name}</span>
                </div>
              ))}
              {articleDocs.length === 0 && (
                <div className="px-3 py-2 text-xs text-zinc-600 italic">No articles</div>
              )}
            </div>
          )}
        </div>

        {/* Multi-media Assets Section */}
        <div className="border-b border-zinc-800/50 pb-1">
          <button
            onClick={() => toggleSection('multimedia')}
            className="w-full flex items-center justify-between p-2 text-xs font-semibold text-blue-400 uppercase tracking-wider hover:text-blue-300 transition-colors"
          >
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Multi-media Assets</span>
            </div>
            <svg className={`w-3 h-3 transition-transform ${expandedSections.multimedia ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {expandedSections.multimedia && (
            <div className="pl-4 pr-2 space-y-0.5 mt-1">
              {mediaDocs.map((doc, idx) => (
                <div
                  key={idx}
                  onClick={() => onSelectDocument?.(doc)}
                  className={`px-3 py-2 text-sm rounded cursor-pointer truncate flex items-center justify-between group transition-colors ${activeDocumentUrl === doc.url
                    ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 border border-transparent'
                    }`}
                  title={doc.name}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {doc.name.match(/\.md$/i) ? (
                      <svg className="w-3.5 h-3.5 flex-shrink-0 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    ) : (
                      <svg className="w-3.5 h-3.5 flex-shrink-0 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      </svg>
                    )}
                    <span className="truncate">{doc.name}</span>
                  </div>

                  <div className="relative">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveMenuId(activeMenuId === `${idx}` ? null : `${idx}`);
                      }}
                      className="p-1 hover:bg-zinc-700 rounded transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <svg className="w-3.5 h-3.5 text-zinc-500" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 8a2 2 0 100-4 2 2 0 000 4zM12 14a2 2 0 100-4 2 2 0 000 4zM12 20a2 2 0 100-4 2 2 0 000 4z" />
                      </svg>
                    </button>

                    {activeMenuId === `${idx}` && (
                      <div className="absolute right-0 top-full mt-1 w-32 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl z-50 py-1">
                        <button
                          onClick={() => onDownloadDocument?.(doc)}
                          className="w-full text-left px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-700 flex items-center gap-2"
                        >
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                          </svg>
                          Download
                        </button>
                        <button
                          onClick={() => doc.id && onDeleteDocument?.(doc.id)}
                          className="w-full text-left px-3 py-1.5 text-xs text-red-400 hover:bg-zinc-700 flex items-center gap-2"
                        >
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {mediaDocs.length === 0 && (
                <div className="px-3 py-2 text-xs text-zinc-600 italic">No media assets</div>
              )}
            </div>
          )}
        </div>

        {/* Archived References Section */}
        <div className="border-b border-zinc-800/50 pb-1">
          <button
            onClick={() => toggleSection('archived')}
            className="w-full flex items-center justify-between p-2 text-xs font-semibold text-blue-400 uppercase tracking-wider hover:text-blue-300 transition-colors"
          >
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
              </svg>
              <span>Archived References</span>
            </div>
            <svg className={`w-3 h-3 transition-transform ${expandedSections.archived ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {expandedSections.archived && (
            <div className="pl-4 pr-2 space-y-0.5 mt-1">
              <div className="px-3 py-2 text-xs text-zinc-600 italic">No archived items</div>
            </div>
          )}
        </div>

        {/* History Chats Section */}
        <div className="pb-1">
          <button
            onClick={() => toggleSection('history')}
            className="w-full flex items-center justify-between p-2 text-xs font-semibold text-blue-400 uppercase tracking-wider hover:text-blue-300 transition-colors"
          >
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <span>History Chats</span>
            </div>
            <svg className={`w-3 h-3 transition-transform ${expandedSections.history ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>


          {expandedSections.history && (
            <div className="pl-4 pr-2 space-y-0.5 mt-1">
              {threads.map((thread) => (
                <div
                  key={thread.id}
                  onClick={() => onSelectThread?.(thread.id)}
                  className="px-3 py-2 text-sm text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded cursor-pointer truncate flex items-center gap-2 group"
                >
                  <svg className="w-3.5 h-3.5 flex-shrink-0 text-zinc-600 group-hover:text-indigo-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span className="truncate">{thread.title}</span>
                </div>
              ))}
              {threads.length === 0 && (
                <div className="px-3 py-2 text-xs text-zinc-600 italic">No recent chats</div>
              )}
            </div>
          )}
        </div>

      </div>

      {/* User Profile Footer */}
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
