const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export interface SourceDocument {
  doc_id: number;
  title: string;
  filename: string;
  snippet: string;
  score: number;
  strategy: string;
}

export interface QueryResponse {
  answer: string;
  sources: SourceDocument[];
  strategies_used: string[];
  response_time_ms: number;
  query: string;
}

export interface DocumentInfo {
  id: number;
  filename: string;
  original_name: string;
  title: string;
  summary: string;
  file_type: string;
  chunk_count: number;
  uploaded_at: string;
  is_indexed: boolean;
}

export interface ConfigResponse {
  enabled_strategies: string[];
  available_strategies: string[];
  embedding_model: string;
  bm25_top_k: number;
  semantic_top_k: number;
}

export interface StatsResponse {
  total_documents: number;
  total_queries: number;
  total_feedback: number;
  avg_response_time_ms: number;
  helpful_count: number;
  not_helpful_count: number;
}

export interface HealthResponse {
  status: string;
  available_strategies: string[];
  enabled_strategies: string[];
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(error || `Request failed: ${res.status}`);
  }
  return res.json();
}

export function getDocumentDownloadUrl(docId: number): string {
  return `${API_BASE}/documents/${docId}/download`;
}

export const api = {
  health: () => request<HealthResponse>("/health"),

  query: (query: string, strategies: string[], topK: number = 10) =>
    request<QueryResponse>("/query", {
      method: "POST",
      body: JSON.stringify({ query, strategies, top_k: topK }),
    }),

  getDocuments: () => request<DocumentInfo[]>("/documents"),

  getDocument: (id: number) =>
    request<Record<string, unknown>>(`/documents/${id}`),

  uploadDocument: async (file: File): Promise<{ message: string; document: DocumentInfo }> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const error = await res.text();
      throw new Error(error || `Upload failed: ${res.status}`);
    }
    return res.json();
  },

  deleteDocument: (id: number) =>
    request<{ message: string }>(`/documents/${id}`, { method: "DELETE" }),

  submitFeedback: (
    query: string,
    answer: string,
    rating: "helpful" | "not_helpful",
    strategyUsed: string
  ) =>
    request<{ message: string }>("/feedback", {
      method: "POST",
      body: JSON.stringify({
        query,
        answer,
        rating,
        strategy_used: strategyUsed,
      }),
    }),

  getConfig: () => request<ConfigResponse>("/config"),

  updateConfig: (config: { enabled_strategies?: string[] }) =>
    request<{ message: string; enabled_strategies: string[] }>("/config", {
      method: "PUT",
      body: JSON.stringify(config),
    }),

  getStats: () => request<StatsResponse>("/stats"),
};
