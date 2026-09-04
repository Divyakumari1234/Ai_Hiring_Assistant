import type { Call, Candidate } from "./types";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });
  if (!response.ok) {
    const data = await response
      .json()
      .catch(() => ({ detail: "Something went wrong" }));
    throw new Error(
      typeof data.detail === "string" ? data.detail : "Request failed",
    );
  }
  return response.json();
}
export const api = {
  search: (job_description: string, location: string) =>
    request<{ results: Candidate[]; source: string; total: number }>(
      "/api/search",
      {
        method: "POST",
        body: JSON.stringify({
          job_description,
          location,
          experience_min: 3,
          experience_max: 12,
        }),
      },
    ),
  candidates: () => request<{ results: Candidate[] }>("/api/candidates"),
  calls: () => request<{ results: Call[] }>("/api/calls"),
  outreach: (candidate_ids: string[], channel: "voice" | "voice+sms") =>
    request<{ message: string; mode: string }>("/api/outreach", {
      method: "POST",
      body: JSON.stringify({ candidate_ids, channel }),
    }),
  health: () =>
    request<{ status: string; hunar_configured: boolean; live_calls: boolean }>(
      "/api/health",
    ),
};
