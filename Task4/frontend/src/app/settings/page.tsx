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
  Cpu,
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
      /* Backend might not be running */
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
      /* handle error */
    } finally {
      setSaving(false);
    }
  };

  const statCards = [
    {
      icon: FileText,
      label: "Documents",
      value: stats?.total_documents ?? "—",
      color: "text-primary",
      border: "border-l-primary",
    },
    {
      icon: MessageSquare,
      label: "Queries",
      value: stats?.total_queries ?? "—",
      color: "text-accent",
      border: "border-l-accent",
    },
    {
      icon: Clock,
      label: "Avg Response",
      value: stats
        ? stats.avg_response_time_ms < 1000
          ? `${Math.round(stats.avg_response_time_ms)}ms`
          : `${(stats.avg_response_time_ms / 1000).toFixed(1)}s`
        : "—",
      color: "text-warning",
      border: "border-l-warning",
    },
    {
      icon: ThumbsUp,
      label: "Helpful",
      value: stats?.helpful_count ?? "—",
      color: "text-success",
      border: "border-l-success",
    },
    {
      icon: ThumbsDown,
      label: "Not Helpful",
      value: stats?.not_helpful_count ?? "—",
      color: "text-danger",
      border: "border-l-danger",
    },
    {
      icon: BarChart3,
      label: "Total Feedback",
      value: stats?.total_feedback ?? "—",
      color: "text-primary",
      border: "border-l-primary",
    },
  ];

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <header className="border-b border-border glass px-4 sm:px-6 py-4 shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="pl-12 lg:pl-0">
            <h1 className="text-lg sm:text-xl font-semibold">Settings</h1>
            <p className="text-xs sm:text-sm text-muted">
              Configure retrieval strategies and view system analytics
            </p>
          </div>
          <button
            onClick={saveConfig}
            disabled={saving}
            className={`flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 shadow-sm active:scale-95 ${
              saved
                ? "bg-success text-white shadow-success/20"
                : "bg-primary text-white hover:bg-primary-dark shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
            }`}
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

      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-8">
        {/* Retrieval Strategies */}
        <section className="animate-fade-in-up">
          <h2 className="text-base sm:text-lg font-semibold mb-4 flex items-center gap-2">
            <Settings className="w-5 h-5 text-primary" />
            Retrieval Strategies
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 sm:gap-4">
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
                    className={`text-left p-4 sm:p-5 rounded-xl border-2 transition-all duration-200 ${
                      isEnabled
                        ? "border-primary bg-primary-light/30 shadow-sm"
                        : "border-border hover:border-primary/30 hover:shadow-sm"
                    } ${
                      !isAvailable
                        ? "opacity-50 cursor-not-allowed"
                        : "active:scale-[0.98]"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div
                        className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors duration-200 ${
                          isEnabled
                            ? "bg-primary text-white"
                            : "bg-surface-hover text-muted"
                        }`}
                      >
                        <Icon className="w-5 h-5" />
                      </div>
                      {/* Toggle indicator */}
                      <div
                        className={`w-10 h-6 rounded-full p-0.5 transition-colors duration-200 ${
                          isEnabled ? "bg-primary" : "bg-border-strong"
                        }`}
                      >
                        <div
                          className={`w-5 h-5 rounded-full bg-white shadow-sm transition-transform duration-200 ${
                            isEnabled ? "translate-x-4" : "translate-x-0"
                          }`}
                        />
                      </div>
                    </div>
                    <h3 className="font-medium text-sm mb-1">{label}</h3>
                    <p className="text-xs text-muted leading-relaxed">
                      {description}
                    </p>
                    {!isAvailable && (
                      <p className="text-xs text-warning mt-2 font-medium">
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
        <section className="animate-fade-in-up [animation-delay:100ms]">
          <h2 className="text-base sm:text-lg font-semibold mb-4 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-primary" />
            Model Configuration
          </h2>
          <div className="bg-surface border border-border rounded-xl p-4 sm:p-5 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-muted mb-1.5 block">
                  Embedding Model
                </label>
                <div className="px-4 py-2.5 rounded-xl border border-border bg-background text-sm font-mono">
                  {config?.embedding_model || "all-MiniLM-L6-v2"}
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-muted mb-1.5 block">
                  BM25 Top-K Results
                </label>
                <div className="px-4 py-2.5 rounded-xl border border-border bg-background text-sm font-mono">
                  {config?.bm25_top_k || 10}
                </div>
              </div>
            </div>
            <div>
              <label className="text-xs font-medium text-muted mb-1.5 block">
                Semantic Top-K Results
              </label>
              <div className="px-4 py-2.5 rounded-xl border border-border bg-background text-sm font-mono">
                {config?.semantic_top_k || 10}
              </div>
            </div>
          </div>
        </section>

        {/* Analytics Dashboard */}
        <section className="animate-fade-in-up [animation-delay:200ms]">
          <h2 className="text-base sm:text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary" />
            System Analytics
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4">
            {statCards.map(({ icon: Icon, label, value, color, border }, i) => (
              <div
                key={label}
                className={`bg-surface border border-border rounded-xl p-4 sm:p-5 border-l-4 ${border} hover:shadow-sm transition-all duration-200 animate-fade-in-up`}
                style={{ animationDelay: `${(i + 3) * 60}ms` }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon className={`w-4 h-4 ${color}`} />
                  <span className="text-xs text-muted">{label}</span>
                </div>
                <p className="text-2xl sm:text-3xl font-bold">{value}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
