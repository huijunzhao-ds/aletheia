
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
      const response = await fetch('http://localhost:8000/api/research', {
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
        throw new Error(`Agent error: ${response.statusText}`);
      }

      const data = await response.json();
      
      // The backend should return { content: string, files: GeneratedFile[] }
      const assistantMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: data.content || "I've completed my analysis.",
        timestamp: new Date(),
        files: data.files || [],
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to contact agent service', error);
      const errorMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: 'I encountered an error connecting to my core processing unit on port 8000. Please ensure your Python backend is running and CORS is enabled.',
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
