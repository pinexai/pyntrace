import { useQuery } from '@tanstack/react-query'
import apiFetch from './client'
import type {
  SecurityReport, McpScan, EvalExperiment, Trace, Span,
  LatencyEndpoint, CostSummary, DailyCost,
  ComplianceReport, GitHistory, ReviewItem,
} from '../types'

export const useSecurityReports = () =>
  useQuery({ queryKey: ['security'], queryFn: () => apiFetch<SecurityReport[]>('/api/security/reports') })

export const useMcpScans = () =>
  useQuery({ queryKey: ['mcp'], queryFn: () => apiFetch<McpScan[]>('/api/mcp-scans') })

export const useEvalExperiments = () =>
  useQuery({ queryKey: ['eval'], queryFn: () => apiFetch<EvalExperiment[]>('/api/eval/experiments') })

export const useTraces = () =>
  useQuery({ queryKey: ['monitor'], queryFn: () => apiFetch<Trace[]>('/api/monitor/traces') })

export const useSpans = (traceId: string | null) =>
  useQuery({
    queryKey: ['spans', traceId],
    queryFn: () => apiFetch<Span[]>(`/api/monitor/traces/${encodeURIComponent(traceId!)}/spans`),
    enabled: !!traceId,
  })

export const useLatencyEndpoints = () =>
  useQuery({ queryKey: ['latency'], queryFn: () => apiFetch<LatencyEndpoint[]>('/api/latency/endpoints') })

export const useCostSummary = () =>
  useQuery({ queryKey: ['costs'], queryFn: () => apiFetch<CostSummary[]>('/api/costs/summary') })

export const useDailyCosts = () =>
  useQuery({ queryKey: ['costs-daily'], queryFn: () => apiFetch<DailyCost[]>('/api/costs/daily?days=30') })

export const useComplianceReports = () =>
  useQuery({ queryKey: ['compliance'], queryFn: () => apiFetch<ComplianceReport[]>('/api/compliance/reports') })

export const useGitHistory = () =>
  useQuery({ queryKey: ['git'], queryFn: () => apiFetch<GitHistory[]>('/api/git/history') })

export const useReviewItems = () =>
  useQuery({ queryKey: ['review'], queryFn: () => apiFetch<ReviewItem[]>('/api/review/pending') })
