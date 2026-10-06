'use client';

import {
  TrendingUp,
  TrendingDown,
  Database,
  MessageSquare,
  BarChart3,
  Brain,
  ArrowUpRight,
  Clock,
  Zap,
  Users,
} from 'lucide-react';
import styles from './page.module.css';

interface MetricCard {
  title: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
  icon: React.ReactNode;
  color: 'primary' | 'secondary' | 'success' | 'warning';
}

const metrics: MetricCard[] = [
  {
    title: 'Total Queries',
    value: '12,847',
    change: '+23.5%',
    trend: 'up',
    icon: <MessageSquare size={20} />,
    color: 'primary',
  },
  {
    title: 'Active Connections',
    value: '8',
    change: '+2',
    trend: 'up',
    icon: <Database size={20} />,
    color: 'secondary',
  },
  {
    title: 'Dashboards',
    value: '24',
    change: '+4',
    trend: 'up',
    icon: <BarChart3 size={20} />,
    color: 'success',
  },
  {
    title: 'ML Models',
    value: '6',
    change: '+1',
    trend: 'up',
    icon: <Brain size={20} />,
    color: 'warning',
  },
];

const recentQueries = [
  {
    query: 'Show revenue by region for Q2 2025',
    time: '2 min ago',
    status: 'completed',
    rows: 12,
  },
  {
    query: 'Top 5 churning customers this month',
    time: '15 min ago',
    status: 'completed',
    rows: 5,
  },
  {
    query: 'Average order value trend over 12 months',
    time: '1 hour ago',
    status: 'completed',
    rows: 12,
  },
  {
    query: 'User signups by acquisition channel',
    time: '3 hours ago',
    status: 'completed',
    rows: 8,
  },
  {
    query: 'Predict next quarter revenue',
    time: '5 hours ago',
    status: 'completed',
    rows: 1,
  },
];

const recentActivity = [
  { action: 'Created dashboard', target: 'Q2 Revenue Overview', time: '10 min ago', icon: <BarChart3 size={14} /> },
  { action: 'Connected database', target: 'production-analytics', time: '1 hour ago', icon: <Database size={14} /> },
  { action: 'Trained model', target: 'Churn Predictor v2', time: '2 hours ago', icon: <Brain size={14} /> },
  { action: 'Shared dashboard', target: 'Marketing KPIs', time: '4 hours ago', icon: <Users size={14} /> },
  { action: 'Ran query', target: 'Monthly active users', time: '5 hours ago', icon: <Zap size={14} /> },
];

export default function DashboardHome() {
  return (
    <div className={styles.page}>
      {/* ── Page Header ────────────────────────────────── */}
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Overview</h1>
          <p className={styles.subtitle}>
            Welcome back! Here&apos;s what&apos;s happening with your data.
          </p>
        </div>
        <div className={styles.headerActions}>
          <span className={styles.lastUpdated}>
            <Clock size={14} />
            Updated just now
          </span>
        </div>
      </div>

      {/* ── Metric Cards ──────────────────────────────── */}
      <div className={styles.metricsGrid}>
        {metrics.map((metric, i) => (
          <div
            key={i}
            className={`${styles.metricCard} ${styles[metric.color]}`}
            style={{ animationDelay: `${i * 0.1}s` }}
          >
            <div className={styles.metricTop}>
              <div className={styles.metricIconWrap}>{metric.icon}</div>
              <span className={`${styles.metricChange} ${styles[metric.trend]}`}>
                {metric.trend === 'up' ? (
                  <TrendingUp size={14} />
                ) : (
                  <TrendingDown size={14} />
                )}
                {metric.change}
              </span>
            </div>
            <div className={styles.metricValue}>{metric.value}</div>
            <div className={styles.metricTitle}>{metric.title}</div>
          </div>
        ))}
      </div>

      {/* ── Content Grid ──────────────────────────────── */}
      <div className={styles.contentGrid}>
        {/* Recent Queries */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <h3 className={styles.cardTitle}>Recent Queries</h3>
            <a href="/explore" className={styles.viewAll}>
              View all <ArrowUpRight size={14} />
            </a>
          </div>
          <div className={styles.queryList}>
            {recentQueries.map((q, i) => (
              <div key={i} className={styles.queryItem}>
                <div className={styles.queryIcon}>
                  <MessageSquare size={14} />
                </div>
                <div className={styles.queryContent}>
                  <span className={styles.queryText}>{q.query}</span>
                  <span className={styles.queryMeta}>
                    {q.rows} rows · {q.time}
                  </span>
                </div>
                <span className={styles.queryStatus}>{q.status}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <h3 className={styles.cardTitle}>Activity</h3>
          </div>
          <div className={styles.activityList}>
            {recentActivity.map((a, i) => (
              <div key={i} className={styles.activityItem}>
                <div className={styles.activityIcon}>{a.icon}</div>
                <div className={styles.activityContent}>
                  <span className={styles.activityAction}>{a.action}</span>
                  <span className={styles.activityTarget}>{a.target}</span>
                </div>
                <span className={styles.activityTime}>{a.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
