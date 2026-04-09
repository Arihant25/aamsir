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
} from "lucide-react";
import Markdown from "react-markdown";
import { prepareWithSegments, measureLineStats } from "@chenglou/pretext";
import { api, getDocumentDownloadUrl, type SourceDocument } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceDocument[];
  strategies?: string[];
  responseTime?: number;
  feedback?: "helpful" | "not_helpful" | null;
  bubbleWidth?: number;
  /** True while the assistant message is still being streamed. */
  pending?: boolean;
}

/** Measure the shrinkwrapped pixel width for a user message bubble. */
function calcBubbleWidth(text: string): number {
  const isMd = window.innerWidth >= 640;
  const fontSize = isMd ? 16 : 14;
  // px-4 (16px) or px-5 (20px) on each side
  const hPad = isMd ? 40 : 32;
  // Available space: 75% of viewport, capped at 672px, less padding
  const maxTextWidth = Math.min(window.innerWidth * 0.75, 672) - hPad;
  const font = `${fontSize}px Segoe UI, Arial, sans-serif`;
  const prepared = prepareWithSegments(text, font);
  const { maxLineWidth } = measureLineStats(prepared, maxTextWidth);
  return maxLineWidth + hPad;
}

const strategyIcons: Record<string, typeof Zap> = {
  syntactic: Zap,
  semantic: Brain,
  agentic: Bot,
};

const strategyLabels: Record<string, string> = {
  syntactic: "Keyword",
  semantic: "Semantic",
  agentic: "Agentic",
};

const suggestions = [
  "What is the leave policy for employees?",
  "How do I submit a travel reimbursement?",
  "What are the graduation requirements?",
];

/** Convert [[doc:ID|Title]] references into standard markdown links. */
function processDocLinks(text: string): string {
  return text.replace(
    /\[\[doc:(\d+)\|([^\]]+)\]\]/g,
    (_, id, title) => `[${title}](${getDocumentDownloadUrl(Number(id))})`
  );
}

/** Custom renderers so all links open in a new tab. */
const markdownComponents = {
  a: ({ href, children, ...rest }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={href} target="_blank" rel="noopener noreferrer" {...rest}>
      {children}
    </a>
  ),
};

function LoadingDots({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 text-muted">
      <div className="flex gap-1.5">
        <span className="w-2 h-2 bg-primary rounded-full animate-pulse-soft" />
        <span className="w-2 h-2 bg-primary rounded-full animate-pulse-soft [animation-delay:200ms]" />
        <span className="w-2 h-2 bg-primary rounded-full animate-pulse-soft [animation-delay:400ms]" />
      </div>
      <span className="text-sm">{label}</span>
    </div>
  );
}

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

  // Only scroll when a new message is appended, not on every streaming token.
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  const toggleStrategy = (s: string) => {
    setSelectedStrategies((prev) => {
      if (prev.includes(s)) {
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

  const handleSubmit = async (e?: React.FormEvent<HTMLFormElement>) => {
    e?.preventDefault();
    const query = input.trim();
    if (!query || loading) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: query,
      bubbleWidth: calcBubbleWidth(query),
    };

    const msgId = `assistant-${Date.now()}`;
    // Add both messages immediately; the assistant stub shows a spinner until
    // tokens arrive. This means the message element stays in the DOM for the
    // entire streaming duration — no fade-in re-animation when streaming ends.
    const assistantStub: Message = {
      id: msgId,
      role: "assistant",
      content: "",
      pending: true,
      feedback: null,
    };

    setMessages((prev) => [...prev, userMsg, assistantStub]);
    setInput("");
    setLoading(true);

    // Local accumulator — avoids stale-closure issues with setState in a loop.
    let draft: Message = assistantStub;

    try {
      for await (const event of api.queryStream(query, selectedStrategies)) {
        if (event.type === "sources") {
          draft = {
            ...draft,
            sources: event.sources,
            strategies: event.strategies_used,
            responseTime: event.response_time_ms,
          };
          setMessages((prev) => prev.map((m) => (m.id === msgId ? { ...draft } : m)));
        } else if (event.type === "token") {
          draft = { ...draft, content: draft.content + event.token };
          setMessages((prev) => prev.map((m) => (m.id === msgId ? { ...draft } : m)));
        } else if (event.type === "done") {
          draft = { ...draft, pending: false };
          setMessages((prev) => prev.map((m) => (m.id === msgId ? { ...draft } : m)));
        }
      }
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId
            ? {
                ...m,
                content:
                  "Sorry, I couldn't process your query. Please make sure the backend server is running and try again.",
                pending: false,
              }
            : m
        )
      );
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
    const userQuery = messages[messages.indexOf(msg) - 1]?.content || "";

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
      /* feedback is non-critical */
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Header */}
      <header className="border-b border-border bg-background px-4 sm:px-6 py-4 shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="pl-12 lg:pl-0">
            <h1 className="text-lg font-serif font-medium text-foreground">Ask AAMSIR</h1>
            <p className="text-xs text-muted" style={{ lineHeight: "1.6" }}>
              Query your documents using natural language
            </p>
          </div>
          {/* Strategy toggles */}
          <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-hide">
            {Object.entries(strategyLabels).map(([key, label]) => {
              const Icon = strategyIcons[key];
              const active = selectedStrategies.includes(key);
              return (
                <button
                  key={key}
                  onClick={() => toggleStrategy(key)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all duration-150 ${
                    active
                      ? "bg-primary text-white shadow-sm"
                      : "bg-surface text-accent border border-border-strong hover:border-primary/30 hover:text-foreground"
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
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Empty state */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mb-8">
              <FileText className="w-7 h-7 text-primary" />
            </div>
            <h2 className="text-2xl sm:text-3xl font-serif font-medium text-foreground mb-3" style={{ lineHeight: "1.2" }}>
              Welcome to AAMSIR
            </h2>
            <p className="text-muted max-w-sm mb-10 text-sm" style={{ lineHeight: "1.6" }}>
              Ask questions about your documents and get accurate, cited answers
              using multiple retrieval strategies.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-2xl w-full">
              {suggestions.map((q, i) => (
                <button
                  key={q}
                  onClick={() => {
                    setInput(q);
                    inputRef.current?.focus();
                  }}
                  className="text-left p-4 rounded-xl border border-border-strong bg-surface hover:bg-surface-hover hover:border-primary/20 transition-all duration-150 text-sm animate-fade-in-up"
                  style={{ animationDelay: `${i * 80}ms` }}
                >
                  <span className="text-accent" style={{ lineHeight: "1.5" }}>{q}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message list — handles both completed and in-progress messages */}
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex animate-fade-in-up ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={
                msg.role === "user"
                  ? "bg-primary text-white rounded-2xl rounded-br-sm px-4 sm:px-5 py-3"
                  : "space-y-3 w-full max-w-3xl"
              }
              style={
                msg.role === "user" && msg.bubbleWidth
                  ? { width: msg.bubbleWidth }
                  : undefined
              }
            >
              {msg.role === "assistant" && (
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-1">
                    <Bot className="w-4 h-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0 space-y-2.5">
                    {/* Answer — shows spinner while pending with no content yet */}
                    <div className="bg-surface border border-border rounded-2xl rounded-tl-sm px-4 sm:px-5 py-4 prose prose-sm max-w-none overflow-hidden wrap-break-word text-foreground prose-headings:text-foreground prose-headings:font-serif prose-strong:text-foreground prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0.5 prose-a:text-primary prose-a:no-underline hover:prose-a:underline">
                      {msg.content ? (
                        <Markdown components={markdownComponents}>
                          {processDocLinks(msg.content)}
                        </Markdown>
                      ) : (
                        <LoadingDots
                          label={msg.sources ? "Generating answer…" : "Searching documents…"}
                        />
                      )}
                    </div>

                    {/* Meta bar — only shown once streaming is complete */}
                    {!msg.pending && (
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 px-1">
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
                                  className="flex items-center gap-1 text-xs text-muted bg-surface-hover px-2 py-0.5 rounded-md border border-border"
                                >
                                  <Icon className="w-3 h-3" />
                                  {s}
                                </span>
                              );
                            })}
                          </div>
                        )}

                        {/* Feedback */}
                        <div className="flex items-center gap-0.5 ml-auto">
                          <button
                            onClick={() => handleFeedback(msg.id, "helpful")}
                            className={`p-1.5 rounded-lg transition-all duration-150 ${
                              msg.feedback === "helpful"
                                ? "text-success bg-success/10"
                                : "text-muted hover:text-success hover:bg-success/10"
                            }`}
                          >
                            <ThumbsUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleFeedback(msg.id, "not_helpful")}
                            className={`p-1.5 rounded-lg transition-all duration-150 ${
                              msg.feedback === "not_helpful"
                                ? "text-danger bg-danger/10"
                                : "text-muted hover:text-danger hover:bg-danger/10"
                            }`}
                          >
                            <ThumbsDown className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Sources — shown as soon as retrieval completes (pending or done) */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div>
                        <button
                          onClick={() => toggleSources(msg.id)}
                          className="flex items-center gap-2 text-xs font-medium text-primary hover:text-primary-dark transition-colors duration-150 px-1"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          {msg.sources.length} source{msg.sources.length !== 1 ? "s" : ""}
                          {expandedSources.has(msg.id) ? (
                            <ChevronUp className="w-3 h-3" />
                          ) : (
                            <ChevronDown className="w-3 h-3" />
                          )}
                        </button>
                        {expandedSources.has(msg.id) && (
                          <div className="mt-2 space-y-2">
                            {msg.sources.map((src, i) => (
                              <a
                                key={i}
                                href={getDocumentDownloadUrl(src.doc_id)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block bg-background border border-border rounded-xl p-3 sm:p-4 text-sm animate-fade-in-up hover:border-border-strong hover:bg-surface-hover transition-all duration-150 overflow-hidden"
                                style={{ animationDelay: `${i * 60}ms` }}
                              >
                                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 mb-2">
                                  <span className="font-medium text-foreground text-xs sm:text-sm truncate">
                                    {src.title}
                                  </span>
                                  <span className="text-[10px] sm:text-xs text-muted bg-surface-hover px-2 py-0.5 rounded-md border border-border whitespace-nowrap w-fit">
                                    {src.strategy} · {(src.score * 100).toFixed(0)}%
                                  </span>
                                </div>
                                <p className="text-muted text-xs leading-relaxed line-clamp-3 wrap-break-word">
                                  {src.snippet}
                                </p>
                                <p className="text-[10px] text-muted/60 mt-2 truncate min-w-0">
                                  {src.filename}
                                </p>
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
              {msg.role === "user" && (
                <p className="text-sm sm:text-base" style={{ lineHeight: "1.5" }}>{msg.content}</p>
              )}
            </div>
          </div>
        ))}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-border bg-background p-3 sm:p-4 shrink-0">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="relative flex items-end gap-2 bg-surface border border-border-strong rounded-2xl p-2 shadow-sm" style={{ boxShadow: "rgba(0,0,0,0.05) 0px 4px 24px" }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your documents…"
              rows={1}
              className="flex-1 resize-none bg-transparent px-3 py-2.5 text-sm focus:outline-none placeholder:text-muted/60 text-foreground"
              style={{
                minHeight: "40px",
                maxHeight: "120px",
                height: "auto",
                lineHeight: "1.6",
              }}
              onInput={(e) => {
                const el = e.currentTarget;
                el.style.height = "auto";
                el.style.height = Math.min(el.scrollHeight, 120) + "px";
              }}
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="shrink-0 h-10 w-10 rounded-xl bg-primary text-white flex items-center justify-center hover:bg-primary-dark transition-all duration-150 disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
