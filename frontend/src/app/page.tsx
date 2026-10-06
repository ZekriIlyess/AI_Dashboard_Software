"use client";

import React, { useEffect } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/stores/authStore';
import styles from './page.module.css';

const HERO_TITLE = "Power BI + AutoML Agent";
const SUBHEADLINE =
  "Unlock autonomous insights and advanced forecasting with AI-driven analytics. Your data never leaves your network.";

const FEATURES = [
  {
    title: "Agent-Driven Insights",
    description: "Ask questions in natural language. Our AI agent understands your schema and generates perfectly optimized SQL.",
  },
  {
    title: "One-Click AutoML",
    description: "Select a target metric and watch as DataChat trains, evaluates, and explains multiple prediction models instantly.",
  },
  {
    title: "Zero-ETL Architecture",
    description: "Connect directly to PostgreSQL, MySQL, Snowflake, or BigQuery. Raw data stays securely in your environment.",
  },
];

export default function Home() {
  const { isAuthenticated, checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <div className={styles.pageWrapper}>
      {/* Hero */}
      <section className={`${styles.hero} glass container`}>
        <h1>{HERO_TITLE}</h1>
        <p className={styles.subheadline}>{SUBHEADLINE}</p>

        <div className={styles.actionButtons}>
          <Link href={isAuthenticated ? "/explore" : "/login"} className="btn-primary">
            {isAuthenticated ? "Go to Dashboard" : "Start Exploring"}
          </Link>
        </div>
      </section>

      {/* Feature Grid */}
      <section className={`${styles.featuresSection} container`}>
        <div className={styles.featureGrid}>
          {FEATURES.map((f, i) => (
            <article key={i} className={`${styles.featureCard} glass`}>
              <h3>{f.title}</h3>
              <p>{f.description}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
