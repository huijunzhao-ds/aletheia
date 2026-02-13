import React, { useState, useEffect, useMemo } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';
import { Dashboard } from './components/Dashboard';
import { Message, RadarItem as RadarConfig } from './types';
import { v4 as uuidv4 } from 'uuid';
import { auth } from './firebaseConfig';
import {
    GoogleAuthProvider,
    signOut,
} from "firebase/auth";
import { DocumentViewer } from './components/DocumentViewer';

import { ComingSoon } from './components/ComingSoon';
import { RadarItemsList } from './components/RadarItemsList';
import { ResearchRadar } from './components/ResearchRadar';
import { NavBar } from './components/NavBar';
import { AddDocumentModal } from './components/AddDocumentModal';

import { useAuth } from './hooks/useAuth';
import { useThreads } from './hooks/useThreads';
import { useRadars } from './hooks/useRadars';
import { useExploration } from './hooks/useExploration';

type ViewState = 'dashboard' | 'exploration' | 'radar' | 'projects' | 'radar-chat';

const App: React.FC = () => {
    // Hooks
    const { user, loading, signInWithGoogle, logout } = useAuth();

    const {
        threads,
        fetchThreads,
        deleteThread,
        setThreads
    } = useThreads(user);

    const {
        radars,
        items: radarItems,
        loadingItems: isRadarItemsLoading,
        fetchRadars,
        fetchRadarItems,
        syncRadar,
        deleteItem: deleteRadarItem,
        setItems: setRadarItems
    } = useRadars(user);

    const {
        items: explorationItems,
        fetchItems: fetchExplorationItems,
        saveItem: saveExplorationItem,
        deleteItem: deleteExplorationItem,
        archiveItem: archiveExplorationItem,
        manualAdd: manualAddExploration,
        setItems: setExplorationItems
    } = useExploration(user);

    // Local UI State
    const [currentView, setCurrentView] = useState<ViewState>('dashboard');
    const [sessionId, setSessionId] = useState<string>(uuidv4());

    // Note: messages are ephemeral session state, not persisted threads (yet)
    const [messages, setMessages] = useState<Message[]>([
        {
            id: 'welcome',
            role: 'assistant',
            content: 'Hello! I am Aletheia. How can I help you today?',
            timestamp: new Date(),
        }
    ]);

    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [isProcessing, setIsProcessing] = useState(false);
    const [currentStatus, setCurrentStatus] = useState<string>('');

    const [activeDocument, setActiveDocument] = useState<{ url: string, name: string } | null>(null);
    const [sessionDocuments, setSessionDocuments] = useState<{ name: string, url: string }[]>([]);

    const [selectedRadar, setSelectedRadar] = useState<RadarConfig | null>(null);
    const [projects, setProjects] = useState<{ id: string, title: string }[]>([]);

    // Modal State
    const [isAddDocModalOpen, setIsAddDocModalOpen] = useState(false);

    const resetSession = async () => {
        // If current session has legitimate user messages, save it to threads if not already there
        const hasUserMessages = messages.some(m => m.role === 'user');
        if (hasUserMessages) {
            const firstUserMessage = messages.find(m => m.role === 'user')?.content || "New Research";
            if (!threads.find(t => t.id === sessionId)) {
                setThreads(prev => [{ id: sessionId, title: firstUserMessage }, ...prev]);
                // await persistThread(sessionId, firstUserMessage); // Disabled on backend
            }
        }

        setSessionId(uuidv4());
        setMessages([{
            id: 'welcome',
            role: 'assistant',
            content: 'Starting a new research thread. How can I help?',
            timestamp: new Date(),
        }]);
        setActiveDocument(null);
        setSessionDocuments([]);
    };

    // Initial Data Fetch
    useEffect(() => {
        if (user) {
            // Load initial View data (Dashboard -> Exploration threads)
            fetchThreads('exploration');
            fetchRadars();
            fetchExplorationItems();

            // Projects placeholder
            setProjects([{ id: 'proj-1', title: 'Deep Learning Review' }, { id: 'proj-2', title: 'Agentic Workflows' }]);
            setCurrentStatus('');
        }
    }, [user, fetchThreads, fetchRadars, fetchExplorationItems]);

    // View Change Effects
    useEffect(() => {
        if (currentView === 'dashboard' || currentView === 'radar') {
            setIsSidebarOpen(false);
        } else {
            setIsSidebarOpen(true);
        }

        // Refresh threads when switching major contexts
        const refreshViewThreads = async () => {
            if (!user) return;

            let agentType = 'exploration';
            if (currentView === 'projects') agentType = 'projects';
            // if radar-chat, handleSelectRadar handles it usually

            if (currentView !== 'radar-chat') {
                fetchThreads(agentType);
            }
        };
        refreshViewThreads();
    }, [currentView, user, fetchThreads]);

    // Filter threads based on context
    const isRadarChat = currentView === 'radar-chat';
    const filteredThreads = useMemo(() => {
        return isRadarChat
            ? threads.filter(t => t.radarId === selectedRadar?.id)
            : (currentView === 'exploration' ? threads.filter(t => !t.radarId) : []);
    }, [isRadarChat, currentView, threads, selectedRadar?.id]);

    // Derived Documents
    const radarDocuments = useMemo(() => radarItems.map(item => {
        const isSummary = !!item.parent;
        const dateStr = item.timestamp ? item.timestamp.split('T')[0].replace(/-/g, '') : '20260201';
        const sanitizedTitle = (item.title || 'summary').toLowerCase().replace(/[^a-z0-9]/g, '_').substring(0, 30);

        let extension = 'md';
        let assetType = 'markdown';

        if (item.asset_type === 'audio' || (item.asset_url && item.asset_url.endsWith('.mp3'))) {
            extension = 'mp3';
            assetType = 'audio';
        }

        const typeLabel = assetType === 'audio' ? 'podcast' : 'digest';

        let downloadUrl = item.asset_url || item.url || '#';
        if (assetType === 'markdown' && !item.asset_url && item.summary) {
            const markdownContent = `# ${item.title}\n\n${item.summary}`;
            downloadUrl = `data:text/markdown;charset=utf-8,${encodeURIComponent(markdownContent)}`;
        }

        return {
            id: item.id,
            name: `${dateStr}-${sanitizedTitle}-${typeLabel}.${extension}`,
            url: downloadUrl,
            isRadarAsset: true,
            assetType: assetType,
            summary: item.summary,
            title: item.title
        };
    }), [radarItems]);

    const explorationDocs = useMemo(() => explorationItems.map(item => {
        const url = item.localAssetPath || item.url || item.pdf_url || '#';
        let name = item.title || "Untitled Paper";
        const ext = item.localAssetType || (url.endsWith('.pdf') ? 'pdf' : 'html');
        if (!name.toLowerCase().endsWith(`.${ext}`)) {
            name = `${name}.${ext}`;
        }

        return {
            id: item.id,
            name: name,
            url: url,
            isRadarAsset: false,
            isArchived: item.isArchived || false,
            summary: item.summary,
            title: item.title
        };
    }), [explorationItems]);


    // Handlers
    const handleSignOut = () => logout();

    const handleSelectThread = async (id: string, overrideAgentType?: string) => {
        setIsProcessing(true);
        setCurrentStatus('Loading research thread...');
        try {
            const token = await user?.getIdToken();
            let agentType = overrideAgentType || 'exploration';
            if (!overrideAgentType) {
                if (currentView === 'projects') agentType = 'projects';
                if (currentView === 'radar-chat') agentType = 'radar';
            }

            const response = await fetch(`/api/session/${id}?agent_type=${agentType}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await response.json();

            if (data.messages) {
                setMessages(data.messages.map((m: any) => ({
                    ...m,
                    timestamp: new Date(m.timestamp)
                })));

                if (data.documents && data.documents.length > 0) {
                    setSessionDocuments(data.documents);
                    setActiveDocument(data.documents[data.documents.length - 1]);
                } else {
                    setSessionDocuments([]);
                    setActiveDocument(null);
                }
                setSessionId(id);
            }
        } catch (error) {
            console.error("Failed to load thread", error);
            setCurrentStatus('Failed to load the selected thread. Please try again.');
        } finally {
            setIsProcessing(false);
            if (!currentStatus.toLowerCase().includes('failed')) {
                setCurrentStatus('');
            }
        }
    };

    const handleSelectRadar = async (radar: RadarConfig) => {
        setSelectedRadar(radar);
        const id = radar.id;
        setCurrentView('radar-chat');
        setIsSidebarOpen(true);

        setMessages([{
            id: 'briefing-loading',
            role: 'assistant',
            content: 'Initializing radar workspace...',
            timestamp: new Date()
        }]);
        setSessionDocuments([]);
        setActiveDocument(null);

        if (!user) {
            setMessages([{
                id: uuidv4(),
                role: 'assistant',
                content: 'You must be signed in to access this radar. Please sign in and try again.',
                timestamp: new Date()
            }]);
            return;
        }

        try {
            const token = await user.getIdToken();

            // 1. Fetch briefing
            const briefingResponse = await fetch(`/api/radars/briefing?radar_id=${id}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            let briefingData = { summary: "", scenario: "new" };
            if (briefingResponse.ok) {
                briefingData = await briefingResponse.json();
            }

            // 2. Fetch Radar Threads
            const radarThreads = await fetchThreads('radar', id);
            // NOTE: useThreads replaces explicit list. 
            // If we need to preserve other threads (which are filtered out anyway), this is fine.

            if (briefingData.scenario === 'resuming' && radarThreads && radarThreads.length > 0) {
                // Scenario 2.1: Pickup existing work
                const latestThread = radarThreads[0];
                await handleSelectThread(latestThread.id, 'radar');
            } else {
                // Scenarios 2.2 and 2.3: New
                setMessages([{
                    id: uuidv4(),
                    role: 'assistant',
                    content: briefingData.summary,
                    timestamp: new Date()
                }]);
                setSessionId(uuidv4());
            }

            // 3. Fetch Items
            fetchRadarItems(id);

        } catch (error) {
            console.error("Error fetching radar details:", error);
            setMessages([{
                id: uuidv4(),
                role: 'assistant',
                content: "I encountered an error trying to initialize this radar. Please try again or check your connection.",
                timestamp: new Date()
            }]);
        }
    };

    const handleSyncRadar = async () => {
        if (!selectedRadar || !user) return;

        setMessages(prev => [...prev, {
            id: uuidv4(),
            role: 'assistant',
            content: '_Agent scanning specialized sources for new research papers..._',
            timestamp: new Date()
        }]);

        await syncRadar(selectedRadar.id, radarItems.length, (msg: string) => {
            setMessages(prev => [...prev, {
                id: uuidv4(),
                role: 'assistant',
                content: msg,
                timestamp: new Date()
            }]);
        });
    };

    const handleDeleteRadarItem = async (itemId: string) => {
        if (!selectedRadar) return;
        deleteRadarItem(selectedRadar.id, itemId);
    };

    const handleDeleteThread = async (threadId: string) => {
        let agentType = 'exploration';
        if (currentView === 'projects') agentType = 'projects';
        if (currentView === 'radar-chat') agentType = 'radar';

        const success = await deleteThread(threadId, agentType);
        if (success && sessionId === threadId) {
            setSessionId(uuidv4());
            setMessages([{
                id: 'welcome',
                role: 'assistant',
                content: 'Starting a new research thread. How can I help?',
                timestamp: new Date(),
            }]);
            setActiveDocument(null);
            setSessionDocuments([]);
        }
    };

    const handleSaveToExploration = async (item: any) => {
        setMessages(prev => [...prev, {
            id: uuidv4(),
            role: 'assistant',
            content: `_Downloading "${item.title}" to Exploration..._`,
            timestamp: new Date()
        }]);

        const success = await saveExplorationItem(item, selectedRadar?.id);

        if (success) {
            setCurrentStatus(`Saved "${item.title}" to your exploration.`);
            setTimeout(() => setCurrentStatus(''), 3000);
            setMessages(prev => [...prev, {
                id: uuidv4(),
                role: 'assistant',
                content: `**Download completed.** \n\nPlease check "To Review" in the Exploration view.`,
                timestamp: new Date()
            }]);
        } else {
            setMessages(prev => [...prev, {
                id: uuidv4(),
                role: 'assistant',
                content: `Failed to save "${item.title}". Please try again.`,
                timestamp: new Date()
            }]);
        }
    };

    const handleSaveToProject = async (item: any) => {
        if (!user) return;
        try {
            const token = await user.getIdToken();
            const payload = {
                title: item.title || item.name,
                summary: item.summary,
                url: item.url,
                source: 'Exploration'
            };

            const response = await fetch('/api/projects/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                setMessages(prev => [...prev, {
                    id: uuidv4(),
                    role: 'assistant',
                    content: `Saved **${payload.title}** to Projects.`,
                    timestamp: new Date()
                }]);
            }
        } catch (error) {
            console.error("Error saving to project:", error);
        }
    };

    const handleArchiveExplorationItem = async (doc: any, archived: boolean) => {
        if (doc.id) {
            archiveExplorationItem(doc.id, archived);
        }
    };

    const handleDeleteExplorationItem = async (id: string) => {
        if (window.confirm("Are you sure you want to delete this specific article?")) {
            deleteExplorationItem(id);
        }
    };

    const handleManualAddExploration = async (mode: 'url' | 'upload', title: string, url: string, file: File | null) => {
        const success = await manualAddExploration(mode, title, url, file || undefined);

        if (success) {
            setCurrentStatus('Item added successfully');
            setTimeout(() => setCurrentStatus(''), 2000);
            return true;
        } else {
            setCurrentStatus('Failed to add item');
            return false;
        }
    };

    // NOTE: handleSendMessage is largely UI and API interaction for chat.
    // It could be a hook `useChat` but it interacts with session state deeply.
    // I'll keep it here for now to avoid over-refactoring.
    const handleSendMessage = async (content: string, files: File[] = []) => {
        if ((!content.trim() && files.length === 0) || !user) return;

        if (!threads.find(t => t.id === sessionId)) {
            // Optimistic add to thread list
            setThreads(prev => [{ id: sessionId, title: content || (files.length > 0 ? `Files: ${files[0].name}...` : "New Research"), radarId: selectedRadar?.id }, ...prev]);
        }

        // Convert files
        const uploadedFiles = await Promise.all(files.map(async (file) => {
            return new Promise<{ name: string, mime_type: string, data: string }>((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => {
                    const base64 = (reader.result as string).split(',')[1];
                    resolve({ name: file.name, mime_type: file.type, data: base64 });
                };
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
        }));

        const userMessage: Message = {
            id: uuidv4(),
            role: 'user',
            content: content,
            timestamp: new Date(),
            files: files.map(f => ({
                path: URL.createObjectURL(f),
                type: f.name.endsWith('.pdf') ? 'pdf' : (f.type.includes('audio') ? 'mp3' : f.type.includes('video') ? 'mp4' : 'pptx'),
                name: f.name
            }))
        };

        setMessages(prev => [...prev, userMessage]);

        // Auto-open PDF
        const pdfFiles = files.filter(f => f.type === 'application/pdf');
        if (pdfFiles.length > 0) {
            const newDocs = pdfFiles.map(f => ({ name: f.name, url: URL.createObjectURL(f) }));
            setSessionDocuments(prev => [...prev, ...newDocs]);
            setActiveDocument(newDocs[newDocs.length - 1]);
        }

        setIsProcessing(true);
        setCurrentStatus(files.length > 0 ? 'Aletheia is analyzing your documents...' : 'Aletheia is initiating research protocol...');

        try {
            const token = await user!.getIdToken();
            const response = await fetch('/api/research', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({
                    query: content,
                    sessionId: sessionId,
                    files: uploadedFiles,
                    radarId: currentView === 'radar-chat' ? selectedRadar?.id : null,
                    activeDocumentUrl: (!isRadarChat && activeDocument) ? activeDocument.url : null,
                    agent_type: currentView === 'radar-chat' ? 'radar' : (currentView === 'projects' ? 'projects' : 'exploration')
                }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown backend error' }));
                throw new Error(errorData.detail || `Agent error: ${response.statusText}`);
            }

            const data = await response.json();
            const assistantMessage: Message = {
                id: uuidv4(),
                role: 'assistant',
                content: data.content || "Research synthesis complete.",
                timestamp: new Date(),
                files: data.files?.map((f: any) => ({
                    path: f.path,
                    type: f.type as any,
                    name: f.name
                })) || [],
            };

            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            console.error('Failed to contact agent service', error);
            const errorMessage: Message = {
                id: uuidv4(),
                role: 'assistant',
                content: `Connection Error: ${error instanceof Error ? error.message : 'The Python backend is unreachable.'}`,
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsProcessing(false);
            setCurrentStatus('');
        }
    };

    const handleDownloadDocument = (doc: { name: string, url: string }) => {
        const link = document.createElement('a');
        link.href = doc.url;
        link.download = doc.name;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handleSelectRadarAsset = async (doc: any) => {
        let content = '';
        let files: any[] = [];

        if (doc.assetType === 'audio') {
            content = `## 🎧 ${doc.title}\n\n**Audio Podcast Summary**\n\n${doc.summary}\n\n---\n*Listen to the AI-generated podcast below:*`;
            files = [{ path: doc.url, type: 'mp3', name: doc.name }];
        } else if (doc.assetType === 'markdown') {
            if (doc.url && doc.url.startsWith('http')) {
                try {
                    const response = await fetch(doc.url);
                    if (response.ok) {
                        content = await response.text();
                    } else {
                        content = `# ${doc.title}\n\n${doc.summary}`;
                    }
                } catch (error) {
                    content = `# ${doc.title}\n\n${doc.summary}`;
                }
            } else {
                content = `# ${doc.title}\n\n${doc.summary}`;
            }
        } else if (doc.assetType === 'pdf') {
            content = `## 📄 ${doc.title}\n\n**Abstract:**\n\n${doc.summary}`;
            files = [{ path: doc.url, type: 'pdf', name: doc.name }];
        } else {
            content = `### ${doc.title}\n\n${doc.summary}`;
        }

        const newMessage: Message = {
            id: uuidv4(),
            role: 'assistant',
            content: content,
            timestamp: new Date(),
            files: files
        };
        setMessages(prev => [...prev, newMessage]);
    };

    const handleNavigate = async (view: string) => {
        if (view === currentView) return;
        if (view === 'exploration' && (currentView === 'radar-chat' || selectedRadar)) {
            resetSession();
            setSelectedRadar(null);
        }
        setCurrentView(view as ViewState);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-screen bg-zinc-950">
                <div className="text-white animate-pulse">Initializing Aletheia...</div>
            </div>
        );
    }

    if (!user) {
        return (
            <div className="flex flex-col items-center justify-center w-full h-full min-h-screen bg-[#0a0a14] text-white p-4 relative overflow-hidden">
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-900/20 via-[#0a0a14] to-[#0a0a14]"></div>
                <div className="max-w-md text-center space-y-8 relative z-10">
                    <div className="space-y-4">
                        <p className="text-zinc-300 text-lg font-normal tracking-wide">Live Research Intelligence System</p>
                        <h1 className="text-6xl md:text-7xl font-medium italic bg-gradient-to-br from-blue-300 via-blue-500 to-blue-600 bg-clip-text text-transparent pb-2" style={{ fontFamily: "'Playfair Display', serif" }}>
                            Aletheia
                        </h1>
                    </div>
                    <div className="pt-4">
                        <button
                            onClick={signInWithGoogle}
                            className="px-8 py-3 bg-white text-black font-semibold rounded-full hover:bg-zinc-200 transition-all duration-300 transform hover:scale-105 flex items-center gap-2 mx-auto"
                        >
                            <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" className="w-5 h-5" alt="Google" />
                            Sign in with Google
                        </button>
                    </div>
                    <p className="text-zinc-500 text-sm mt-8 font-normal tracking-wide opacity-80">Limited spots available. No credit card required.</p>
                </div>
            </div>
        );
    }

    // Dashboard View
    if (currentView === 'dashboard') {
        return (
            <Dashboard
                onNavigate={(view: string) => setCurrentView(view as ViewState)}
                userPhoto={user?.photoURL}
                userName={user?.displayName}
                onSignOut={handleSignOut}
                isSidebarOpen={isSidebarOpen}
                onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
                messages={[]}
                onNewConversation={resetSession}
                threads={filteredThreads}
                onSelectThread={handleSelectThread}
                onDeleteThread={handleDeleteThread}
                documents={[]}
                onSelectDocument={setActiveDocument}
                onDeleteDocument={() => { }}
                onDownloadDocument={handleDownloadDocument}
                activeDocumentUrl={activeDocument?.url}
            />
        );
    }

    // Research Radar View
    if (currentView === 'radar') {
        return (
            <ResearchRadar
                onNavigate={(view: string) => setCurrentView(view as ViewState)}
                userPhoto={user?.photoURL}
                userName={user?.displayName}
                onSignOut={handleSignOut}
                isSidebarOpen={isSidebarOpen}
                onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
                messages={[]}
                onNewConversation={resetSession}
                threads={filteredThreads}
                onSelectThread={handleSelectThread}
                onDeleteThread={handleDeleteThread}
                documents={[]}
                onSelectDocument={setActiveDocument}
                onDeleteDocument={() => { }}
                onDownloadDocument={handleDownloadDocument}
                activeDocumentUrl={activeDocument?.url}
                onSelectRadar={handleSelectRadar}
            />
        );
    }

    // Coming Soon Views (Projects)
    if (currentView === 'projects') {
        return (
            <ComingSoon
                title='Research Projects'
                description="Aletheia can assist you working on research projects, from preparing for a presentation to writing a paper draft. The feature will come soon. Stay tuned."
                onNavigate={(view: string) => setCurrentView(view as ViewState)}
                userPhoto={user?.photoURL}
                userName={user?.displayName}
                onSignOut={handleSignOut}
                isSidebarOpen={isSidebarOpen}
                onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
                messages={messages}
                onNewConversation={resetSession}
                threads={filteredThreads}
                onSelectThread={handleSelectThread}
                onDeleteThread={handleDeleteThread}
                documents={sessionDocuments}
                onSelectDocument={setActiveDocument}
                onDeleteDocument={() => { }}
                onDownloadDocument={handleDownloadDocument}
                activeDocumentUrl={activeDocument?.url}
            />
        );
    }

    return (
        <div className="flex h-screen w-full overflow-hidden bg-zinc-950">
            <Sidebar
                isOpen={isSidebarOpen}
                onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
                messages={messages}
                userName={user.displayName}
                userPhoto={user.photoURL}
                onNewConversation={resetSession}
                threads={filteredThreads}
                onSelectThread={handleSelectThread}
                onDeleteThread={handleDeleteThread}
                documents={isRadarChat ? radarDocuments : [...explorationDocs, ...sessionDocuments]}
                onSelectDocument={isRadarChat ? handleSelectRadarAsset : setActiveDocument}
                onDeleteDocument={isRadarChat ? handleDeleteRadarItem : handleDeleteExplorationItem}
                onDownloadDocument={handleDownloadDocument}
                onArchiveDocument={!isRadarChat ? handleArchiveExplorationItem : undefined}
                onSaveToProject={handleSaveToProject}
                activeDocumentUrl={isRadarChat ? undefined : activeDocument?.url}
                onAddDocument={() => setIsAddDocModalOpen(true)}
            />
            <main className="flex-1 flex overflow-hidden relative">
                {!isSidebarOpen && (
                    <button
                        onClick={() => setIsSidebarOpen(true)}
                        className="absolute bottom-4 left-4 z-50 p-2 bg-zinc-900 border border-zinc-800 rounded-lg text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all shadow-lg animate-in slide-in-from-left duration-300"
                        title="Show Sidebar"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                        </svg>
                    </button>
                )}
                {isRadarChat && (
                    <div className="w-[540px] h-full flex flex-col border-r border-zinc-800 animate-in slide-in-from-left duration-500">
                        <RadarItemsList
                            items={radarItems}
                            isLoading={isRadarItemsLoading}
                            onRefresh={handleSyncRadar}
                            onDeleteItem={handleDeleteRadarItem}
                            onSaveToExploration={handleSaveToExploration}
                            onSaveToProject={handleSaveToProject}
                            outputMedia={selectedRadar?.outputMedia || 'Insight Digest'}
                            radarName={selectedRadar?.title}
                            onItemClick={(item) => {
                                const doc = radarDocuments.find(d => d.id === item.id);
                                if (doc) {
                                    handleSelectRadarAsset(doc);
                                }
                            }}
                        />
                    </div>
                )}
                {!isRadarChat && activeDocument && (
                    <div className="flex-1 h-full flex flex-col min-w-0">
                        <DocumentViewer
                            url={activeDocument.url}
                            name={activeDocument.name}
                            onClose={() => setActiveDocument(null)}
                        />
                    </div>
                )}
                <div className={`flex flex-col relative h-full border-l border-zinc-800 transition-all duration-500 ease-in-out ${((!isRadarChat && activeDocument) || isRadarChat) ? 'flex-1 min-w-0' : 'w-full'}`}>
                    <div className="absolute top-4 right-4 z-50">
                        <NavBar
                            currentView={currentView}
                            onNavigate={handleNavigate}
                            userPhoto={user?.photoURL}
                            userName={user?.displayName}
                            onSignOut={handleSignOut}
                        />
                    </div>
                    <ChatArea
                        messages={messages}
                        onSendMessage={handleSendMessage}
                        isProcessing={isProcessing}
                        currentStatus={currentStatus}
                        onFileClick={(file) => {
                            if (file.type === 'pdf' && !isRadarChat) {
                                setActiveDocument({
                                    url: file.path,
                                    name: file.name
                                });
                            }
                        }}
                        userPhoto={user?.photoURL}
                    />
                </div>
            </main>

            <AddDocumentModal
                isOpen={isAddDocModalOpen}
                onClose={() => setIsAddDocModalOpen(false)}
                onAdd={handleManualAddExploration}
            />
        </div>
    );
};

export default App;
