import React, { useState, useRef, useEffect } from 'react';
import { getAuth } from 'firebase/auth';
import { Sidebar } from './Sidebar';
import { NavBar } from './NavBar';
import { Message } from '../types';

interface ResearchRadarProps {
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

interface RadarItem {
    id: string;
    title: string;
    description: string;
    source: string;
    lastUpdated: string;
    status: 'active' | 'paused';
}

export const ResearchRadar: React.FC<ResearchRadarProps> = ({
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
    // State for radars
    const [radars, setRadars] = useState<RadarItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    // Fetch radars on mount
    useEffect(() => {
        const fetchRadars = async () => {
            try {
                const auth = getAuth();
                const user = auth.currentUser;
                if (!user) return;
                const token = await user.getIdToken();

                const response = await fetch('/api/radars', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    // map backend data to frontend interface
                    const mappedRadars: RadarItem[] = data.map((item: any) => ({
                        id: item.id,
                        title: item.title,
                        description: item.description,
                        source: Array.isArray(item.sources) ? item.sources.join(', ') : (item.source || ''),
                        lastUpdated: item.lastUpdated || 'Unknown',
                        status: item.status || 'active'
                    }));
                    setRadars(mappedRadars);
                }
            } catch (error) {
                console.error("Failed to fetch radars:", error);
            } finally {
                setIsLoading(false);
            }
        };

        fetchRadars();
    }, []);

    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [isSourceDropdownOpen, setIsSourceDropdownOpen] = useState(false);

    // Config for Sources
    const availableSources = [
        { id: 'Arxiv', label: 'Arxiv', available: true },
        { id: 'X', label: 'X (Twitter)', available: false },
        { id: 'RSS', label: 'RSS', available: false },
        { id: 'URL', label: 'URL', available: false }
    ];

    const [newRadar, setNewRadar] = useState<{
        title: string;
        description: string;
        sources: string[];
        frequency: string;
        outputMedia: string;
        customPrompt: string;
        arxivConfig?: {
            categories: string;
            authors: string;
            keywords: string;
            journalReference?: string;
        };
    }>({
        title: '',
        description: '',
        sources: [],
        frequency: 'Daily',
        outputMedia: 'Text Digest',
        customPrompt: ''
    });

    const dropdownRef = useRef<HTMLDivElement>(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsSourceDropdownOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    const handleCreateRadar = () => {
        setIsCreateModalOpen(true);
    };

    const handleCloseModal = () => {
        setIsCreateModalOpen(false);
        setIsSourceDropdownOpen(false);
        // Reset form
        setNewRadar({
            title: '',
            description: '',
            sources: [],
            frequency: 'Daily',
            outputMedia: 'Text Digest',
            customPrompt: '',
            arxivConfig: {
                categories: '',
                authors: '',
                keywords: '',
                journalReference: ''
            }
        });
    };

    const handleSaveRadar = async () => {
        try {
            const auth = getAuth();
            const user = auth.currentUser;
            if (!user) return;
            const token = await user.getIdToken();

            const payload = {
                title: newRadar.title,
                description: newRadar.description,
                sources: newRadar.sources,
                frequency: newRadar.frequency,
                outputMedia: newRadar.outputMedia,
                customPrompt: newRadar.customPrompt,
                arxivConfig: newRadar.sources.includes('Arxiv') ? {
                    categories: newRadar.arxivConfig?.categories?.split(',').map(s => s.trim()).filter(Boolean) || [],
                    authors: newRadar.arxivConfig?.authors?.split(',').map(s => s.trim()).filter(Boolean) || [],
                    keywords: newRadar.arxivConfig?.keywords?.split(',').map(s => s.trim()).filter(Boolean) || [],
                    journalReference: newRadar.arxivConfig?.journalReference || ''
                } : null
            };

            const response = await fetch('/api/radars', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                const result = await response.json();

                // Add new radar to local state (optimistic or using response data)
                const radar: RadarItem = {
                    id: result.id,
                    title: newRadar.title,
                    description: newRadar.description,
                    source: newRadar.sources.join(', '),
                    lastUpdated: 'Just now',
                    status: 'active'
                };
                setRadars([...radars, radar]);
                handleCloseModal();
            } else {
                console.error("Failed to save radar");
            }

        } catch (error) {
            console.error("Error saving radar:", error);
        }
    };

    const handleSourceToggle = (source: string) => {
        setNewRadar(prev => {
            if (prev.sources.includes(source)) {
                return { ...prev, sources: prev.sources.filter(s => s !== source) };
            } else {
                return { ...prev, sources: [...prev.sources, source] };
            }
        });
    };

    const removeSource = (source: string) => {
        setNewRadar(prev => ({ ...prev, sources: prev.sources.filter(s => s !== source) }));
    };

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
                {/* Mobile Sidebar Toggle */}
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

                <div className="flex-1 overflow-y-auto p-8 relative flex flex-col">
                    {/* Background effects */}
                    <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
                        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-900/10 rounded-full blur-[100px]" />
                        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-900/10 rounded-full blur-[100px]" />
                    </div>

                    {/* Header */}
                    <div className="relative z-10 flex justify-between items-center mb-12 pl-12 md:pl-0">
                        <div className="flex items-center gap-4">
                            <h1 className="text-3xl font-medium italic tracking-wide bg-gradient-to-br from-blue-300 via-blue-500 to-blue-600 bg-clip-text text-transparent" style={{ fontFamily: "'Playfair Display', serif" }}>
                                Aletheia
                            </h1>
                        </div>
                        <div className="flex items-center gap-4">
                            <NavBar
                                currentView="radar"
                                onNavigate={onNavigate}
                                userPhoto={userPhoto}
                                userName={userName}
                                onSignOut={onSignOut}
                            />
                        </div>
                    </div>

                    {/* Page Title & Description */}
                    <div className="relative z-10 mb-12 max-w-4xl">
                        <h2 className="text-4xl font-bold text-white mb-4 tracking-tight">Research Radar</h2>
                        <p className="text-zinc-400 text-lg leading-relaxed">
                            Research Radar will allow you to track real-time updates from Arxiv, Tech Blogs, and Social Media.
                        </p>
                    </div>

                    {/* Radar List Grid */}
                    <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {/* New Radar Card */}
                        <div
                            onClick={handleCreateRadar}
                            className="bg-zinc-900/40 border border-dashed border-zinc-800 rounded-2xl p-8 flex flex-col items-center justify-center min-h-[200px] hover:bg-zinc-900/60 hover:border-blue-500/50 transition-all cursor-pointer group"
                        >
                            <div className="w-16 h-16 rounded-full bg-blue-500/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                </svg>
                            </div>
                            <span className="text-zinc-400 font-medium group-hover:text-blue-300 transition-colors">Create New Radar</span>
                        </div>

                        {/* Existing Radars */}
                        {radars.map((radar) => (
                            <div key={radar.id} className="bg-zinc-900/80 border border-zinc-800 rounded-2xl p-6 hover:border-zinc-700 transition-all shadow-lg backdrop-blur-sm group">
                                <div className="flex justify-between items-start mb-4">
                                    <h3 className="text-xl font-semibold text-white group-hover:text-blue-400 transition-colors">{radar.title}</h3>
                                    <div className={`w-2 h-2 rounded-full ${radar.status === 'active' ? 'bg-green-500' : 'bg-yellow-500'}`} />
                                </div>
                                <p className="text-zinc-400 text-sm mb-6 line-clamp-2">{radar.description}</p>

                                <div className="flex items-center justify-between text-xs text-zinc-500 border-t border-zinc-800/50 pt-4">
                                    <div className="flex items-center gap-2">
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                        </svg>
                                        <span>{radar.source}</span>
                                    </div>
                                    <span>{radar.lastUpdated}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Create Radar Modal */}
                {isCreateModalOpen && (
                    <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg shadow-2xl animate-in fade-in zoom-in duration-300 flex flex-col max-h-[90vh]">
                            <div className="flex justify-between items-center p-6 border-b border-zinc-800">
                                <h3 className="text-xl font-semibold text-white">Create New Radar</h3>
                                <button onClick={handleCloseModal} className="text-zinc-400 hover:text-white transition-colors">
                                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>

                            <div className="p-6 space-y-4 overflow-y-auto">
                                <div>
                                    <label className="block text-sm font-medium text-zinc-400 mb-1">
                                        Title <span className="text-red-500 ml-0.5">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={newRadar.title}
                                        onChange={(e) => setNewRadar({ ...newRadar, title: e.target.value })}
                                        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                        placeholder="e.g. AI Agents Trend"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-zinc-400 mb-1">Description</label>
                                    <textarea
                                        value={newRadar.description}
                                        onChange={(e) => setNewRadar({ ...newRadar, description: e.target.value })}
                                        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 h-24 resize-none"
                                        placeholder="What should this radar track?"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-zinc-400 mb-2">
                                        Sources <span className="text-red-500 ml-0.5">*</span>
                                    </label>

                                    {/* Selected Tokens - Floating Panel Style */}
                                    <div className="flex flex-wrap gap-2 mb-2 min-h-[2rem]">
                                        {newRadar.sources.map(sId => {
                                            const sourceDef = availableSources.find(s => s.id === sId) || { label: sId };
                                            return (
                                                <span key={sId} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-blue-500/20 text-blue-300 border border-blue-500/30 text-sm animate-in zoom-in-50 duration-200">
                                                    {sourceDef.label}
                                                    <button
                                                        onClick={() => removeSource(sId)}
                                                        className="hover:text-white ml-1 focus:outline-none"
                                                    >
                                                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                        </svg>
                                                    </button>
                                                </span>
                                            );
                                        })}
                                    </div>

                                    {/* Multi-Select Dropdown */}
                                    <div className="relative" ref={dropdownRef}>
                                        <button
                                            type="button"
                                            onClick={() => setIsSourceDropdownOpen(!isSourceDropdownOpen)}
                                            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-left text-zinc-300 focus:outline-none focus:ring-2 focus:ring-blue-500/50 flex justify-between items-center"
                                        >
                                            <span className="text-sm">Select sources...</span>
                                            <svg className={`w-4 h-4 text-zinc-500 transition-transform ${isSourceDropdownOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                            </svg>
                                        </button>

                                        {isSourceDropdownOpen && (
                                            <div className="absolute z-10 w-full mt-1 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-100">
                                                {availableSources.map(source => (
                                                    <div
                                                        key={source.id}
                                                        onClick={() => {
                                                            handleSourceToggle(source.id);
                                                            // Optional: Close on select? Maybe keep open for multi-select.
                                                        }}
                                                        className={`
                                                            px-4 py-2.5 text-sm cursor-pointer flex items-center justify-between
                                                            ${newRadar.sources.includes(source.id) ? 'bg-blue-900/20 text-blue-300' : 'text-zinc-300 hover:bg-zinc-700'}
                                                        `}
                                                    >
                                                        <span className={!source.available ? 'opacity-50' : ''}>{source.label}</span>
                                                        <div className="flex items-center gap-2">
                                                            {!source.available && <span className="text-[10px] px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-500">Soon</span>}
                                                            {newRadar.sources.includes(source.id) && (
                                                                <svg className="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                                </svg>
                                                            )}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                    <p className="text-xs text-zinc-500 mt-2">
                                        Select one or more sources to track. Currently only Arxiv is fully supported.
                                    </p>
                                </div>

                                {/* Arxiv Specific Configuration */}
                                {newRadar.sources.includes('Arxiv') && (
                                    <div className="bg-zinc-800/30 border border-zinc-800 rounded-xl p-4 space-y-4 animate-in fade-in slide-in-from-top-2">
                                        <div className="flex items-center gap-2 mb-2">
                                            <div className="w-1 h-4 bg-orange-500 rounded-full" />
                                            <h4 className="text-sm font-semibold text-zinc-200">Arxiv Configuration</h4>
                                        </div>

                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-xs font-medium text-zinc-400 mb-1">Categories / Subjects</label>
                                                <input
                                                    type="text"
                                                    value={newRadar.arxivConfig?.categories || ''}
                                                    onChange={(e) => setNewRadar({
                                                        ...newRadar,
                                                        arxivConfig: {
                                                            ...newRadar.arxivConfig!,
                                                            categories: e.target.value
                                                        }
                                                    })}
                                                    className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-orange-500/50"
                                                    placeholder="e.g. cs.AI, cs.LG"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs font-medium text-zinc-400 mb-1">Authors</label>
                                                <input
                                                    type="text"
                                                    value={newRadar.arxivConfig?.authors || ''}
                                                    onChange={(e) => setNewRadar({
                                                        ...newRadar,
                                                        arxivConfig: {
                                                            ...newRadar.arxivConfig!,
                                                            authors: e.target.value
                                                        }
                                                    })}
                                                    className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-orange-500/50"
                                                    placeholder="e.g. Geoffrey Hinton"
                                                />
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-2 gap-4">
                                            <div>
                                                <label className="block text-xs font-medium text-zinc-400 mb-1">Keywords (Abstract)</label>
                                                <input
                                                    type="text"
                                                    value={newRadar.arxivConfig?.keywords || ''}
                                                    onChange={(e) => setNewRadar({
                                                        ...newRadar,
                                                        arxivConfig: {
                                                            ...newRadar.arxivConfig!,
                                                            keywords: e.target.value
                                                        }
                                                    })}
                                                    className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-orange-500/50"
                                                    placeholder="e.g. reinforcement learning"
                                                />
                                            </div>
                                            <div>
                                                <label className="block text-xs font-medium text-zinc-400 mb-1">Journal Reference</label>
                                                <input
                                                    type="text"
                                                    value={newRadar.arxivConfig?.journalReference || ''}
                                                    onChange={(e) => setNewRadar({
                                                        ...newRadar,
                                                        arxivConfig: {
                                                            ...newRadar.arxivConfig!,
                                                            journalReference: e.target.value
                                                        }
                                                    })}
                                                    className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-orange-500/50"
                                                    placeholder="e.g. CVPR 2024"
                                                />
                                            </div>
                                        </div>
                                    </div>
                                )}

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-zinc-400 mb-1">
                                            Frequency <span className="text-red-500 ml-0.5">*</span>
                                        </label>
                                        <select
                                            value={newRadar.frequency}
                                            onChange={(e) => setNewRadar({ ...newRadar, frequency: e.target.value })}
                                            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                        >
                                            <option>Daily</option>
                                            <option>Weekly</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-zinc-400 mb-1">
                                            Output Media <span className="text-red-500 ml-0.5">*</span>
                                        </label>
                                        <select
                                            value={newRadar.outputMedia}
                                            onChange={(e) => setNewRadar({ ...newRadar, outputMedia: e.target.value })}
                                            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                                        >
                                            <option>Text Digest</option>
                                            <option>Audio Podcast</option>
                                            <option>Visual Dashboard</option>
                                        </select>
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-zinc-400 mb-1">Customize Prompt</label>
                                    <textarea
                                        value={newRadar.customPrompt}
                                        onChange={(e) => setNewRadar({ ...newRadar, customPrompt: e.target.value })}
                                        className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 h-24 resize-none"
                                        placeholder="Specific instructions for the AI on how to filter or summarize updates..."
                                    />
                                </div>
                            </div>

                            <div className="p-6 border-t border-zinc-800 flex justify-end gap-3">
                                <button
                                    onClick={handleCloseModal}
                                    className="px-4 py-2 text-zinc-400 hover:text-white transition-colors text-sm font-medium"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSaveRadar}
                                    disabled={!newRadar.title || newRadar.sources.length === 0}
                                    className={`px-4 py-2 rounded-lg transition-colors text-sm font-medium ${(!newRadar.title || newRadar.sources.length === 0)
                                            ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed'
                                            : 'bg-blue-600 hover:bg-blue-500 text-white'
                                        }`}
                                >
                                    Create Radar
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
};
