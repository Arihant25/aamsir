"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Settings,
  Zap,
  Brain,
  Bot,
  BarChart3,
  FileText,
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Clock,
  Save,
  CheckCircle,
} from "lucide-react";
import { api, type ConfigResponse, type StatsResponse } from "@/lib/api";

const strategyInfo: Record<
  string,
  { icon: typeof Zap; label: string; description: string }
> = {
  syntactic: {
    icon: Zap,
    label: "Keyword (BM25)",
    description:
      "Traditional keyword-based search using BM25 scoring. Fast and precise for exact-match queries.",
  },
  semantic: {
    icon: Brain,
    label: "Semantic (Vector)",
    description:
      "Dense vector similarity search using sentence embeddings. Finds conceptually related documents.",
  },
  agentic: {
    icon: Bot,
    label: "Agentic (LLM)",
    description:
      "LLM-powered retrieval using reasoning and tool use. Most capable but requires Ollama.",
  },
};

export default function SettingsPage() {
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [enabled, setEnabled] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [configData, statsData] = await Promise.all([
        api.getConfig(),
        api.getStats(),
      ]);
      setConfig(configData);
      setStats(statsData);
      setEnabled(configData.enabled_strategies);
    } catch {
      // Backend might not be running
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const toggleStrategy = (s: string) => {
    setEnabled((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]
    );
    setSaved(false);
  };

  const saveConfig = async () => {
    setSaving(true);
    try {
      await api.updateConfig({ enabled_strategies: enabled });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      // Handle error
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="border-b border-border bg-surface/80 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Settings</h1>
            <p className="text-sm text-muted">
              Configure retrieval strategies and view system analytics
            </p>
          </div>
          <button
            onClick={saveConfig}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-dark transition-colors shadow-md shadow-primary/25 disabled:opacity-50"
          >
            {saved ? (
              <>
                <CheckCircle className="w-4 h-4" />
                Saved
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                {saving ? "Saving..." : "Save Changes"}
              </>
            )}
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Retrieval Strategies */}
        <section>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Settings className="w-5 h-5 text-primary" />
            Retrieval Strategies
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(strategyInfo).map(
              ([key, { icon: Icon, label, description }]) => {
                const isEnabled = enabled.includes(key);
                const isAvailable =
                  config?.available_strategies.includes(key) ?? false;
                return (
                  <button
                    key={key}
                    onClick={() => toggleStrategy(key)}
                    disabled={!isAvailable}
                    className={`text-left p-5 rounded-xl border-2 transition-all ${
                      isEnabled
                        ? "border-primary bg-primary-light/30 shadow-sm"
                        : "border-border hover:border-primary/30"
                    } ${!isAvailable ? "opacity-50 cursor-not-allowed" : ""}`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div
                        className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          isEnabled
                            ? "bg-primary text-white"
                            : "bg-surface-hover text-muted"
                        }`}
                      >
                        <Icon className="w-5 h-5" />
                      </div>
                      <div
                        className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                          isEnabled
                            ? "border-primary bg-primary"
                            : "border-border"
                        }`}
                      >
                        {isEnabled && (
                          <CheckCircle className="w-3 h-3 text-white" />
                        )}
                      </div>
                    </div>
                    <h3 className="font-medium text-sm mb-1">{label}</h3>
                    <p className="text-xs text-muted leading-relaxed">
                      {description}
                    </p>
                    {!isAvailable && (
                      <p className="text-xs text-warning mt-2">
                        Requires Ollama
                      </p>
                    )}
                  </button>
                );
              }
            )}
          </div>
        </section>

        {/* Model Configuration */}
        <section>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Brain className="w-5 h-5 text-primary" />
            Model Configuration
          </h2>
          <div className="bg-surface border border-border rounded-xl p-5 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-muted mb-1 block">
                  Embedding Model
                </label>
                <div className="px-4 py-2.5 rounded-lg border border-border bg-background text-sm">
                  {config?.embedding_model || "all-MiniLM-L6-v2"}
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-muted mb-1 block">
                  BM25 Top-K Results
                </label>
                <div className="px-4 py-2.5 rounded-lg border border-border bg-background text-sm">
                  {config?.bm25_top_k || 10}
                </div>
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted mb-1 block">
                Semantic Top-K Results
              </label>
              <div className="px-4 py-2.5 rounded-lg border border-border bg-background text-sm">
                {config?.semantic_top_k || 10}
              </div>
            </div>
          </div>
        </section>

        {/* Analytics Dashboard */}
        <section>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary" />
            System Analytics
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4 text-primary" />
                <span className="text-xs text-muted">Documents</span>
              </div>
              <p className="text-3xl font-bold">
                {stats?.total_documents ?? "—"}
              </p>
            </div>
            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <MessageSquare className="w-4 h-4 text-accent" />
                <span className="text-xs text-muted">Queries</span>
              </div>
              <p className="text-3xl font-bold">
                {stats?.total_queries ?? "—"}
              </p>
            </div>
            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-warning" />
                <span className="text-xs text-muted">Avg Response</span>
              </div>
              <p className="text-3xl font-bold">
                {stats
                  ? stats.avg_response_time_ms < 1000
                    ? `${Math.round(stats.avg_response_time_ms)}ms`
                    : `${(stats.avg_response_time_ms / 1000).toFixed(1)}s`
                  : "—"}
              </p>
            </div>
            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <ThumbsUp className="w-4 h-4 text-success" />
                <span className="text-xs text-muted">Helpful</span>
              </div>
              <p className="text-3xl font-bold">
                {stats?.helpful_count ?? "—"}
              </p>
            </div>
            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <ThumbsDown className="w-4 h-4 text-danger" />
                <span className="text-xs text-muted">Not Helpful</span>
              </div>
              <p className="text-3xl font-bold">
                {stats?.not_helpful_count ?? "—"}
              </p>
            </div>
            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="w-4 h-4 text-primary" />
                <span className="text-xs text-muted">Total Feedback</span>
              </div>
              <p className="text-3xl font-bold">
                {stats?.total_feedback ?? "—"}
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
