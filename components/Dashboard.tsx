import React from 'react';
import { Sidebar } from './Sidebar';
import { Message } from '../types';

interface DashboardProps {
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
    activeDocumentUrl?: string;
}

export const Dashboard: React.FC<DashboardProps> = ({
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
                activeDocumentUrl={activeDocumentUrl}
            />

            <main className="flex-1 flex flex-col relative overflow-hidden bg-zinc-950">
                {/* Mobile Sidebar Toggle - only show when sidebar is closed */}
                {!isSidebarOpen && (
                    <button
                        onClick={onToggleSidebar}
                        className="absolute top-4 left-4 z-50 p-2 bg-zinc-900 border border-zinc-800 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all shadow-lg animate-in slide-in-from-left duration-300"
                        title="Show Sidebar"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                        </svg>
                    </button>
                )}

                <div className="flex-1 overflow-y-auto p-8 relative">
                    {/* Background effects */}
                    <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
                        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-900/10 rounded-full blur-[100px]" />
                        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-900/10 rounded-full blur-[100px]" />
                    </div>

                    {/* Header */}
                    <div className="relative z-10 flex justify-between items-center mb-16 pl-12 md:pl-0">
                        {/* Added padding-left for mobile toggle space */}
                        <div className="flex items-center gap-4">
                            <h1 className="text-3xl font-medium italic tracking-wide bg-gradient-to-br from-blue-300 via-blue-500 to-blue-600 bg-clip-text text-transparent" style={{ fontFamily: "'Playfair Display', serif" }}>
                                Aletheia
                            </h1>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900/50 border border-zinc-800 rounded-full backdrop-blur-sm">
                                {userPhoto && (
                                    <img src={userPhoto} alt="Profile" className="w-6 h-6 rounded-full border border-zinc-700" />
                                )}
                                <span className="text-zinc-300 text-xs font-medium">{userName}</span>
                            </div>
                            <button
                                onClick={onSignOut}
                                className="px-4 py-1.5 bg-zinc-900 text-zinc-400 text-sm rounded-lg hover:text-white transition-colors border border-zinc-800"
                            >
                                Sign Out
                            </button>
                        </div>
                    </div>

                    {/* Main Content */}
                    <div className="relative z-10 max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8 pt-10">

                        {/* Research Radar Card */}
                        <div
                            onClick={() => onNavigate('radar')}
                            className="group relative bg-zinc-900/40 border border-zinc-800 rounded-2xl p-8 hover:bg-zinc-900/60 transition-all duration-300 hover:border-zinc-700 hover:shadow-2xl hover:shadow-blue-900/10 cursor-pointer"
                        >
                            <div className="h-12 w-12 rounded-lg bg-blue-500/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                                <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
                                </svg>
                            </div>
                            <h2 className="text-2xl font-semibold mb-3 text-zinc-100 group-hover:text-blue-200 transition-colors">Research Radar</h2>
                            <p className="text-zinc-400 leading-relaxed">
                                Monitor and collect data from configured sources. Track academic papers, tech blogs, and market trends in real-time.
                            </p>
                            <div className="mt-8 flex items-center text-blue-400 text-sm font-medium opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300">
                                View Radar <span className="ml-2">→</span>
                            </div>
                        </div>

                        {/* Exploration Card */}
                        <div
                            onClick={() => onNavigate('exploration')}
                            className="group relative bg-zinc-900/40 border border-zinc-800 rounded-2xl p-8 hover:bg-zinc-900/60 transition-all duration-300 hover:border-zinc-700 hover:shadow-2xl hover:shadow-purple-900/10 cursor-pointer"
                        >
                            <div className="h-12 w-12 rounded-lg bg-purple-500/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                                <svg className="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                            </div>
                            <h2 className="text-2xl font-semibold mb-3 text-zinc-100 group-hover:text-purple-200 transition-colors">Exploration</h2>
                            <p className="text-zinc-400 leading-relaxed">
                                Deep dive into topics with AI-assisted research. Chat, analyze documents, and generate multimedia reports.
                            </p>
                            <div className="mt-8 flex items-center text-purple-400 text-sm font-medium opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300">
                                Start Exploration <span className="ml-2">→</span>
                            </div>
                        </div>

                        {/* Projects Card */}
                        <div
                            onClick={() => onNavigate('projects')}
                            className="group relative bg-zinc-900/40 border border-zinc-800 rounded-2xl p-8 hover:bg-zinc-900/60 transition-all duration-300 hover:border-zinc-700 hover:shadow-2xl hover:shadow-green-900/10 cursor-pointer"
                        >
                            <div className="h-12 w-12 rounded-lg bg-green-500/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                                <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                                </svg>
                            </div>
                            <h2 className="text-2xl font-semibold mb-3 text-zinc-100 group-hover:text-green-200 transition-colors">Projects</h2>
                            <p className="text-zinc-400 leading-relaxed">
                                Manage your research projects, saved collections, and generated artifacts in one organized space.
                            </p>
                            <div className="mt-8 flex items-center text-green-400 text-sm font-medium opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300">
                                View Projects <span className="ml-2">→</span>
                            </div>
                        </div>

                    </div>
                </div>
            </main>
        </div>
    );
};
