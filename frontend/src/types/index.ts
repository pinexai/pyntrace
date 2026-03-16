export interface SecurityReport {
  id: number
  target_fn: string
  model: string
  model_provider?: string
  total_attacks: number
  vulnerable_count: number
  vulnerability_rate: number
  total_cost_usd: number
  avg_latency_ms?: number
  status?: string
  git_commit?: string
  created_at: number
  results_json?: string | AttackResult[]
}

export interface AttackResult {
  plugin: string
  vulnerable: boolean
  template_name?: string
  severity?: string
}

export interface McpScan {
  id: number
  endpoint: string
  total_tests: number
  vulnerable_count: number
  created_at: number
}

export interface EvalExperiment {
  id: number
  name: string
  function_name: string
  git_commit?: string
  pass_rate?: number
  created_at: number
}

export interface Trace {
  id: string
  name: string
  start_time: number
  end_time?: number
  error?: boolean | string
  user_id?: string
}

export interface Span {
  id: string
  name: string
  span_type: 'llm' | 'tool' | 'retrieval' | 'embed' | string
  start_time: number
  end_time: number
  error?: boolean | string
}

export interface LatencyEndpoint {
  endpoint: string
  calls: number
  p50_ms: number
  p95_ms: number
  p99_ms: number
  min_ms?: number
  max_ms?: number
  error_rate?: number
}

export interface CostSummary {
  model: string
  calls: number
  total_cost: number
  avg_ms?: number
}

export interface DailyCost {
  date: string
  cost: number
}

export interface ComplianceReport {
  id: number
  framework: string
  overall_status: string
  created_at: number
}

export interface GitHistory {
  git_commit: string
  scans: number
  avg_vuln_rate: number
  total_cost: number
}

export interface ReviewItem {
  result_id: number
  plugin: string
  severity?: string
  label?: string
  reviewer?: string
  created_at: number
}

export type TabName =
  | 'security' | 'mcp' | 'eval' | 'monitor'
  | 'latency'  | 'costs' | 'review' | 'compliance' | 'git'
