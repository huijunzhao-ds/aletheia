import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';
import { Dashboard } from './components/Dashboard';
import { Message, RadarItem } from './types';
import { v4 as uuidv4 } from 'uuid';
import { auth } from './firebaseConfig';
import {
  onAuthStateChanged,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  User
} from "firebase/auth";
import { DocumentViewer } from './components/DocumentViewer';

import { ComingSoon } from './components/ComingSoon';
import { RadarItemsList } from './components/RadarItemsList';
import { ResearchRadar } from './components/ResearchRadar';
import { NavBar } from './components/NavBar';

type ViewState = 'dashboard' | 'exploration' | 'radar' | 'projects' | 'radar-chat';

const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentView, setCurrentView] = useState<ViewState>('dashboard');
  const [sessionId, setSessionId] = useState<string>(uuidv4());
  const [threads, setThreads] = useState<{ id: string, title: string, radarId?: string }[]>([]);
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
  const [selectedRadar, setSelectedRadar] = useState<RadarItem | null>(null);
  const [radarItems, setRadarItems] = useState<any[]>([]);
  const [isRadarItemsLoading, setIsRadarItemsLoading] = useState(false);
  const [radars, setRadars] = useState<{ id: string, title: string }[]>([]);
  const [projects, setProjects] = useState<{ id: string, title: string }[]>([]);

  const persistThread = async (id: string, title: string) => {
    // NOTE: Thread persistence to the backend is currently disabled because
    // there is no POST /api/threads endpoint implemented on the server.
    // This function is kept as a no-op to preserve the existing API and
    // can be updated once the corresponding backend route is available.
    return;
  };

  const resetSession = async () => {
    // If current session has legitimate user messages, save it to threads if not already there
    const hasUserMessages = messages.some(m => m.role === 'user');
    if (hasUserMessages) {
      const firstUserMessage = messages.find(m => m.role === 'user')?.content || "New Research";
      if (!threads.find(t => t.id === sessionId)) {
        setThreads(prev => [{ id: sessionId, title: firstUserMessage }, ...prev]);
        await persistThread(sessionId, firstUserMessage);
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

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setLoading(false);
      // Reset view to dashboard on login
      if (currentUser) {
        setCurrentView('dashboard');
      }
    });
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    const fetchGlobalData = async () => {
      if (!user) return;
      try {
        const token = await user.getIdToken();
        // Fetch threads
        const threadsRes = await fetch('/api/threads', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const threadsData = await threadsRes.json();
        if (threadsData.threads) setThreads(threadsData.threads);

        // Fetch radars
        const radarsRes = await fetch('/api/radars', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (radarsRes.ok) {
          const radarsData = await radarsRes.json();
          setRadars(radarsData.map((r: any) => ({ id: r.id, title: r.title })));
        }

        // Projects (placeholder)
        setProjects([{ id: 'proj-1', title: 'Deep Learning Review' }, { id: 'proj-2', title: 'Agentic Workflows' }]);

        setCurrentStatus('');
      } catch (error) {
        console.error("Failed to fetch global data", error);
      }
    };
    if (user) {
      fetchGlobalData();
    }
  }, [user]);

  useEffect(() => {
    if (currentView === 'dashboard' || currentView === 'radar') {
      setIsSidebarOpen(false);
    } else {
      setIsSidebarOpen(true);
    }
  }, [currentView]);

  const handleGoogleSignIn = async () => {
    const provider = new GoogleAuthProvider();
    try {
      await signInWithPopup(auth, provider);
    } catch (error) {
      console.error("Error signing in with Google", error);
    }
  };

  const handleSignOut = () => signOut(auth);

  const handleSelectThread = async (id: string) => {
    setIsProcessing(true);
    setCurrentStatus('Loading research thread...');
    try {
      const token = await user?.getIdToken();
      const response = await fetch(`/api/session/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();

      // Load history messages if present
      if (data.messages) {
        setMessages(data.messages.map((m: any) => ({
          ...m,
          timestamp: new Date(m.timestamp)
        })));

        // Restore documents and active document
        if (data.documents && data.documents.length > 0) {
          setSessionDocuments(data.documents);
          // Auto-open the most recent document
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
      // Only clear status if it wasn't an error
      if (!currentStatus.toLowerCase().includes('failed')) {
        setCurrentStatus('');
      }
    }
  };

  const handleSelectRadar = async (radar: RadarItem) => {
    setSelectedRadar(radar);
    const id = radar.id;
    setCurrentView('radar-chat');
    setIsSidebarOpen(true);

    // Clear previous session state before starting/resuming radar session
    setMessages([{
      id: 'briefing-loading',
      role: 'assistant',
      content: 'Initializing radar workspace...',
      timestamp: new Date()
    }]);
    setSessionDocuments([]);
    setActiveDocument(null);

    try {
      const token = await auth.currentUser?.getIdToken();

      // 1. Fetch briefing and determine scenario
      const briefingResponse = await fetch(`/api/radars/briefing?radar_id=${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      let briefingData = { summary: "", scenario: "new" };
      if (briefingResponse.ok) {
        briefingData = await briefingResponse.json();
      }

      // 2. Fetch threads for this radar specifically to decide if we resume
      const threadsRes = await fetch(`/api/threads?radar_id=${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const threadsData = await threadsRes.json();
      const radarThreads = threadsData.threads || [];

      // Update global threads with new items (deduplicated)
      setThreads(prev => {
        const existingIds = new Set(prev.map(t => t.id));
        const newThreads = radarThreads.filter((t: any) => !existingIds.has(t.id));
        return [...newThreads, ...prev];
      });

      if (briefingData.scenario === 'resuming' && radarThreads.length > 0) {
        // Scenario 2.1: Pickup existing work - Load the latest thread
        const latestThread = radarThreads[0]; // Assuming backend returns sorted by date
        await handleSelectThread(latestThread.id);

        // Prepend the briefing/welcome back message to the existing history
        setMessages(prev => [{
          id: uuidv4(),
          role: 'assistant',
          content: briefingData.summary,
          timestamp: new Date()
        }, ...prev]);
      } else {
        // Scenarios 2.2 and 2.3: New parse or new radar
        setMessages([{
          id: uuidv4(),
          role: 'assistant',
          content: briefingData.summary,
          timestamp: new Date()
        }]);
        setSessionId(uuidv4());
      }

      // 3. Fetch items (papers/artifacts)
      setIsRadarItemsLoading(true);
      const itemsResponse = await fetch(`/api/radars/${id}/items`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (itemsResponse.ok) {
        const items = await itemsResponse.json();
        setRadarItems(items);
      }
    } catch (error) {
      console.error("Error fetching radar details:", error);
      setMessages([{
        id: uuidv4(),
        role: 'assistant',
        content: "I encountered an error trying to initialize this radar. Please try again or check your connection.",
        timestamp: new Date()
      }]);
    } finally {
      setIsRadarItemsLoading(false);
    }
  };

  const handleSyncRadar = async () => {
    if (!selectedRadar || !user) return;

    setIsRadarItemsLoading(true);
    try {
      const token = await user.getIdToken();

      // 1. Trigger the background sync
      const syncResponse = await fetch(`/api/radars/${selectedRadar.id}/sync`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (syncResponse.ok) {
        setMessages(prev => [...prev, {
          id: uuidv4(),
          role: 'assistant',
          content: '_Agent scanning specialized sources for new research papers..._',
          timestamp: new Date()
        }]);

        // 2. Poll/Wait a few seconds for background items to be created
        await new Promise(resolve => setTimeout(resolve, 3000));

        const itemsResponse = await fetch(`/api/radars/${selectedRadar.id}/items`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (itemsResponse.ok) {
          const items = await itemsResponse.json();
          setRadarItems(items);
        }
      }
    } catch (error) {
      console.error("Error syncing radar:", error);
    } finally {
      setIsRadarItemsLoading(false);
    }
  };

  const handleDeleteRadarItem = async (itemId: string) => {
    if (!selectedRadar || !user) return;

    try {
      const token = await user.getIdToken();
      const response = await fetch(`/api/radars/${selectedRadar.id}/items/${itemId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        setRadarItems(prev => prev.filter(item => item.id !== itemId));
      }
    } catch (error) {
      console.error("Error deleting radar item:", error);
    }
  };

  const handleDeleteThread = async (threadId: string) => {
    if (!user) return;
    try {
      const token = await user.getIdToken();
      const response = await fetch(`/api/threads/${threadId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        setThreads(prev => prev.filter(t => t.id !== threadId));
        if (sessionId === threadId) {
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
      }
    } catch (error) {
      console.error("Error deleting thread:", error);
    }
  };

  const handleSaveToExploration = async (item: any) => {
    if (!user) return;
    try {
      const token = await user.getIdToken();
      const response = await fetch('/api/exploration/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          ...item,
          savedAt: new Date().toISOString(),
          sourceRadarId: selectedRadar?.id
        })
      });
      if (response.ok) {
        // Show a brief success toast (using global status for now)
        setCurrentStatus(`Saved "${item.title}" to your exploration.`);
        setTimeout(() => setCurrentStatus(''), 3000);
      }
    } catch (error) {
      console.error("Error saving to exploration:", error);
    }
  };

  const handleSaveToProject = (item: any) => {
    // Selection of project will be implemented later
    console.log("Saving to project - logic to be implemented:", item);
    setCurrentStatus(`Choosing project for "${item.title}" (Coming Soon)`);
    setTimeout(() => setCurrentStatus(''), 3000);
  };

  const handleSendMessage = async (content: string, files: File[] = []) => {
    if ((!content.trim() && files.length === 0) || !user) return;

    // Add current session to threads list if this is the first message
    if (!threads.find(t => t.id === sessionId)) {
      setThreads(prev => [{ id: sessionId, title: content || (files.length > 0 ? `Files: ${files[0].name}...` : "New Research") }, ...prev]);
    }

    // Convert files to base64 for transmission
    const uploadedFiles = await Promise.all(files.map(async (file) => {
      return new Promise<{ name: string, mime_type: string, data: string }>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = (reader.result as string).split(',')[1];
          resolve({
            name: file.name,
            mime_type: file.type,
            data: base64
          });
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

    // Auto-open the last uploaded PDF in the viewer
    const pdfFiles = files.filter(f => f.type === 'application/pdf');
    if (pdfFiles.length > 0) {
      const newDocs = pdfFiles.map(f => ({
        name: f.name,
        url: URL.createObjectURL(f)
      }));
      setSessionDocuments(prev => [...prev, ...newDocs]);
      setActiveDocument(newDocs[newDocs.length - 1]);
    }

    setIsProcessing(true);
    setCurrentStatus(files.length > 0 ? 'Aletheia is analyzing your documents...' : 'Aletheia is initiating research protocol...');

    try {
      // Get the ID token from Firebase (user is guaranteed non-null by the earlier check)
      const token = await user!.getIdToken();

      const response = await fetch('/api/research', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          query: content,
          sessionId: sessionId,
          files: uploadedFiles,
          radarId: currentView === 'radar-chat' ? selectedRadar?.id : null
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


  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-zinc-950">
        <div className="text-white animate-pulse">Initializing Aletheia...</div>
      </div>
    );
  }

  // Login View
  if (!user) {
    return (
      <div className="flex flex-col items-center justify-center w-full h-full min-h-screen bg-[#0a0a14] text-white p-4 relative overflow-hidden">
        {/* Background effects */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-900/20 via-[#0a0a14] to-[#0a0a14]"></div>

        <div className="max-w-md text-center space-y-8 relative z-10">
          <div className="space-y-4">
            <p className="text-zinc-300 text-lg font-normal tracking-wide">
              Live Research Intelligence System
            </p>
            <h1 className="text-6xl md:text-7xl font-medium italic bg-gradient-to-br from-blue-300 via-blue-500 to-blue-600 bg-clip-text text-transparent pb-2" style={{ fontFamily: "'Playfair Display', serif" }}>
              Aletheia
            </h1>
          </div>
          <div className="pt-4">
            <button
              onClick={handleGoogleSignIn}
              className="px-8 py-3 bg-white text-black font-semibold rounded-full hover:bg-zinc-200 transition-all duration-300 transform hover:scale-105 flex items-center gap-2 mx-auto"
            >
              <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" className="w-5 h-5" alt="Google" />
              Sign in with Google
            </button>
          </div>
          <p className="text-zinc-500 text-sm mt-8 font-normal tracking-wide opacity-80">
            Limited spots available. No credit card required.
          </p>
        </div>
      </div>
    );
  }

  const handleDownloadDocument = (doc: { name: string, url: string }) => {
    const link = document.createElement('a');
    link.href = doc.url;
    link.download = doc.name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Filter threads based on context
  const isRadarChat = currentView === 'radar-chat';
  const filteredThreads = isRadarChat
    ? threads.filter(t => t.radarId === selectedRadar?.id)
    : threads.filter(t => !t.radarId);

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
        title='Project Management'
        description="Project Management will enable you to organize your research threads, save artifacts, and collaborate with teams. This feature is in active development."
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


  const radarDocuments = radarItems.map(item => {
    const dateStr = item.timestamp.split('T')[0].replace(/-/g, '');
    const sanitizedTitle = item.title.toLowerCase().replace(/[^a-z0-9]/g, '_').substring(0, 30);
    const isPodcast = selectedRadar?.outputMedia?.toLowerCase().includes('podcast');
    const extension = isPodcast ? 'mp3' : 'md';
    const typeLabel = isPodcast ? 'podcast' : 'digest';
    return {
      id: item.id,
      name: `${dateStr}-${sanitizedTitle}-${typeLabel}.${extension}`,
      url: item.url || '#',
      isRadarAsset: true
    };
  });

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
        documents={isRadarChat ? radarDocuments : sessionDocuments}
        onSelectDocument={isRadarChat ? () => { } : setActiveDocument}
        onDeleteDocument={isRadarChat ? handleDeleteRadarItem : undefined}
        onDownloadDocument={handleDownloadDocument}
        activeDocumentUrl={isRadarChat ? undefined : activeDocument?.url}
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
              onItemClick={(item) => {
                handleSendMessage(`What are the key findings of the paper titled "${item.title}"?`);
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
              onNavigate={(view: string) => setCurrentView(view as ViewState)}
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
    </div>
  );
};

export default App;
