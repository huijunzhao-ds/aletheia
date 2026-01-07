
import React, { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatArea } from './components/ChatArea';
import { ResearchMode, Message, GeneratedFile } from './types';
import { v4 as uuidv4 } from 'uuid';

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hello! I am Aletheia, your Multimedia Research Assistant. How can I help you explore academic topics today? You can ask me to find papers, generate lecture audio, or create video summaries.',
      timestamp: new Date(),
    }
  ]);
  const [mode, setMode] = useState<ResearchMode>(ResearchMode.QUICK);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<string>('');

  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return;

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
      // Connect to your local Python backend
      const response = await fetch('/api/research', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: content,
          mode: mode,
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
        // Map backend response files to ensure correct type matching
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
        content: `Connection Error: ${error instanceof Error ? error.message : 'The Python backend on port 8000 is unreachable.'} Please check main.py and CORS settings.`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsProcessing(false);
      setCurrentStatus('');
    }
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-zinc-950">
      <Sidebar
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        currentMode={mode}
        onModeChange={setMode}
        messages={messages}
      />
      <main className="flex-1 flex flex-col relative h-full">
        <ChatArea
          messages={messages}
          onSendMessage={handleSendMessage}
          isProcessing={isProcessing}
          currentStatus={currentStatus}
        />
      </main>
    </div>
  );
};

export default App;
