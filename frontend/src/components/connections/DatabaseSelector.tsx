"use client";

import React from "react";
import { Database, HardDrive, Cpu, Layers } from "lucide-react";
import styles from "./DatabaseSelector.module.css";

interface DatabaseOption {
  type: string;
  name: string;
  description: string;
  icon: React.ReactNode;
}

interface DatabaseSelectorProps {
  selected: string | null;
  onSelect: (type: string) => void;
}

export function DatabaseSelector({ selected, onSelect }: DatabaseSelectorProps) {
  const options: DatabaseOption[] = [
    { type: "postgresql", name: "PostgreSQL", description: "Standard relational open source database.", icon: <Database size={24} /> },
    { type: "mysql", name: "MySQL", description: "Widely used open source relational database.", icon: <Database size={24} /> },
    { type: "sqlite", name: "SQLite", description: "Local database file storage connection.", icon: <HardDrive size={24} /> },
    { type: "snowflake", name: "Snowflake", description: "Enterprise data warehouse cloud connection.", icon: <Cpu size={24} /> },
    { type: "bigquery", name: "Google BigQuery", description: "Google Cloud analytics database cluster.", icon: <Layers size={24} /> },
    { type: "sqlserver", name: "SQL Server", description: "Microsoft Relational SQL Database Server.", icon: <Database size={24} /> },
    { type: "redshift", name: "AWS Redshift", description: "Amazon cloud analytics data warehouse.", icon: <Layers size={24} /> }
  ];

  return (
    <div className={styles.grid}>
      {options.map((opt) => (
        <div
          key={opt.type}
          className={`${styles.card} ${selected === opt.type ? styles.selected : ""}`}
          onClick={() => onSelect(opt.type)}
        >
          <div className={styles.icon}>{opt.icon}</div>
          <div className={styles.meta}>
            <h4 className={styles.name}>{opt.name}</h4>
            <p className={styles.description}>{opt.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
