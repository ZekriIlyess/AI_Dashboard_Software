"use client";

import React, { useState, useEffect } from "react";
import { Database, Snowflake, Trash2, Plus, Server, Check, HardDrive, Cloud } from "lucide-react";
import styles from "./ConnectionWizard.module.css";
import { api, ApiError } from "@/lib/api";

type DbName = "postgres" | "mysql" | "snowflake" | "sqlite" | "bigquery";

interface DbItem {
  name: string;
  type: DbName;
  icon: React.ComponentType<any>;
  color: string;
}

const dbList: DbItem[] = [
  { name: "PostgreSQL", type: "postgres", icon: Database, color: "#818cf8" },
  { name: "MySQL", type: "mysql", icon: Database, color: "#38bdf8" },
  { name: "Snowflake", type: "snowflake", icon: Snowflake, color: "#22d3ee" },
  { name: "SQLite", type: "sqlite", icon: HardDrive, color: "#10b981" },
  { name: "BigQuery", type: "bigquery", icon: Cloud, color: "#f59e0b" },
];

const commonFields = ["Host", "Port", "Database", "Username", "Password"];

interface DatabaseConnection {
  id: string;
  db_type: string;
  name?: string;
  database?: string;
  host?: string;
}

export default function ConnectionWizard() {
  const [existingConnections, setExistingConnections] = useState<DatabaseConnection[]>([]);
  const [selectedDb, setSelectedDb] = useState<DbName>("postgres");
  const [connectionData, setConnectionData] = useState<Record<string, string>>(
    Object.fromEntries(commonFields.map((f) => [f, ""]))
  );
  const [status, setStatus] = useState<"idle" | "testing" | "success" | "error" | "saving">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  const loadConnections = async () => {
    try {
      const payload: any = await api.get("/connections/");
      setExistingConnections(payload || []);
    } catch (e) {
      console.error("Failed to load existing DB connections", e);
    }
  };

  useEffect(() => {
    loadConnections();
  }, []);

  // Reset form when active database selection changes
  useEffect(() => {
    setConnectionData(Object.fromEntries(commonFields.map((f) => [f, ""])));
    setStatus("idle");
    setErrorMessage("");
  }, [selectedDb]);

  const handleChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setConnectionData((prev) => ({
      ...prev,
      [field]: e.target.value,
    }));
    if (status === "success" || status === "error") {
      setStatus("idle");
    }
  };

  const getDefaultPort = (dbType: DbName) => {
    if (dbType === "postgres") return 5432;
    if (dbType === "mysql") return 3306;
    return 443;
  };

  const buildPayload = () => {
    if (selectedDb === "sqlite") {
      return {
        db_type: selectedDb,
        host: connectionData["Host"] || "",
        port: 0,
        database: "sqlite.db",
        username: "sqlite",
        password: "sqlite_password",
      };
    }
    if (selectedDb === "bigquery") {
      return {
        db_type: selectedDb,
        host: connectionData["Host"] || "",
        port: 0,
        database: connectionData["Database"] || "",
        username: "bigquery",
        password: "bigquery_password",
      };
    }
    return {
      db_type: selectedDb,
      host: connectionData["Host"] || "",
      port: parseInt(connectionData["Port"]) || getDefaultPort(selectedDb),
      database: connectionData["Database"] || "",
      username: connectionData["Username"] || "",
      password: connectionData["Password"] || "",
    };
  };

  const handleTest = async (e: React.MouseEvent) => {
    e.preventDefault();
    setStatus("testing");
    setErrorMessage("");
    
    try {
      await api.post("/connections/test", buildPayload());
      setStatus("success");
    } catch (err) {
      setStatus("error");
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage(String(err));
      }
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("saving");
    try {
      await api.post("/connections/", buildPayload());
      setStatus("idle");
      setConnectionData(Object.fromEntries(commonFields.map((f) => [f, ""])));
      loadConnections(); // Refresh the list
    } catch (err) {
      setStatus("error");
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage(String(err));
      }
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to disconnect this database?")) return;
    try {
      await api.delete(`/connections/${id}`);
      loadConnections();
    } catch (err) {
      console.error("Failed to delete connection", err);
      alert("Failed to delete connection.");
    }
  };

  // Get active fields dynamically for the selected database
  const getActiveFields = (): { key: string; label: string; placeholder: string; type: string }[] => {
    if (selectedDb === "sqlite") {
      return [
        { key: "Host", label: "SQLite File Path", placeholder: "e.g. C:\\databases\\local_store.db or /var/db/app.db", type: "text" }
      ];
    }
    if (selectedDb === "bigquery") {
      return [
        { key: "Host", label: "Service Account JSON Path", placeholder: "e.g. C:\\keys\\gcp-service-account.json", type: "text" },
        { key: "Database", label: "BigQuery Project ID", placeholder: "e.g. enterprise-analytics-322105", type: "text" }
      ];
    }
    if (selectedDb === "snowflake") {
      return [
        { key: "Host", label: "Account Identifier", placeholder: "e.g. xy12345.us-east-2.aws", type: "text" },
        { key: "Database", label: "Database Name", placeholder: "e.g. CUSTOMER_DB", type: "text" },
        { key: "Username", label: "Username", placeholder: "e.g. READ_ONLY_USER", type: "text" },
        { key: "Password", label: "Password", placeholder: "Enter Snowflake password", type: "password" }
      ];
    }
    // Default PostgreSQL / MySQL
    const defaultPort = selectedDb === "postgres" ? "5432" : "3306";
    return [
      { key: "Host", label: "Host / Server Address", placeholder: "e.g. localhost or database.internal.net", type: "text" },
      { key: "Port", label: "Port", placeholder: `e.g. ${defaultPort}`, type: "text" },
      { key: "Database", label: "Database Name", placeholder: "e.g. ecommerce_production", type: "text" },
      { key: "Username", label: "Username", placeholder: "e.g. db_reader", type: "text" },
      { key: "Password", label: "Password", placeholder: "Enter database password", type: "password" }
    ];
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Existing Connections Section */}
      {existingConnections.length > 0 && (
        <section className={styles.existingConnections}>
          <h2 style={{ marginBottom: '1.25rem', color: '#fff', fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
            Connected Data Sources
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.25rem' }}>
            {existingConnections.map((conn) => {
              const dbConf = dbList.find(d => d.type === conn.db_type) || { icon: Server, color: "#a5b4fc", name: conn.db_type };
              const Icon = dbConf.icon;

              return (
                <div key={conn.id} className={styles.connectionCard}>
                  <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start', flex: 1, minWidth: 0 }}>
                    <div className={styles.connAvatar} style={{ color: dbConf.color }}>
                      <Icon size={20} />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', flex: 1, minWidth: 0 }}>
                      <h3 style={{ margin: 0, color: '#fff', fontSize: '1rem', fontWeight: 600 }}>
                        {dbConf.name}
                      </h3>
                      <span style={{ fontSize: '0.825rem', color: 'var(--color-text-muted)', fontFamily: 'var(--font-family-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {conn.db_type === "sqlite" ? "Local file" : conn.host}
                      </span>
                      {conn.db_type !== "sqlite" && (
                        <span style={{ fontSize: '0.825rem', color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          Database/Project: <strong style={{ color: '#fff', fontWeight: 500 }}>{conn.database}</strong>
                        </span>
                      )}
                    </div>
                    
                    <button 
                      onClick={() => handleDelete(conn.id)}
                      className={styles.disconnectBtn}
                      title="Disconnect database"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Add New Connection Wizard */}
      <div className={styles.wizardContainer}>
        {/* ------------------- LEFT COLUMN -------------------- */}
        <aside className={styles.leftColumn}>
          <span className={styles.sidebarTitle}>Select Source</span>
          {dbList.map((db) => {
            const DbIcon = db.icon;
            const isSelected = db.type === selectedDb;

            return (
              <div
                key={db.type}
                onClick={() => setSelectedDb(db.type)}
                className={`${styles.dbCard} ${isSelected ? styles.active : ""}`}
              >
                <div className={styles.dbIconWrapper} style={{ color: isSelected ? '#fff' : db.color, background: isSelected ? db.color : 'rgba(255,255,255,0.02)' }}>
                  <DbIcon size={18} />
                </div>
                <span>{db.name}</span>
              </div>
            );
          })}
        </aside>

        {/* ------------------- RIGHT COLUMN -------------------------- */}
        <section className={styles.rightColumn}>
          <div className={styles.formHeader}>
            <h3 className={styles.title}>Connect to {dbList.find(d => d.type === selectedDb)?.name}</h3>
            <p className={styles.subtitle}>Credentials are fully encrypted. Read-only permissions are recommended.</p>
          </div>

          <form onSubmit={handleSave}>
            <div className={styles.formGrid}>
              {getActiveFields().map((field) => (
                <div key={field.key} className={styles.inputGroup} style={field.key === "Host" ? { gridColumn: '1 / -1' } : {}}>
                  <label htmlFor={field.key}>{field.label}</label>
                  <input
                    id={field.key}
                    type={field.type}
                    placeholder={field.placeholder}
                    value={connectionData[field.key] || ""}
                    onChange={handleChange(field.key)}
                    required
                  />
                </div>
              ))}
            </div>
            
            {status === "error" && (
              <div className={styles.errorContainer}>
                <strong>Connection Error:</strong> {errorMessage}
              </div>
            )}

            {/* Buttons row */}
            <div className={styles.buttonsRow}>
              <button
                onClick={handleTest}
                type="button"
                className={`${styles.testBtn} ${status === "success" ? styles.testSuccess : ""}`}
                disabled={status === "testing" || status === "saving"}
              >
                {status === "testing" ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div className={styles.spinner} />
                    <span>Testing...</span>
                  </div>
                ) : status === "success" ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Check size={16} />
                    <span>Tested Successfully</span>
                  </div>
                ) : (
                  "Test Connection"
                )}
              </button>
              <button type="submit" className={styles.saveBtn} disabled={status !== "success"}>
                {status === "saving" ? "Saving..." : (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Plus size={16} />
                    <span>Save Connection</span>
                  </div>
                )}
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
