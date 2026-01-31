import React from 'react';

interface NavBarProps {
    currentView: string;
    onNavigate: (view: string) => void;
    userPhoto?: string | null;
    userName?: string | null;
    onSignOut: () => void;
}

export const NavBar: React.FC<NavBarProps> = ({ currentView, onNavigate, userPhoto, userName, onSignOut }) => {
    return (
        <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 bg-zinc-900/90 p-1.5 rounded-xl border border-zinc-800 backdrop-blur-md shadow-lg">
                <button
                    onClick={() => onNavigate('dashboard')}
                    className="px-3 py-1.5 text-zinc-400 hover:text-white text-xs font-medium rounded-lg transition-colors hover:bg-zinc-800"
                >
                    Back to Dashboard
                </button>

                <div className="w-px h-4 bg-zinc-800 mx-1"></div>

                <button
                    onClick={() => onNavigate('radar')}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all text-xs font-medium ${currentView === 'radar'
                            ? 'bg-zinc-800 text-blue-400 shadow-sm ring-1 ring-zinc-700'
                            : 'text-zinc-400 hover:text-blue-300 hover:bg-zinc-800/50'
                        }`}
                    title="Research Radar"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
                    </svg>
                    <span className="hidden md:inline">Radar</span>
                </button>

                <button
                    onClick={() => onNavigate('exploration')}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all text-xs font-medium ${currentView === 'exploration'
                            ? 'bg-zinc-800 text-purple-400 shadow-sm ring-1 ring-zinc-700'
                            : 'text-zinc-400 hover:text-purple-300 hover:bg-zinc-800/50'
                        }`}
                    title="Exploration"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    <span className="hidden md:inline">Exploration</span>
                </button>

                <button
                    onClick={() => onNavigate('projects')}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all text-xs font-medium ${currentView === 'projects'
                            ? 'bg-zinc-800 text-green-400 shadow-sm ring-1 ring-zinc-700'
                            : 'text-zinc-400 hover:text-green-300 hover:bg-zinc-800/50'
                        }`}
                    title="Projects"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                    <span className="hidden md:inline">Projects</span>
                </button>
            </div>

            <div className="h-8 w-px bg-zinc-800/50 mx-1"></div>

            {/* User Profile */}
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
    );
};
