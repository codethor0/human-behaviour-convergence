// SPDX-License-Identifier: PROPRIETARY
/**
 * Canonical API base URL configuration and helpers.
 *
 * Single source of truth for all API calls.
 * Do not hardcode API URLs elsewhere.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8100";

// RequestInit is a built-in TypeScript type from the Fetch API
// No explicit import needed - it's part of lib.dom.d.ts

export interface Region {
  id: string;
  name: string;
  country: string;
  region_type: string;
  latitude: number;
  longitude: number;
  region_group?: string;
}

export interface ForecastRequest {
  latitude: number;
  longitude: number;
  region_name: string;
  days_back: number;
  forecast_horizon: number;
  region_id?: string;
}

export async function api<T>(
  path: string,
  // eslint-disable-next-line no-undef
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;

  let res: Response;
  try {
    res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
  } catch (networkError: unknown) {
    // Catch network errors (CORS failures, connection refused, etc.)
    const errorMessage =
      networkError instanceof Error
        ? networkError.message
        : String(networkError);
    throw new Error(
      `Network error: ${errorMessage} — Check that backend is running at ${API_BASE} and CORS is configured correctly`
    );
  }

  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = body.detail ?? body.error ?? JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(
      `Request failed ${res.status}: ${res.statusText}${detail ? ` — ${detail}` : ""}`
    );
  }

  return (await res.json()) as T;
}

export async function fetchRegions(): Promise<Region[]> {
  return api<Region[]>("/api/forecasting/regions");
}

export async function fetchDataSources(): Promise<any[]> {
  return api<any[]>("/api/forecasting/data-sources");
}

export async function runForecast(body: ForecastRequest): Promise<any> {
  return api<any>("/api/forecast", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
