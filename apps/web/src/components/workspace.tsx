"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  ArrowUpRight,
  AudioLines,
  BookOpen,
  Boxes,
  ChartNoAxesCombined,
  ChevronRight,
  CircleHelp,
  Cpu,
  FlaskConical,
  GitCompareArrows,
  History,
  Menu,
  Play,
  Settings2,
  SlidersHorizontal,
  TerminalSquare,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import type { LucideIcon } from "lucide-react";
const navigation: [string, [string, string, LucideIcon][]][] = [
  [
    "Workspace",
    [
      ["/", "Overview", Activity],
      ["/models", "Model explorer", Cpu],
      ["/agents", "Agent explorer", Boxes],
      ["/benchmarks", "Benchmark library", BookOpen],
    ],
  ],
  [
    "Research",
    [
      ["/experiments/new", "Experiment builder", FlaskConical],
      ["/experiments", "Live experiments", AudioLines],
      ["/compare", "Comparison studio", GitCompareArrows],
      ["/replay", "Execution replay", History],
      ["/optimize", "Optimization lab", SlidersHorizontal],
      ["/reports", "Reports", ChartNoAxesCombined],
    ],
  ],
  [
    "Environment",
    [
      ["/settings", "Integrations & settings", Settings2],
      ["/docs", "Documentation", CircleHelp],
    ],
  ],
];
function Navigation({ close }: { close?: () => void }) {
  const path = usePathname();
  return (
    <>
      <Link href="/" className="brand" onClick={close}>
        <span className="brand-name">
          Bench <span>Agents</span>
        </span>
      </Link>
      <nav aria-label="Main navigation">
        {navigation.map(([group, items]) => (
          <div className="nav-group" key={group}>
            <p>{group}</p>
            {items.map(([url, label, Icon]) => (
              <Link
                onClick={close}
                key={url}
                href={url}
                aria-current={path === url ? "page" : undefined}
                className={path === url ? "selected" : ""}
              >
                <Icon size={17} />
                <span>{label}</span>
                {path === url ? <ChevronRight size={14} /> : null}
              </Link>
            ))}
          </div>
        ))}
      </nav>
      <div className="sidebar-foot">
        <Link href="/docs#terminal" className="terminal-nav">
          <TerminalSquare size={16} /> Terminal guide <ArrowUpRight size={13} />
        </Link>
        <small>Local workspace · v0.1.0</small>
      </div>
    </>
  );
}
export function Workspace({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const path = usePathname();
  const label =
    navigation
      .flatMap(([, items]) => items)
      .find(([url]) => url === path)?.[1] ?? "Workspace";
  return (
    <div className="workspace">
      <aside className="sidebar">
        <Navigation />
      </aside>
      <div className="workspace-body">
        <header className="utility">
          <div className="breadcrumbs">
            <Sheet open={open} onOpenChange={setOpen}>
              <SheetTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="mobile-menu"
                  aria-label="Open navigation"
                >
                  <Menu />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="mobile-nav">
                <SheetTitle className="sr-only">
                  Workspace navigation
                </SheetTitle>
                <Navigation close={() => setOpen(false)} />
              </SheetContent>
            </Sheet>
            <span className="crumb-workspace">Local workspace</span>
            <ChevronRight size={14} />
            <span>{label}</span>
          </div>
          <div className="utility-actions">
            <Button asChild variant="outline" size="sm">
              <Link href="/experiments/new">
                <Play size={13} />
                New experiment
              </Link>
            </Button>
          </div>
        </header>
        <main id="main-content">{children}</main>
        <footer className="workspace-footer">
          <span>
            Bench Agents <span className="footer-divider">/</span> Local
            benchmarking workspace
          </span>
          <Link href="/docs">
            Methodology <ArrowUpRight size={12} />
          </Link>
        </footer>
      </div>
    </div>
  );
}
