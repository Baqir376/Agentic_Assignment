export interface PipelineResponse {
  success: boolean;
  latency_seconds: number;
  raw_text: string;
  sanitized_text: string;
  final_answer: string;
  pii_token_map: Record<string, string>;
  reverse_map: Record<string, string>;
  pii_counts: Record<string, number>;
  routing_decision: "local" | "cloud" | string;
  routing_reason: string;
  routing_stage: "symbolic" | "neural" | string;
  validation_passed: boolean;
  validation_attempts: number;
  hallucination_detected: boolean;
  hallucination_reason?: string | null;
  debate_rounds: number;
  errors: string[];
}

export interface AuditRun {
  id: number;
  run_id: string;
  timestamp: string;
  category: string;
  pii_found_total: number;
  pii_by_type: string;
  routing_decision: string;
  routing_stage: string;
  sensitivity_flagged: number;
  response_source: string;
  hallucination_detected: number;
  latency_seconds: number;
  success: number;
}

export interface AuditStats {
  total_runs: number;
  successful_runs: number;
  avg_pii_found: number;
  avg_latency: number;
  routing_breakdown: {
    local: number;
    cloud: number;
  };
  hallucination_rate: number;
  avg_validation_attempts: number;
}

export interface PresetDocument {
  id: string;
  title: string;
  category: "Medical" | "Legal" | "HR" | "Financial";
  task: string;
  text: string;
  badge: string;
}

