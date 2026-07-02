export interface User {
  id: string;
  username: string;
  role: 'admin' | 'user';
  created_at: string;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  content: string;
  source_name: string;
  document_id: string;
  chunk_id: number;
  score: number;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  sources: string | null; // JSON string or null
  created_at: string;
  
  // Local UI helper
  parsedSources?: Citation[];
}

export interface KnowledgeDocument {
  id: string;
  filename: string;
  file_size: string;
  chunk_count: number;
  uploaded_at: string;
}
