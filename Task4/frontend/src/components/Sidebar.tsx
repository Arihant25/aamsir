"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  FileText,
  Settings,
  Menu,
  X,
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
  const [mobileOpen, setMobileOpen] = useState(false);

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
    const interval = setInterval(checkHealth, 3_600_000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  return (
    <>
      {/* Mobile hamburger */}
      <button
        className={`fixed top-4 left-4 z-50 p-2.5 rounded-xl bg-surface border border-border shadow-sm lg:hidden transition-all duration-200 ${
          mobileOpen ? "opacity-0 pointer-events-none" : "opacity-100 hover:bg-surface-hover"
        }`}
        onClick={() => setMobileOpen(true)}
        aria-label="Open menu"
      >
        <Menu className="w-5 h-5 text-foreground" />
      </button>

      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-40 lg:hidden animate-fade-in"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`fixed inset-y-0 left-0 w-64 bg-surface border-r border-border-strong flex flex-col z-50 transition-transform duration-300 ease-out ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        } lg:translate-x-0`}
      >
        {/* Brand */}
        <div className="p-5 border-b border-border-strong">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center shrink-0">
                <span className="text-white text-xs font-serif font-medium tracking-wide">A</span>
              </div>
              <div>
                <h1 className="text-base font-serif font-medium text-foreground tracking-tight">AAMSIR</h1>
                <p className="text-[11px] text-muted leading-tight">
                  Intelligent Retrieval
                </p>
              </div>
            </div>
            <button
              className="lg:hidden p-1.5 rounded-lg hover:bg-surface-hover transition-colors"
              onClick={() => setMobileOpen(false)}
              aria-label="Close menu"
            >
              <X className="w-5 h-5 text-muted" />
            </button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-0.5">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/" && pathname.startsWith(item.href));
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm transition-all duration-150 ${
                  isActive
                    ? "bg-primary text-white shadow-sm"
                    : "text-accent hover:bg-surface-hover hover:text-foreground"
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span className={isActive ? "font-medium" : ""}>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-border-strong space-y-2">
          <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-background">
            {online === null ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-warning opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-warning" />
                </span>
                <span className="text-xs text-muted">Connecting…</span>
              </>
            ) : online ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
                </span>
                <span className="text-xs text-muted">System Online</span>
              </>
            ) : (
              <>
                <span className="inline-flex rounded-full h-2 w-2 bg-danger" />
                <span className="text-xs text-danger font-medium">Backend Offline</span>
              </>
            )}
          </div>
          <p className="text-[10px] text-muted/60 px-3">Team 5 — S26CS6.401</p>
        </div>
      </aside>
    </>
  );
}
