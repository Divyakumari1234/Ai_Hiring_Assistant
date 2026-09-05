import type { Call, Dashboard } from "./types";
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const readOnly = (options?.method ?? "GET").toUpperCase() === "GET";
  const attempts = readOnly ? 3 : 1;
  for (let attempt = 0; attempt < attempts; attempt++) {
    let response: Response;
    try {
      response = await fetch(path, {
        ...options,
        cache: "no-store",
        signal:
          options?.signal ??
          (readOnly ? AbortSignal.timeout(45000) : undefined),
        headers: { "Content-Type": "application/json", ...options?.headers },
      });
    } catch {
      if (attempt + 1 < attempts && !options?.signal?.aborted) {
        await new Promise((resolve) =>
          setTimeout(resolve, 800 * (attempt + 1)),
        );
        continue;
      }
      throw new Error(
        readOnly
          ? "Connection to the server failed after retrying. Keep the backend running and click Retry."
          : "The call request could not be confirmed. Refresh Conversations before trying again to avoid duplicate calls.",
      );
    }
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      if ([502, 503, 504].includes(response.status) && attempt + 1 < attempts) {
        await new Promise((resolve) =>
          setTimeout(resolve, 800 * (attempt + 1)),
        );
        continue;
      }
      throw new Error(
        typeof data.detail === "string"
          ? data.detail
          : `Server connection failed (HTTP ${response.status}). Keep the backend running and click Retry.`,
      );
    }
    return response.json();
  }
  throw new Error("Could not load company data. Please retry.");
}
let dashboardRequest: Promise<Dashboard> | null = null;
export const api = {
  dashboard: (refresh = false) => {
    if (!dashboardRequest) {
      dashboardRequest = request<Dashboard>(
        `/api/dashboard${refresh ? "?refresh=true" : ""}`,
      ).finally(() => {
        dashboardRequest = null;
      });
    }
    return dashboardRequest;
  },
  call: (id: string) => request<Call>(`/api/calls/${encodeURIComponent(id)}`),
  outreach: (candidate_ids: string[], agent_id: string, confirmed: boolean) =>
    request<{ message: string; mode: string }>("/api/outreach", {
      method: "POST",
      body: JSON.stringify({ candidate_ids, agent_id, confirmed }),
    }),
};
