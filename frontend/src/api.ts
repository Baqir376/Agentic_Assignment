import type { AuditRun, PipelineResponse } from "./types";

export const MAX_DOCUMENT_LENGTH = 30000;
export const MAX_TASK_LENGTH = 2000;
const object = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export async function readResponse(
  response: Response,
): Promise<Record<string, unknown>> {
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new Error(
      "The service sent an unreadable response. Your document is still here. Retry or check the service.",
    );
  }
  if (!object(data))
    throw new Error("The service sent an unexpected response. Please retry.");
  if (!response.ok)
    throw new Error(
      typeof data.error === "string"
        ? data.error
        : `The service could not complete the request (${response.status}). Please retry.`,
    );
  return data;
}

export function parseResult(data: Record<string, unknown>): PipelineResponse {
  if (data.success !== true)
    throw new Error(
      typeof data.error === "string"
        ? data.error
        : "Processing did not complete. Please retry.",
    );
  if (
    !["raw_text", "sanitized_text", "final_answer", "routing_decision"].every(
      (key) => typeof data[key] === "string",
    ) ||
    !object(data.pii_token_map) ||
    !Object.values(data.pii_token_map).every((v) => typeof v === "string") ||
    typeof data.latency_seconds !== "number" ||
    !Number.isFinite(data.latency_seconds) ||
    data.latency_seconds < 0 ||
    typeof data.validation_passed !== "boolean"
  ) {
    throw new Error(
      "The result is incomplete and cannot be displayed safely. Your document is unchanged. Please retry.",
    );
  }
  return {
    ...data,
    routing_reason:
      typeof data.routing_reason === "string" ? data.routing_reason : "",
    errors: Array.isArray(data.errors)
      ? data.errors.filter((v): v is string => typeof v === "string")
      : [],
    hallucination_detected: data.hallucination_detected === true,
  } as unknown as PipelineResponse;
}

export function parseRuns(value: unknown): AuditRun[] {
  if (
    !Array.isArray(value) ||
    !value.every(
      (r) =>
        object(r) &&
        typeof r.run_id === "string" &&
        typeof r.id === "number" &&
        typeof r.timestamp === "string" &&
        (r.category === null || typeof r.category === "string") &&
        (r.success === 0 || r.success === 1) &&
        typeof r.latency_seconds === "number" &&
        typeof r.routing_decision === "string" &&
        typeof r.pii_found_total === "number",
    )
  ) {
    throw new Error(
      "The service returned incomplete audit records. Please retry.",
    );
  }
  return value as AuditRun[];
}
