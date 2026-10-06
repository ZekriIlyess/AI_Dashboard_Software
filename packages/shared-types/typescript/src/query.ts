// =============================================================================
// Nexus AI — Shared TypeScript Types: Query
// =============================================================================

/** A natural language query request */
export interface QueryRequest {
  connectionId: string;
  query: string;
  /** Optional: provide context from previous messages */
  conversationId?: string;
}

/** Response from the AI agent */
export interface QueryResponse {
  id: string;
  /** The original natural language query */
  naturalLanguageQuery: string;
  /** Generated SQL query */
  generatedSql: string;
  /** SQL validation result */
  validation: SqlValidationResult;
  /** Query results (if executed successfully) */
  result?: QueryResult;
  /** AI-generated explanation */
  explanation: string;
  /** Suggested visualizations */
  suggestedCharts: ChartSuggestion[];
  /** Follow-up question suggestions */
  suggestedFollowUps: string[];
  /** Execution metadata */
  metadata: QueryMetadata;
}

/** SQL validation result */
export interface SqlValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  /** Estimated cost/complexity */
  estimatedRows?: number;
  estimatedTimeMs?: number;
}

/** Query execution result */
export interface QueryResult {
  columns: ResultColumn[];
  rows: Record<string, unknown>[];
  totalRows: number;
  truncated: boolean;
  executionTimeMs: number;
}

/** Column metadata for query results */
export interface ResultColumn {
  name: string;
  type: string;
  isNumeric: boolean;
  isTemporal: boolean;
  isCategorical: boolean;
}

/** Chart suggestion from the Viz Agent */
export interface ChartSuggestion {
  chartType: "bar" | "line" | "scatter" | "pie" | "heatmap" | "histogram" | "area" | "table";
  title: string;
  xAxis?: string;
  yAxis?: string;
  groupBy?: string;
  confidence: number;
  reason: string;
}

/** Query execution metadata */
export interface QueryMetadata {
  agentsUsed: string[];
  totalTimeMs: number;
  llmModel: string;
  llmTokensUsed: number;
  cached: boolean;
}

/** Streaming message types for WebSocket */
export type StreamingMessage =
  | { type: "thinking"; content: string }
  | { type: "sql_generated"; sql: string; validation: SqlValidationResult }
  | { type: "executing"; message: string }
  | { type: "result"; data: QueryResult }
  | { type: "explanation"; content: string }
  | { type: "chart"; suggestion: ChartSuggestion }
  | { type: "follow_ups"; suggestions: string[] }
  | { type: "error"; message: string; code: string }
  | { type: "done"; metadata: QueryMetadata };
