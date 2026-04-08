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
    if (!confirm(`Delete "${doc.original_name}"? This cannot be undone.`)) return;
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

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="border-b border-border bg-surface/80 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Document Management</h1>
            <p className="text-sm text-muted">
              Upload, view, and manage your document corpus
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search documents..."
                className="pl-9 pr-4 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 w-64"
              />
            </div>
            <label className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium cursor-pointer hover:bg-primary-dark transition-colors shadow-md shadow-primary/25">
              <Upload className="w-4 h-4" />
              Upload
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

      <div className="flex-1 overflow-y-auto p-6">
        {/* Drop Zone */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-2xl p-8 mb-6 text-center transition-all ${
            dragActive
              ? "border-primary bg-primary-light/50"
              : "border-border hover:border-primary/30"
          }`}
        >
          <FileUp
            className={`w-10 h-10 mx-auto mb-3 ${
              dragActive ? "text-primary" : "text-muted"
            }`}
          />
          <p className="text-sm text-muted">
            {uploading
              ? "Uploading and indexing..."
              : "Drag and drop files here, or click Upload above"}
          </p>
          <p className="text-xs text-muted mt-1">
            Supports PDF, TXT, MD files
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-surface border border-border rounded-xl p-4">
            <p className="text-2xl font-bold">{documents.length}</p>
            <p className="text-xs text-muted">Total Documents</p>
          </div>
          <div className="bg-surface border border-border rounded-xl p-4">
            <p className="text-2xl font-bold">
              {documents.reduce((sum, d) => sum + d.chunk_count, 0)}
            </p>
            <p className="text-xs text-muted">Total Chunks</p>
          </div>
          <div className="bg-surface border border-border rounded-xl p-4">
            <p className="text-2xl font-bold">
              {documents.filter((d) => d.is_indexed).length}
            </p>
            <p className="text-xs text-muted">Indexed</p>
          </div>
        </div>

        {/* Document List */}
        {loading ? (
          <div className="text-center text-muted py-12">
            Loading documents...
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center text-muted py-12">
            <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>
              {searchQuery
                ? "No documents match your search"
                : "No documents uploaded yet"}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((doc) => (
              <div
                key={doc.id}
                className="bg-surface border border-border rounded-xl p-4 flex items-center gap-4 hover:bg-surface-hover transition-colors group"
              >
                <div className="w-10 h-10 rounded-lg bg-surface-hover flex items-center justify-center">
                  {fileTypeIcon(doc.file_type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{doc.title || doc.original_name}</p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-muted">{doc.original_name}</span>
                    <span className="text-xs text-muted flex items-center gap-1">
                      <Hash className="w-3 h-3" />
                      {doc.chunk_count} chunks
                    </span>
                    <span className="text-xs text-muted flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(doc.uploaded_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {doc.is_indexed ? (
                    <span className="flex items-center gap-1 text-xs text-success bg-success/10 px-2 py-1 rounded-full">
                      <CheckCircle className="w-3 h-3" />
                      Indexed
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-xs text-warning bg-warning/10 px-2 py-1 rounded-full">
                      <AlertCircle className="w-3 h-3" />
                      Pending
                    </span>
                  )}
                  <button
                    onClick={() => handleDelete(doc)}
                    className="p-2 rounded-lg text-muted hover:text-danger hover:bg-danger/5 transition-colors opacity-0 group-hover:opacity-100"
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
          className={`fixed bottom-6 right-6 flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg animate-fade-in-up text-sm font-medium ${
            toast.type === "success"
              ? "bg-success text-white"
              : "bg-danger text-white"
          }`}
        >
          {toast.type === "success" ? (
            <CheckCircle className="w-4 h-4" />
          ) : (
            <AlertCircle className="w-4 h-4" />
          )}
          {toast.message}
          <button onClick={() => setToast(null)}>
            <X className="w-4 h-4 opacity-70 hover:opacity-100" />
          </button>
        </div>
      )}
    </div>
  );
}
