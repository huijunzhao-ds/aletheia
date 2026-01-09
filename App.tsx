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
    if (!user) {
      return;
    }

    try {
      await fetch('/api/threads', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id,
          title,
          userId: user.uid,
        }),
      });
    } catch (error) {
      console.error('Failed to persist thread', error);
    }
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
      } catch (error) {
        console.error("Failed to fetch threads", error);
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
      if (data.messages && data.messages.length > 0) {
        setMessages(data.messages.map((m: any) => ({
          ...m,
          timestamp: new Date(m.timestamp)
        })));
        setSessionId(id);
      }
    } catch (error) {
      console.error("Failed to load thread", error);
    } finally {
      setIsProcessing(false);
      setCurrentStatus('');
    }
  };

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || !user) return;

    // Add current session to threads list if this is the first message
    if (!threads.find(t => t.id === sessionId)) {
      setThreads(prev => [{ id: sessionId, title: content }, ...prev]);
    }

    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsProcessing(true);
    setCurrentStatus('Aletheia is initiating research protocol...');

    try {
      // Get the ID token from Firebase
      const token = await user.getIdToken();

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
