"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Upload,
  FileText,
  Trash2,
  Search,
  FileUp,
  CheckCircle,
  AlertCircle,
  X,
  File,
  Clock,
  Hash,
  Layers,
} from "lucide-react";
import { api, type DocumentInfo } from "@/lib/api";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [toast, setToast] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const docs = await api.getDocuments();
      setDocuments(docs);
    } catch {
      showToast("error", "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const showToast = (type: "success" | "error", message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 4000);
  };

  const handleUpload = async (files: FileList | File[]) => {
    setUploading(true);
    const fileArray = Array.from(files);

    for (const file of fileArray) {
      try {
        await api.uploadDocument(file);
        showToast("success", `"${file.name}" uploaded and indexed`);
      } catch {
        showToast("error", `Failed to upload "${file.name}"`);
      }
    }

    setUploading(false);
    fetchDocuments();
  };

  const handleDelete = async (doc: DocumentInfo) => {
    if (!confirm(`Delete "${doc.original_name}"? This cannot be undone.`))
      return;
    try {
      await api.deleteDocument(doc.id);
      setDocuments((prev) => prev.filter((d) => d.id !== doc.id));
      showToast("success", `"${doc.original_name}" deleted`);
    } catch {
      showToast("error", "Failed to delete document");
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files.length > 0) {
      handleUpload(e.dataTransfer.files);
    }
  };

  const filtered = documents.filter(
    (d) =>
      d.original_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const fileTypeIcon = (type: string) => {
    switch (type) {
      case "pdf":
        return <FileText className="w-5 h-5 text-danger" />;
      case "md":
        return <Hash className="w-5 h-5 text-accent" />;
      default:
        return <File className="w-5 h-5 text-primary" />;
    }
  };

  const totalChunks = documents.reduce((sum, d) => sum + d.chunk_count, 0);
  const indexedCount = documents.filter((d) => d.is_indexed).length;

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="border-b border-border glass px-4 sm:px-6 py-4 shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="pl-12 lg:pl-0">
            <h1 className="text-lg sm:text-xl font-semibold">
              Document Management
            </h1>
            <p className="text-xs sm:text-sm text-muted">
              Upload, view, and manage your document corpus
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative flex-1 sm:flex-none">
              <Search className="w-4 h-4 text-muted absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search documents..."
                className="w-full sm:w-56 pl-9 pr-4 py-2 rounded-xl border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50 transition-all duration-200 placeholder:text-muted/50"
              />
            </div>
            <label className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-white text-sm font-medium hover:bg-primary-dark transition-all duration-200 shadow-sm shadow-primary/20 active:scale-95 whitespace-nowrap">
              <Upload className="w-4 h-4" />
              <span className="hidden sm:inline">Upload</span>
              <input
                type="file"
                multiple
                accept=".pdf,.txt,.md,.docx"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files) handleUpload(e.target.files);
                  e.target.value = "";
                }}
              />
            </label>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
        {/* Drop zone */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-2xl p-6 sm:p-8 text-center transition-all duration-300 ${
            dragActive
              ? "border-primary bg-primary-light/50 scale-[1.01]"
              : "border-border hover:border-primary/30"
          }`}
        >
          <FileUp
            className={`w-8 h-8 sm:w-10 sm:h-10 mx-auto mb-3 transition-colors duration-200 ${
              dragActive ? "text-primary" : "text-muted/50"
            }`}
          />
          <p className="text-sm text-muted">
            {uploading
              ? "Uploading and indexing..."
              : "Drag and drop files here, or click Upload above"}
          </p>
          <p className="text-xs text-muted/60 mt-1">
            Supports PDF, TXT, MD files
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-surface border border-border rounded-xl p-3 sm:p-4 border-l-4 border-l-primary">
            <div className="flex items-center gap-2 mb-1">
              <FileText className="w-3.5 h-3.5 text-primary" />
              <p className="text-[10px] sm:text-xs text-muted">Documents</p>
            </div>
            <p className="text-xl sm:text-2xl font-bold">{documents.length}</p>
          </div>
          <div className="bg-surface border border-border rounded-xl p-3 sm:p-4 border-l-4 border-l-accent">
            <div className="flex items-center gap-2 mb-1">
              <Layers className="w-3.5 h-3.5 text-accent" />
              <p className="text-[10px] sm:text-xs text-muted">Chunks</p>
            </div>
            <p className="text-xl sm:text-2xl font-bold">{totalChunks}</p>
          </div>
          <div className="bg-surface border border-border rounded-xl p-3 sm:p-4 border-l-4 border-l-success">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle className="w-3.5 h-3.5 text-success" />
              <p className="text-[10px] sm:text-xs text-muted">Indexed</p>
            </div>
            <p className="text-xl sm:text-2xl font-bold">{indexedCount}</p>
          </div>
        </div>

        {/* Document list */}
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-surface border border-border rounded-xl p-4 flex items-center gap-4"
              >
                <div className="w-10 h-10 rounded-lg bg-surface-hover animate-shimmer" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-48 max-w-full bg-surface-hover animate-shimmer rounded" />
                  <div className="h-3 w-32 max-w-full bg-surface-hover animate-shimmer rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center text-muted py-16">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p className="text-sm">
              {searchQuery
                ? "No documents match your search"
                : "No documents uploaded yet"}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((doc, i) => (
              <div
                key={doc.id}
                className="bg-surface border border-border rounded-xl p-3 sm:p-4 flex items-center gap-3 sm:gap-4 hover:bg-surface-hover hover:shadow-sm hover:-translate-y-px transition-all duration-200 group animate-fade-in-up"
                style={{ animationDelay: `${i * 40}ms` }}
              >
                <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-lg bg-surface-hover flex items-center justify-center shrink-0">
                  {fileTypeIcon(doc.file_type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">
                    {doc.title || doc.original_name}
                  </p>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 mt-1">
                    <span className="text-xs text-muted truncate max-w-32 sm:max-w-none">
                      {doc.original_name}
                    </span>
                    <span className="text-xs text-muted items-center gap-1 hidden sm:flex">
                      <Hash className="w-3 h-3" />
                      {doc.chunk_count} chunks
                    </span>
                    <span className="text-xs text-muted items-center gap-1 hidden sm:flex">
                      <Clock className="w-3 h-3" />
                      {new Date(doc.uploaded_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {doc.is_indexed ? (
                    <span className="flex items-center gap-1 text-[10px] sm:text-xs text-success bg-success/10 px-2 py-1 rounded-full whitespace-nowrap">
                      <CheckCircle className="w-3 h-3" />
                      <span className="hidden sm:inline">Indexed</span>
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[10px] sm:text-xs text-warning bg-warning/10 px-2 py-1 rounded-full whitespace-nowrap">
                      <AlertCircle className="w-3 h-3" />
                      <span className="hidden sm:inline">Pending</span>
                    </span>
                  )}
                  <button
                    onClick={() => handleDelete(doc)}
                    className="p-2 rounded-lg text-muted hover:text-danger hover:bg-danger/5 transition-all duration-200 opacity-0 group-hover:opacity-100 active:scale-90"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div
          className={`fixed bottom-4 left-4 right-4 sm:left-auto sm:right-6 sm:max-w-sm z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-xl animate-slide-in-up text-sm font-medium ${
            toast.type === "success"
              ? "bg-success text-white"
              : "bg-danger text-white"
          }`}
        >
          {toast.type === "success" ? (
            <CheckCircle className="w-4 h-4 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 shrink-0" />
          )}
          <span className="flex-1 truncate">{toast.message}</span>
          <button
            onClick={() => setToast(null)}
            className="shrink-0 opacity-70 hover:opacity-100 transition-opacity"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
