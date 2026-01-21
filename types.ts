
export type FileType = 'mp3' | 'mp4' | 'pptx' | 'pdf';

export interface GeneratedFile {
  path: string;
  type: FileType;
  name: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  files?: GeneratedFile[];
  statusUpdates?: string[];
  isThinking?: boolean;
}

export interface AppState {
  messages: Message[];
  isSidebarOpen: boolean;
  isProcessing: boolean;
  status: string;
}
