import React from 'react';

interface CapturedItem {
    id: string;
    title: string;
    summary: string;
    url?: string;
    authors: string[];
    timestamp: any;
    type: string;
}

interface RadarItemsListProps {
    items: CapturedItem[];
    onItemClick: (item: CapturedItem) => void;
    onRefresh: () => void;
    isLoading: boolean;
}

export const RadarItemsList: React.FC<RadarItemsListProps> = ({ items, onItemClick, onRefresh, isLoading }) => {
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
                    disabled={isLoading}
                    className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-semibold transition-all flex items-center gap-2"
                >
                    <svg className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Trigger Initial Sweep
                </button>
            </div>
        );
    }

    return (
        <div className="flex-1 flex flex-col p-6 space-y-4 overflow-y-auto bg-zinc-950/50 custom-scrollbar">
            <div className="flex items-center justify-between mb-2">
                <h3 className="text-zinc-400 text-xs font-bold uppercase tracking-widest">Captured Papers</h3>
                <div className="flex items-center gap-4">
                    <span className="text-zinc-600 text-[10px]">{items.length} items found</span>
                    <button
                        onClick={onRefresh}
                        className="text-zinc-500 hover:text-white transition-colors"
                        title="Refresh Feed"
                    >
                        <svg className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                    </button>
                </div>
            </div>
            {items.map((item) => (
                <div
                    key={item.id}
                    onClick={() => onItemClick(item)}
                    className="bg-zinc-900/60 border border-zinc-800/50 rounded-2xl p-5 hover:bg-zinc-900 hover:border-blue-500/30 transition-all cursor-pointer group shadow-sm"
                >
                    <div className="flex justify-between items-start mb-2">
                        <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 text-[10px] font-bold rounded uppercase tracking-tighter border border-blue-500/20">
                            {item.type}
                        </span>
                        {item.url && (
                            <a
                                href={item.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                className="text-zinc-600 hover:text-blue-400 transition-colors"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                            </a>
                        )}
                    </div>
                    <h4 className="text-white font-semibold text-sm mb-2 group-hover:text-blue-300 transition-colors leading-snug">
                        {item.title}
                    </h4>
                    <p className="text-zinc-500 text-xs line-clamp-3 mb-3 leading-relaxed">
                        {item.summary}
                    </p>
                    <div className="flex flex-wrap gap-1 mt-auto">
                        {item.authors.slice(0, 2).map((author, idx) => (
                            <span key={idx} className="text-zinc-600 text-[10px] bg-zinc-800/50 px-2 py-0.5 rounded">
                                {author}
                            </span>
                        ))}
                    </div>
                </div>
            ))}
        </div>
    );
};
