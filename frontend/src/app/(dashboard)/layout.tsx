"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { 
  Database, 
  MessageSquare, 
  LayoutDashboard, 
  BrainCircuit, 
  Sliders, 
  LogOut,
  ChevronRight
} from "lucide-react";
import { useAuthStore } from "@/stores/authStore";
import styles from "./layout.module.css";

type NavLink = { href: string; label: string; icon: React.ComponentType<any> };

const sideLinks: NavLink[] = [
  { href: "/connections",   label: "Connections", icon: Database },
  { href: "/explore",       label: "Explore (Chat)", icon: MessageSquare },
  { href: "/dashboards",    label: "Dashboards", icon: LayoutDashboard },
  { href: "/models",        label: "Models", icon: BrainCircuit },
  { href: "/settings",      label: "Settings", icon: Sliders }
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  // Get initials for profile placeholder
  const getInitials = () => {
    if (!user || !user.name) return "U";
    return user.name
      .split(" ")
      .map((n: string) => n[0])
      .join("")
      .toUpperCase()
      .substring(0, 2);
  };

  return (
    <div className={styles.dashboard}>
      {/* ---------- Top navigation ---------- */}
      <nav className={styles.navbar}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <Link href="/" className={styles.logo}>
            <span style={{ color: 'var(--color-primary-accent)', fontWeight: 800 }}>DataChat</span>
          </Link>
          <span className={styles.divider}>/</span>
          <span className={styles.subtext}>Analytics Workspace</span>
        </div>
        
        <div className={styles.profileSection}>
          <span className={styles.userName}>{user?.name || "User"}</span>
          <div className={styles.avatar}>
            {getInitials()}
          </div>
        </div>
      </nav>

      {/* ---------------------- Left sidebar ---------------------- */}
      <aside className={styles.sidebar}>
        <div className={styles.navGroup}>
          <span className={styles.navGroupTitle}>Navigation</span>
          {sideLinks.map((ln, i) => {
            const Icon = ln.icon;
            // Check if current path starts with link path to mark active
            const isActive = pathname === ln.href || pathname.startsWith(ln.href + "/");

            return (
              <Link
                key={i}
                href={ln.href}
                className={`${styles.sidebarLink} ${isActive ? styles.activeLink : ""}`}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1 }}>
                  <Icon size={18} strokeWidth={isActive ? 2.2 : 1.8} />
                  <span>{ln.label}</span>
                </div>
                {isActive && <ChevronRight size={14} className={styles.activeChevron} />}
              </Link>
            );
          })}
        </div>

        {/* Footer Area with Logout */}
        <div className={styles.sidebarFooter}>
          <button onClick={handleLogout} className={styles.logoutBtn}>
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* --------------------------- Page content --------------------------- */}
      <main className={styles.content}>{children}</main>
    </div>
  );
}
