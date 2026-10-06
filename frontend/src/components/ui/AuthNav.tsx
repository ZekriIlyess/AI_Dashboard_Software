"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { useAuthStore } from "@/stores/authStore";

export function AuthNav() {
  const { isAuthenticated, user, checkAuth, logout } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  if (isAuthenticated && user) {
    return (
      <div className="nav-links" style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <span style={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.9rem' }}>
          {user.name || user.email}
        </span>
        <Link href="/explore" className="btn-secondary nav-btn" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}>
          Dashboard
        </Link>
        <button 
          onClick={() => {
            logout();
            window.location.href = "/";
          }} 
          className="btn-secondary nav-btn" 
          style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', background: 'transparent', border: '1px solid rgba(255,255,255,0.2)' }}
        >
          Logout
        </button>
      </div>
    );
  }

  return (
    <div className="nav-links">
      <Link href="/login" className="btn-secondary nav-btn">Sign In</Link>
    </div>
  );
}
