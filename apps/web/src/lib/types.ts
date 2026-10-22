export type Json = Record<string, unknown>;
export interface ModelConfig {
  id?: string;
  name: string;
  adapter: string;
  model: string;
  base_url?: string | null;
  api_key_env?: string | null;
  capabilities: string[];
  context_window?: number | null;
  input_cost_per_million?: number | null;
  output_cost_per_million?: number | null;
  demo: boolean;
  description: string;
}
export interface AgentConfig {
  id?: string;
  name: string;
  adapter: string;
  executable?: string | null;
  args: string[];
  model_flag?: string | null;
  model_base_url_env?: string | null;
  model_api_key_env?: string | null;
  capabilities: string[];
  env_allowlist: string[];
  demo: boolean;
  native: boolean;
  description: string;
}
export interface SystemSpec {
  model_id?: string;
  agent_id?: string;
  label?: string;
  parameters?: Json;
}
export interface ExperimentConfig {
  name: string;
  description?: string;
  mode: string;
  systems: SystemSpec[];
  benchmark_id: string;
  task_ids: string[];
  trials: number;
  budget_seconds: number;
  task_timeout_seconds: number;
  max_tokens: number;
  max_total_tokens?: number | null;
  max_cost_usd?: number | null;
  retries: number;
  memory_mb: number;
  cpus: number;
  isolation: string;
  allow_host_process: boolean;
  network: boolean;
  tools: string[];
  seed: number;
  demo: boolean;
  baseline_id?: string | null;
}
export interface Registration<T> {
  id: string;
  config: T;
  name?: string;
  demo?: boolean;
}
export interface Compatibility {
  compatible: boolean;
  reasons: string[];
  warnings: string[];
  capabilities: Record<string, string>;
  requirements: string[];
}
export interface Metrics {
  by_category?: Record<string, Metrics>;
  total?: number;
  passed?: number;
  failed?: number;
  success_rate?: number | null;
  confidence_low?: number | null;
  confidence_high?: number | null;
  duration_seconds?: number | null;
  median_latency_seconds?: number | null;
  p95_latency_seconds?: number | null;
  tokens?: number | null;
  cost_usd?: number | null;
  cost_per_success_usd?: number | null;
  warning?: string | null;
}
export interface Experiment {
  id: string;
  name: string;
  mode: string;
  status: string;
  demo: boolean;
  created_at: string;
  config: ExperimentConfig;
  runs?: Run[];
}
export interface Result {
  task_id: string;
  task_name: string;
  category: string;
  passed: boolean;
  duration_seconds: number;
  error?: string | null;
  failure_category?: string | null;
  output?: Json | null;
  verification: {
    passed: boolean;
    verifier: string;
    evidence: Json;
    reason?: string | null;
  };
  demo: boolean;
}
export interface TraceEvent {
  sequence: number;
  type: string;
  timestamp: string;
  task_id?: string;
  message: string;
  data: Json;
  severity: string;
  provenance: string;
}
export interface Artifact {
  id: string;
  name: string;
  size_bytes: number;
  media_type: string;
  sha256: string;
}
export interface Run {
  id: string;
  experiment_id: string;
  system_id: string;
  system_name: string;
  trial: number;
  status: string;
  metrics: Metrics;
  error?: string | null;
  started_at?: string;
  finished_at?: string;
  manifest: Json & { demo?: boolean };
  results?: Result[];
  events?: TraceEvent[];
  artifacts?: Artifact[];
}
export interface Benchmark {
  id: string;
  name: string;
  version: string;
  description: string;
  task_count?: number;
  categories?: string[];
  requirements?: string[];
  tasks?: {
    id: string;
    name: string;
    category: string;
    verifier: string;
    requires_execution?: boolean;
    required_capabilities?: string[];
    description?: string;
    prompt?: string;
  }[];
  [key: string]: unknown;
}
export interface Overview {
  experiments: Experiment[];
  models: Registration<ModelConfig>[];
  agents: Registration<AgentConfig>[];
  runs: Run[];
  metrics: Metrics;
  recent_failures: (Result & { run_id?: string })[];
}
export interface Comparison {
  runs: Run[];
  summary?: unknown;
  tasks?: unknown;
  task_rows?: unknown;
  comparable: boolean;
  reasons: string[];
  [key: string]: unknown;
}
