import React from 'react';
import { Sidebar } from './Sidebar';
import { NavBar } from './NavBar';
import { Message } from '../types';

interface ComingSoonProps {
    title: string;
    description: string;
    onNavigate: (view: string) => void;
    userPhoto?: string | null;
    userName?: string | null;
    onSignOut: () => void;
    // Sidebar props
    isSidebarOpen: boolean;
    onToggleSidebar: () => void;
    messages: Message[];
    onNewConversation: () => void;
    threads: { id: string, title: string }[];
    onSelectThread: (id: string) => void;
    documents: { name: string, url: string }[];
    onSelectDocument: (doc: { url: string, name: string } | null) => void;
    onDeleteDocument?: (id: string) => void;
    onDownloadDocument?: (doc: { name: string, url: string }) => void;
    onDeleteThread?: (id: string) => void;
    activeDocumentUrl?: string;
}

export const ComingSoon: React.FC<ComingSoonProps> = ({
    title,
    description,
    onNavigate,
    userPhoto,
    userName,
    onSignOut,
    isSidebarOpen,
    onToggleSidebar,
    messages,
    onNewConversation,
    threads,
    onSelectThread,
    documents,
    onSelectDocument,
    onDeleteDocument,
    onDownloadDocument,
    onDeleteThread,
    activeDocumentUrl
}) => {
    return (
        <div className="flex h-screen w-full overflow-hidden bg-zinc-950">
            <Sidebar
                isOpen={isSidebarOpen}
                onToggle={onToggleSidebar}
                messages={messages}
                userName={userName}
                userPhoto={userPhoto}
                onNewConversation={onNewConversation}
                threads={threads}
                onSelectThread={onSelectThread}
                documents={documents}
                onSelectDocument={onSelectDocument}
                onDeleteDocument={onDeleteDocument}
                onDownloadDocument={onDownloadDocument}
                onDeleteThread={onDeleteThread}
                activeDocumentUrl={activeDocumentUrl}
            />

            <main className="flex-1 flex flex-col relative overflow-hidden bg-zinc-950">
                {/* Mobile Sidebar Toggle - only show when sidebar is closed */}
                {!isSidebarOpen && (
                    <button
                        onClick={onToggleSidebar}
                        className="absolute bottom-4 left-4 z-50 p-2 bg-zinc-900 border border-zinc-800 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all shadow-lg animate-in slide-in-from-left duration-300"
                        title="Show Sidebar"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                        </svg>
                    </button>
                )}

                <div className="flex-1 overflow-y-auto p-8 relative flex flex-col">
                    {/* Background effects */}
                    <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
                        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-900/10 rounded-full blur-[100px]" />
                        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-900/10 rounded-full blur-[100px]" />
                    </div>

                    {/* Header */}
                    <div className="relative z-10 flex justify-between items-center mb-16 pl-12 md:pl-0">
                        <div className="flex items-center gap-4">
                            <h1 className="text-3xl font-medium italic tracking-wide bg-gradient-to-br from-blue-300 via-blue-500 to-blue-600 bg-clip-text text-transparent" style={{ fontFamily: "'Playfair Display', serif" }}>
                                Aletheia
                            </h1>
                        </div>
                        <div className="flex items-center gap-4">
                            <NavBar
                                currentView={title === 'Research Radar' ? 'radar' : 'projects'}
                                onNavigate={onNavigate}
                                userPhoto={userPhoto}
                                userName={userName}
                                onSignOut={onSignOut}
                            />
                        </div>
                    </div>

                    {/* Main Content - Centered */}
                    <div className="relative z-10 flex-1 flex flex-col items-center justify-center -mt-20">
                        <div className="bg-zinc-900/40 border border-zinc-800 p-12 rounded-3xl max-w-2xl text-center backdrop-blur-sm shadow-2xl relative overflow-hidden group">
                            {/* Glow effect */}
                            <div className="absolute inset-0 bg-gradient-to-tr from-blue-500/5 via-transparent to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />

                            <div className="relative z-10">
                                <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-zinc-800/50 mb-8 border border-zinc-700/50">
                                    <svg className="w-10 h-10 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                </div>
                                <h2 className="text-4xl font-bold text-white mb-4 tracking-tight">{title}</h2>
                                <p className="text-zinc-400 text-lg leading-relaxed max-w-lg mx-auto">
                                    {description}
                                </p>
                                <div className="mt-8">
                                    <span className="inline-block px-4 py-1.5 rounded-full bg-blue-500/10 text-blue-400 text-xs font-semibold tracking-wider uppercase border border-blue-500/20">
                                        Coming Soon
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                </div>
            </main>
        </div>
    );
};
