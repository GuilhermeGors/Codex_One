"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileText,
  MessageSquare,
  BarChart3,
  Settings,
  ShieldAlert,
  Zap,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const navItems = [
  { href: "/", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/documents", icon: FileText, label: "Documents" },
  { href: "/query", icon: MessageSquare, label: "Query" },
  { href: "/analytics", icon: BarChart3, label: "Analytics" },
  { href: "/security", icon: ShieldAlert, label: "Security Intelligence" },
  { href: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-16 flex-col items-center border-r border-border bg-sidebar py-4">
      {/* Logo */}
      <div className="mb-8 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 glow-cyan">
        <Zap className="h-5 w-5 text-primary" />
      </div>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col items-center gap-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Tooltip key={item.href}>
              <TooltipTrigger
                className={`flex h-10 w-10 items-center justify-center rounded-lg transition-all duration-200 ${
                  isActive
                    ? "bg-primary/15 text-primary glow-cyan"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                }`}
                render={<Link href={item.href} />}
              >
                <item.icon className="h-5 w-5" />
              </TooltipTrigger>
              <TooltipContent side="right">
                <p>{item.label}</p>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </nav>

      {/* Status indicator */}
      <div className="mt-auto">
        <Tooltip>
          <TooltipTrigger className="flex h-3 w-3 rounded-full bg-neon-green animate-pulse-neon">
            <span className="sr-only">System status</span>
          </TooltipTrigger>
          <TooltipContent side="right">
            <p>System Online</p>
          </TooltipContent>
        </Tooltip>
      </div>
    </aside>
  );
}
