"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight, Table, Database } from "lucide-react";
import styles from "./SchemaViewer.module.css";

interface Column {
  column_name?: string;
  name?: string;
  data_type?: string;
  type?: string;
}

interface SchemaViewerProps {
  schema: Record<string, Column[]>;
  onSelectTable?: (tableName: string) => void;
}

export function SchemaViewer({ schema, onSelectTable }: SchemaViewerProps) {
  const [expandedTables, setExpandedTables] = useState<Record<string, boolean>>({});

  const toggleTable = (tableName: string) => {
    setExpandedTables((prev) => ({
      ...prev,
      [tableName]: !prev[tableName]
    }));
  };

  const tables = Object.keys(schema);

  if (tables.length === 0) {
    return (
      <div className={styles.empty}>
        <Database size={24} style={{ opacity: 0.5, marginBottom: "0.5rem" }} />
        <p>No tables detected in connection schema.</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h3 className={styles.header}>Database Schema Tables</h3>
      <div className={styles.list}>
        {tables.map((table) => {
          const isExpanded = !!expandedTables[table];
          const cols = schema[table];

          return (
            <div key={table} className={styles.tableNode}>
              <div className={styles.tableRow} onClick={() => toggleTable(table)}>
                <span className={styles.chevron}>
                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </span>
                <Table size={16} className={styles.tableIcon} />
                <span
                  className={styles.tableName}
                  onClick={(e) => {
                    if (onSelectTable) {
                      e.stopPropagation();
                      onSelectTable(table);
                    }
                  }}
                  title={onSelectTable ? "Click to analyze table" : undefined}
                >
                  {table}
                </span>
                <span className={styles.countBadge}>{cols.length} cols</span>
              </div>

              {isExpanded && (
                <div className={styles.columnsList}>
                  {cols.map((col, idx) => {
                    const cName = col.column_name || col.name || "";
                    const cType = col.data_type || col.type || "";
                    return (
                      <div key={idx} className={styles.columnRow}>
                        <span className={styles.colName}>{cName}</span>
                        <span className={styles.colType}>{cType.toLowerCase()}</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
