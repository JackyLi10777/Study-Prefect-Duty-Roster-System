import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { CalendarDays, ClipboardPenLine, Gauge, HeartHandshake, LibraryBig } from "lucide-react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sing Yin Study Prefect Duty Roster",
  description: "Local-first duty roster system for Sing Yin Study Prefects"
};

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: Gauge },
  { href: "/roster", label: "Generate Roster", icon: CalendarDays },
  { href: "/leave", label: "Leave Adjustment", icon: ClipboardPenLine },
  { href: "/audit", label: "Fairness Audit", icon: HeartHandshake },
  { href: "/devotional", label: "Daily Verse", icon: LibraryBig }
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-HK">
      <body>
        <div className="app-shell">
          <aside className="sidebar">
            <div className="mb-8 flex items-center gap-3">
              <Image src="/logo.png" alt="Sing Yin school badge" width={48} height={48} priority />
              <div>
                <div className="text-sm font-semibold text-[color:var(--brand)]">Sing Yin</div>
                <div className="text-xs text-[color:var(--muted)]">Study Prefect Roster</div>
              </div>
            </div>
            <nav className="grid gap-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link className="nav-link" href={item.href} key={item.href}>
                    <Icon aria-hidden size={18} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </aside>
          <main className="main">{children}</main>
        </div>
      </body>
    </html>
  );
}

