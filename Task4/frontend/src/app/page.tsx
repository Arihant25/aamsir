"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send,
  ThumbsUp,
  ThumbsDown,
  FileText,
  Zap,
  Brain,
  Bot,
  ChevronDown,
  ChevronUp,
  Clock,
  Sparkles,
} from "lucide-react";
import Markdown from "react-markdown";
import { api, type SourceDocument } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceDocument[];
  strategies?: string[];
  responseTime?: number;
  feedback?: "helpful" | "not_helpful" | null;
}

const strategyIcons: Record<string, typeof Zap> = {
  syntactic: Zap,
  semantic: Brain,
  agentic: Bot,
};

const strategyLabels: Record<string, string> = {
  syntactic: "Keyword (BM25)",
  semantic: "Semantic (Vector)",
  agentic: "Agentic (LLM)",
};

export default function QueryPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([
    "syntactic",
    "semantic",
  ]);
  const [expandedSources, setExpandedSources] = useState<Set<string>>(
    new Set()
  );
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const toggleStrategy = (s: string) => {
    setSelectedStrategies((prev) => {
      if (prev.includes(s)) {
        // Don't allow deselecting the last strategy
        if (prev.length <= 1) return prev;
        return prev.filter((x) => x !== s);
      }
      return [...prev, s];
    });
  };

  const toggleSources = (msgId: string) => {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      if (next.has(msgId)) next.delete(msgId);
      else next.add(msgId);
      return next;
    });
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    const query = input.trim();
    if (!query || loading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: query,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.query(query, selectedStrategies);
      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: res.answer,
        sources: res.sources,
        strategies: res.strategies_used,
        responseTime: res.response_time_ms,
        feedback: null,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: Message = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content:
          "Sorry, I couldn't process your query. Please make sure the backend server is running and try again.",
        feedback: null,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (
    msgId: string,
    rating: "helpful" | "not_helpful"
  ) => {
    const msg = messages.find((m) => m.id === msgId);
    if (!msg) return;
    const userQuery =
      messages[messages.indexOf(msg) - 1]?.content || "";

    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, feedback: rating } : m))
    );

    try {
      await api.submitFeedback(
        userQuery,
        msg.content,
        rating,
        msg.strategies?.join(",") || ""
      );
    } catch {
      // Silently fail — feedback is non-critical
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="border-b border-border bg-surface/80 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold">Ask AAMSIR</h1>
            <p className="text-sm text-muted">
              Query your documents using natural language
            </p>
          </div>
          {/* Strategy Toggles */}
          <div className="flex items-center gap-2">
            {Object.entries(strategyLabels).map(([key, label]) => {
              const Icon = strategyIcons[key];
              const active = selectedStrategies.includes(key);
              return (
                <button
                  key={key}
                  onClick={() => toggleStrategy(key)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all border ${
                    active
                      ? "bg-primary text-white border-primary shadow-sm"
                      : "bg-surface text-muted border-border hover:border-primary/50"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-20 h-20 rounded-2xl bg-primary-light flex items-center justify-center mb-6">
              <Sparkles className="w-10 h-10 text-primary" />
            </div>
            <h2 className="text-2xl font-semibold mb-2">
              Welcome to AAMSIR
            </h2>
            <p className="text-muted max-w-md mb-8">
              Ask questions about your documents and get accurate, cited
              answers using multiple retrieval strategies.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 max-w-2xl">
              {[
                "What is the leave policy for employees?",
                "How do I submit a travel reimbursement?",
                "What are the graduation requirements?",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => {
                    setInput(q);
                    inputRef.current?.focus();
                  }}
                  className="text-left p-4 rounded-xl border border-border bg-surface hover:bg-surface-hover hover:border-primary/30 transition-all text-sm"
                >
                  <span className="text-muted">{q}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex animate-fade-in-up ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-3xl ${
                msg.role === "user"
                  ? "bg-primary text-white rounded-2xl rounded-br-md px-5 py-3"
                  : "space-y-3 w-full"
              }`}
            >
              {msg.role === "assistant" && (
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0 mt-1">
                    <Bot className="w-4 h-4 text-accent" />
                  </div>
                  <div className="flex-1 space-y-3">
                    {/* Answer */}
                    <div className="bg-surface border border-border rounded-2xl rounded-tl-md px-5 py-4 prose prose-sm max-w-none text-foreground prose-headings:text-foreground prose-strong:text-foreground prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-a:text-primary">
                      <Markdown>{msg.content}</Markdown>
                    </div>

                    {/* Meta bar */}
                    <div className="flex items-center gap-4 px-1">
                      {msg.responseTime != null && (
                        <span className="flex items-center gap-1 text-xs text-muted">
                          <Clock className="w-3 h-3" />
                          {msg.responseTime < 1000
                            ? `${Math.round(msg.responseTime)}ms`
                            : `${(msg.responseTime / 1000).toFixed(1)}s`}
                        </span>
                      )}
                      {msg.strategies && msg.strategies.length > 0 && (
                        <div className="flex items-center gap-1">
                          {msg.strategies.map((s) => {
                            const Icon = strategyIcons[s] || Zap;
                            return (
                              <span
                                key={s}
                                className="flex items-center gap-1 text-xs text-muted bg-surface-hover px-2 py-0.5 rounded-full"
                              >
                                <Icon className="w-3 h-3" />
                                {s}
                              </span>
                            );
                          })}
                        </div>
                      )}

                      {/* Feedback */}
                      <div className="flex items-center gap-1 ml-auto">
                        <button
                          onClick={() => handleFeedback(msg.id, "helpful")}
                          className={`p-1.5 rounded-lg transition-colors ${
                            msg.feedback === "helpful"
                              ? "text-success bg-success/10"
                              : "text-muted hover:text-success hover:bg-success/5"
                          }`}
                        >
                          <ThumbsUp className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() =>
                            handleFeedback(msg.id, "not_helpful")
                          }
                          className={`p-1.5 rounded-lg transition-colors ${
                            msg.feedback === "not_helpful"
                              ? "text-danger bg-danger/10"
                              : "text-muted hover:text-danger hover:bg-danger/5"
                          }`}
                        >
                          <ThumbsDown className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Sources */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div>
                        <button
                          onClick={() => toggleSources(msg.id)}
                          className="flex items-center gap-2 text-xs font-medium text-primary hover:text-primary-dark transition-colors px-1"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          {msg.sources.length} source
                          {msg.sources.length !== 1 ? "s" : ""}
                          {expandedSources.has(msg.id) ? (
                            <ChevronUp className="w-3 h-3" />
                          ) : (
                            <ChevronDown className="w-3 h-3" />
                          )}
                        </button>
                        {expandedSources.has(msg.id) && (
                          <div className="mt-2 space-y-2">
                            {msg.sources.map((src, i) => (
                              <div
                                key={i}
                                className="bg-surface-hover border border-border rounded-xl p-4 text-sm animate-fade-in-up"
                              >
                                <div className="flex items-center justify-between mb-2">
                                  <span className="font-medium text-foreground">
                                    {src.title}
                                  </span>
                                  <span className="text-xs text-muted bg-surface px-2 py-0.5 rounded-full">
                                    {src.strategy} &middot;{" "}
                                    {(src.score * 100).toFixed(0)}%
                                  </span>
                                </div>
                                <p className="text-muted text-xs leading-relaxed">
                                  {src.snippet}
                                </p>
                                <p className="text-[10px] text-muted mt-2">
                                  {src.filename}
                                </p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
              {msg.role === "user" && <p>{msg.content}</p>}
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex justify-start animate-fade-in-up">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0 mt-1">
                <Bot className="w-4 h-4 text-accent" />
              </div>
              <div className="bg-surface border border-border rounded-2xl rounded-tl-md px-5 py-4">
                <div className="flex items-center gap-2 text-muted">
                  <div className="flex gap-1">
                    <span
                      className="w-2 h-2 bg-primary rounded-full animate-pulse-soft"
                      style={{ animationDelay: "0ms" }}
                    />
                    <span
                      className="w-2 h-2 bg-primary rounded-full animate-pulse-soft"
                      style={{ animationDelay: "300ms" }}
                    />
                    <span
                      className="w-2 h-2 bg-primary rounded-full animate-pulse-soft"
                      style={{ animationDelay: "600ms" }}
                    />
                  </div>
                  <span className="text-sm">Searching documents...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-border bg-surface/80 backdrop-blur-sm p-4">
        <form
          onSubmit={handleSubmit}
          className="max-w-4xl mx-auto flex items-end gap-3"
        >
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your documents..."
              rows={1}
              className="w-full resize-none rounded-xl border border-border bg-background px-4 py-3 pr-12 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary placeholder:text-muted"
              style={{
                minHeight: "48px",
                maxHeight: "120px",
                height: "auto",
              }}
              onInput={(e) => {
                const el = e.currentTarget;
                el.style.height = "auto";
                el.style.height = Math.min(el.scrollHeight, 120) + "px";
              }}
            />
          </div>
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="h-12 w-12 rounded-xl bg-primary text-white flex items-center justify-center hover:bg-primary-dark transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-md shadow-primary/25"
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </div>
    </div>
  );
}
