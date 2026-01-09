import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';
import { ResearchMode, Message } from './types';
import { v4 as uuidv4 } from 'uuid';
import { auth } from './firebaseConfig';
import {
  onAuthStateChanged,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  User
} from "firebase/auth";

const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionId, setSessionId] = useState<string>(uuidv4());
  const [threads, setThreads] = useState<{ id: string, title: string }[]>([]);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hello! I am Aletheia. How can I help you today?',
      timestamp: new Date(),
    }
  ]);
  const [mode, setMode] = useState<ResearchMode>(ResearchMode.QUICK);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<string>('');

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
  };

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    const fetchThreads = async () => {
      if (!user) return;
      try {
        const token = await user.getIdToken();
        const response = await fetch('/api/threads', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();
        if (data.threads) {
          setThreads(data.threads);
        }
        // Clear any previous error status related to loading threads
        setCurrentStatus('');
      } catch (error) {
        console.error("Failed to fetch threads", error);
        // Inform the user that loading their thread history failed
        setCurrentStatus('Failed to load your previous threads. Some history may be missing.');
      }
    };
    fetchThreads();
  }, [user]);

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
        setSessionId(id);
      }

      // Restore the research mode used for this session
      if (data.mode) {
        setMode(data.mode as ResearchMode);
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

    const fileListText = files.length > 0 ? ` [Attached: ${files.map(f => f.name).join(', ')}]` : '';
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: content + fileListText,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
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
          mode: mode,
          sessionId: sessionId,
          files: uploadedFiles
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

  return (
    <div className="flex h-screen w-full overflow-hidden bg-zinc-950">
      {user ? (
        <>
          <Sidebar
            isOpen={isSidebarOpen}
            onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
            currentMode={mode}
            onModeChange={setMode}
            messages={messages}
            userName={user.displayName}
            userPhoto={user.photoURL}
            onNewConversation={resetSession}
            threads={threads}
            onSelectThread={handleSelectThread}
          />
          <main className="flex-1 flex flex-col relative h-full">
            <div className="absolute top-4 right-4 z-50 flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900/50 border border-zinc-800 rounded-full backdrop-blur-sm">
                {user.photoURL && (
                  <img src={user.photoURL} alt="Profile" className="w-6 h-6 rounded-full border border-zinc-700" />
                )}
                <span className="text-zinc-300 text-xs font-medium">{user.displayName}</span>
              </div>
              <button
                onClick={handleSignOut}
                className="px-4 py-1.5 bg-zinc-900 text-zinc-400 text-sm rounded-lg hover:text-white transition-colors border border-zinc-800"
              >
                Sign Out
              </button>
            </div>
            <ChatArea
              messages={messages}
              onSendMessage={handleSendMessage}
              isProcessing={isProcessing}
              currentStatus={currentStatus}
            />
          </main>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center w-full h-full bg-zinc-950 text-white p-4">
          <div className="max-w-md text-center space-y-6">
            <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-400 to-purple-600 bg-clip-text text-transparent">
              Aletheia
            </h1>
            <p className="text-zinc-400 text-lg">
              Unlock the future of multimedia research. Sign in to start your journey.
            </p>
            <div className="pt-4">
              <button
                onClick={handleGoogleSignIn}
                className="px-8 py-3 bg-white text-black font-semibold rounded-full hover:bg-zinc-200 transition-all duration-300 transform hover:scale-105 flex items-center gap-2 mx-auto"
              >
                <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" className="w-5 h-5" alt="Google" />
                Sign in with Google
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
