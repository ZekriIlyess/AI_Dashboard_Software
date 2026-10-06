"use client";

import { useState } from "react";
import Link from "next/link";
import styles from "./login.module.css";

import { useAuthStore } from "@/stores/authStore";

export default function LoginPage() {
  const { login } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (email && password) {
      setError("");
      try {
        await login(email, password);
        window.location.href = "/explore";
      } catch (err: any) {
        setError(err.message || "Failed to login");
      }
    } else {
      setError("Please fill both fields");
    }
  };

  return (
    <div className={styles.fullScreen}>
      <div className={styles.bg} />

      <div className={`${styles.card} ${error ? styles.error : ""}`}>
        <h2>Welcome to DataChat</h2>

        <form onSubmit={handleSubmit} noValidate>
          <label htmlFor="email" className={styles.label}>
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@domain.com"
            className={styles.input}
            required
          />

          <label htmlFor="password" className={styles.label}>
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className={styles.input}
            required
          />

          {error && <p className={styles.errorMsg}>{error}</p>}

          <button type="submit" className={styles.button}>
            Sign In
          </button>
        </form>

        <p className={styles.footerLink}>
          Don’t have an account? <Link href="/register">Register</Link>
        </p>
      </div>
    </div>
  );
}
