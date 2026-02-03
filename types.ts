
export type FileType = 'mp3' | 'mp4' | 'pptx' | 'pdf';

export interface GeneratedFile {
  path: string;
  type: FileType;
  name: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  timestamp: Date;
  files?: GeneratedFile[];
  statusUpdates?: string[];
  isThinking?: boolean;
}

export interface ArxivConfig {
  categories: string[];
  authors: string[];
  keywords: string[];
  journalReference?: string;
}

export interface RadarItem {
  id: string;
  title: string;
  description: string;
  sources: string[];
  frequency: string;
  outputMedia: string;
  customPrompt?: string;
  arxivConfig?: ArxivConfig;
  lastUpdated: string;
  status: 'active' | 'paused';
  latestSummary?: string;

}
