import React from 'react';

interface CapturedItem {
    id: string;
    title: string;
    summary?: string;
    url?: string;
    authors?: string[];
    timestamp?: string;
    added_at?: string;
    published?: string;
    type?: string;
    tags?: string[];
}

interface RadarItemsListProps {
    items: CapturedItem[];
    onItemClick: (item: CapturedItem) => void;
    onRefresh: () => void;
    onDeleteItem: (id: string) => void;
    onSaveToExploration: (item: CapturedItem) => void;
    onSaveToProject: (item: CapturedItem) => void;
    isLoading: boolean;
    outputMedia?: string;
    radarName?: string;
}

export const RadarItemsList: React.FC<RadarItemsListProps> = ({
    items,
    onItemClick,
    onRefresh,
    onDeleteItem,
    onSaveToExploration,
    onSaveToProject,
    isLoading,
    outputMedia,
    radarName
}) => {
    const [activeSaveMenu, setActiveSaveMenu] = React.useState<string | null>(null);

    // Close menu when clicking elsewhere
    React.useEffect(() => {
        const handleOutsideClick = () => setActiveSaveMenu(null);
        if (activeSaveMenu) {
            window.addEventListener('click', handleOutsideClick);
        }
        return () => window.removeEventListener('click', handleOutsideClick);
    }, [activeSaveMenu]);
    if (isLoading) {
        return (
            <div className="flex-1 flex flex-col p-6 space-y-4 overflow-y-auto bg-zinc-950/50">
                {[1, 2, 3].map(i => (
                    <div key={i} className="bg-zinc-900/40 border border-zinc-800/50 rounded-2xl p-5 animate-pulse">
                        <div className="h-4 bg-zinc-800 rounded w-3/4 mb-3"></div>
                        <div className="h-3 bg-zinc-800 rounded w-full mb-2"></div>
                        <div className="h-3 bg-zinc-800 rounded w-2/3"></div>
                    </div>
                ))}
            </div>
        );
    }

    if (items.length === 0) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-zinc-950/50">
                <div className="w-16 h-16 bg-zinc-900 rounded-full flex items-center justify-center mb-4 text-zinc-600">
                    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                </div>
                <h3 className="text-zinc-400 font-medium mb-2">No papers found yet</h3>
                <p className="text-zinc-600 text-sm mb-6">Run a manual sync or wait for the next scheduled update.</p>

                <button
                    onClick={onRefresh}
                    className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold transition-all flex items-center gap-2 shadow-lg shadow-blue-500/20"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Trigger Initial Sweep
                </button>
            </div>
        );
    }

    const getRelativeTime = (timestamp: string) => {
        try {
            const date = new Date(timestamp);
            const now = new Date();
            const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
            if (diffInHours < 1) return 'Just now';
            if (diffInHours < 24) return `${diffInHours} hours ago`;
            return `${Math.floor(diffInHours / 24)} days ago`;
        } catch (e) {
            return 'Recently';
        }
    };

    return (
        <div className="flex-1 flex flex-col p-6 space-y-4 overflow-y-auto bg-[#0a0a0f]">
            <div className="flex items-center justify-between mb-4 px-2">
                <h3 className="text-zinc-500 text-[11px] font-bold uppercase tracking-[0.2em]">Latest Updates</h3>
                <div className="flex items-center gap-4">
                    <span className="text-zinc-600 text-[10px] font-medium">{items.length} items found</span>
                    <button
                        onClick={onRefresh}
                        className="p-1.5 text-zinc-500 hover:text-white hover:bg-zinc-800 rounded-lg transition-all"
                        title="Refresh Feed"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                    </button>
                </div>
            </div>
            {items.map((item) => (
                <div
                    key={item.id}
                    onClick={() => onItemClick(item)}
                    className="bg-[#161621] border border-zinc-800/40 rounded-2xl p-6 hover:border-zinc-700/60 transition-all cursor-pointer group shadow-xl"
                >
                    {/* Top Row: Category and Time */}
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <span className="px-3 py-1 bg-blue-500/10 text-blue-400 text-[11px] font-bold rounded-full border border-blue-500/20">
                                {radarName || item.type || 'Research Radar'}
                            </span>
                            <span className="text-zinc-500 text-xs font-medium">
                                {getRelativeTime(item.added_at || item.published || item.timestamp || '')}
                            </span>
                        </div>
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                if (window.confirm('Delete this paper from your feed?')) {
                                    onDeleteItem(item.id);
                                }
                            }}
                            className="p-1.5 text-zinc-600 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                            title="Delete Item"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                        </button>
                    </div>

                    {/* Title */}
                    <h4 className="text-white font-bold text-lg mb-1 leading-tight group-hover:text-blue-200 transition-colors">
                        {item.title}
                    </h4>

                    {/* Authors */}
                    <div className="flex flex-wrap gap-x-2 gap-y-1 mb-3">
                        {item.authors && item.authors.map((author, idx) => (
                            <span key={idx} className="text-zinc-500 text-xs font-medium">
                                {author}{idx < item.authors.length - 1 ? ' •' : ''}
                            </span>
                        ))}
                    </div>

                    {/* Summary */}
                    <p className="text-zinc-400 text-[13px] line-clamp-2 mb-6 leading-relaxed opacity-80">
                        {item.summary}
                    </p>



                    {/* Bottom Row: Actions and Source */}
                    <div className="flex items-center justify-between mt-auto">
                        <div className="flex items-center gap-2 relative">
                            <button
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveSaveMenu(activeSaveMenu === item.id ? null : item.id);
                                }}
                                className="flex items-center gap-2 bg-[#4a89f3] text-white px-4 py-2 rounded-xl text-xs font-bold hover:bg-blue-500 transition-all shadow-lg shadow-blue-500/10"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                                </svg>
                                Save
                            </button>

                            {/* Save Menu Dropdown */}
                            {activeSaveMenu === item.id && (
                                <div
                                    className="absolute bottom-full left-0 mb-2 w-48 bg-[#1a1b2e] border border-zinc-800 rounded-xl shadow-2xl z-50 py-2 animate-in fade-in slide-in-from-bottom-2 duration-200"
                                    onClick={(e) => e.stopPropagation()}
                                >
                                    <button
                                        onClick={() => {
                                            onSaveToExploration(item);
                                            setActiveSaveMenu(null);
                                        }}
                                        className="w-full text-left px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800 hover:text-white transition-colors flex items-center gap-2"
                                    >
                                        <svg className="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                        </svg>
                                        Save to Exploration
                                    </button>
                                    <button
                                        onClick={() => {
                                            onSaveToProject(item);
                                            setActiveSaveMenu(null);
                                        }}
                                        className="w-full text-left px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800 hover:text-white transition-colors flex items-center gap-2"
                                    >
                                        <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                                        </svg>
                                        Save to Project...
                                    </button>
                                </div>
                            )}


                        </div>
                        <span className="text-zinc-600 text-[10px] font-bold uppercase tracking-widest pt-2">
                            {item.type || 'arXiv'}
                        </span>
                    </div>
                </div>
            ))}
        </div>
    );
};
