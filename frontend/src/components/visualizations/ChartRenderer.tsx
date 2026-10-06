"use client";

import React, { useEffect, useState } from "react";
import styles from "./ChartRenderer.module.css";

// Dummy data for the scaffold
const mockData = [
  { label: "Jan", value: 35 },
  { label: "Feb", value: 50 },
  { label: "Mar", value: 40 },
  { label: "Apr", value: 85 },
  { label: "May", value: 65 },
  { label: "Jun", value: 100 },
];

export default function ChartRenderer() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return <div style={{ height: '100%' }}>Loading...</div>;

  return (
    <div className={styles.chartContainer}>
      {mockData.map((data, idx) => (
        <div key={idx} className={styles.barWrapper}>
          <div 
            className={styles.barValue}
            style={{ animationDelay: `${0.5 + (idx * 0.1)}s` }}
          >
            {data.value}k
          </div>
          <div
            className={styles.barInner}
            style={{
              height: `${data.value}%`,
              animationDelay: `${idx * 0.1}s`,
            }}
          />
          <div className={styles.barLabel}>{data.label}</div>
        </div>
      ))}
    </div>
  );
}
