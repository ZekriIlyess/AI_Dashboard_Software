// =============================================================================
// Nexus AI — Shared TypeScript Types: Database
// =============================================================================

/** Supported database types */
export type DatabaseType =
  | "postgresql"
  | "mysql"
  | "sqlite"
  | "sqlserver"
  | "snowflake"
  | "bigquery"
  | "redshift";

/** Database connection configuration */
export interface ConnectionConfig {
  id: string;
  name: string;
  dbType: DatabaseType;
  host: string;
  port: number;
  database: string;
  username: string;
  /** Password is never sent to the frontend — only used for creation */
  password?: string;
  ssl: boolean;
  isActive: boolean;
  createdAt: string;
  lastTestedAt?: string;
}

/** Result of a connection test */
export interface ConnectionTestResult {
  success: boolean;
  message: string;
  latencyMs: number;
  serverVersion?: string;
}

/** Database schema information */
export interface SchemaInfo {
  tables: TableInfo[];
  totalTables: number;
  totalColumns: number;
  extractedAt: string;
}

/** Table information */
export interface TableInfo {
  name: string;
  schema: string;
  columns: ColumnInfo[];
  rowCount?: number;
  sizeBytes?: number;
  primaryKey?: string[];
  foreignKeys: ForeignKeyInfo[];
  indexes: IndexInfo[];
}

/** Column information */
export interface ColumnInfo {
  name: string;
  dataType: string;
  isNullable: boolean;
  isPrimaryKey: boolean;
  isForeignKey: boolean;
  defaultValue?: string;
  /** Sample unique values (for categorical columns) */
  sampleValues?: string[];
  /** Basic statistics (for numerical columns) */
  stats?: ColumnStats;
}

/** Column statistics */
export interface ColumnStats {
  min?: number;
  max?: number;
  mean?: number;
  median?: number;
  stdDev?: number;
  nullCount: number;
  distinctCount: number;
}

/** Foreign key relationship */
export interface ForeignKeyInfo {
  column: string;
  referencedTable: string;
  referencedColumn: string;
}

/** Index information */
export interface IndexInfo {
  name: string;
  columns: string[];
  isUnique: boolean;
}
