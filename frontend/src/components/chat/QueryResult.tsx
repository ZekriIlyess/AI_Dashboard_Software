"use client";

import React from "react";
import styles from "./QueryResult.module.css";

interface QueryResultProps {
  data: Record<string, any>[];
  sql?: string;
}

export function QueryResult({ data, sql }: QueryResultProps) {
  if (!data || data.length === 0) {
    return <div className={styles.empty}>No rows returned.</div>;
  }

  const columns = Object.keys(data[0]);

  return (
    <div className={styles.container}>
      {sql && (
        <div className={styles.sqlBlock}>
          <div className={styles.sqlHeader}>Executed SQL Query</div>
          <pre className={styles.sqlCode}><code>{sql}</code></pre>
        </div>
      )}
      
      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              {columns.map(col => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rIdx) => (
              <tr key={rIdx}>
                {columns.map(col => (
                  <td key={col}>{String(row[col] ?? "")}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className={styles.footer}>
        Total Rows: {data.length}
      </div>
    </div>
  );
}
