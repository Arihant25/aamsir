"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  FileText,
  Settings,
  Activity,
  Database,
  AlertCircle,
} from "lucide-react";
import { api } from "@/lib/api";

const navItems = [
  { href: "/", label: "Query", icon: MessageSquare },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const [online, setOnline] = useState<boolean | null>(null);

  const checkHealth = useCallback(async () => {
    try {
      await api.health();
      setOnline(true);
    } catch {
      setOnline(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10_000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-64 bg-surface border-r border-border flex flex-col z-10">
      {/* Logo */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
            <Database className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">AAMSIR</h1>
            <p className="text-xs text-muted">Intelligent Retrieval</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-150 ${
                isActive
                  ? "bg-primary text-white shadow-md shadow-primary/25"
                  : "text-muted hover:bg-surface-hover hover:text-foreground"
              }`}
            >
              <Icon className="w-5 h-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 px-4 py-2">
          {online === null ? (
            <>
              <Activity className="w-4 h-4 text-muted animate-pulse" />
              <span className="text-xs text-muted">Connecting...</span>
            </>
          ) : online ? (
            <>
              <Activity className="w-4 h-4 text-success" />
              <span className="text-xs text-muted">System Online</span>
            </>
          ) : (
            <>
              <AlertCircle className="w-4 h-4 text-danger" />
              <span className="text-xs text-danger">Backend Offline</span>
            </>
          )}
        </div>
        <p className="text-[10px] text-muted px-4 mt-1">
          Team 5 — S26CS6.401
        </p>
      </div>
    </aside>
  );
}
