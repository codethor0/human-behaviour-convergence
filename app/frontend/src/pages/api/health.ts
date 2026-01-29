import type { NextApiRequest, NextApiResponse } from 'next';

interface HealthResponse {
  status: string;
  duration_ms: number;
  uptime: number;
  timestamp: string;
  version: string;
  checks: {
    backend: { status: string; response_time_ms?: number; error?: string };
    grafana: { status: string; error?: string };
    prometheus: { status: string; error?: string };
  };
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<HealthResponse | { status: string; error: string }>
) {
  const start = Date.now();

  if (req.method !== 'GET') {
    return res.status(405).json({ status: 'error', error: 'Method not allowed' });
  }

  try {
    const checks = {
      backend: await checkBackend(),
      grafana: await checkGrafana(),
      prometheus: await checkPrometheus(),
    };

    const duration = Date.now() - start;

    const response: HealthResponse = {
      status: 'healthy',
      duration_ms: duration,
      uptime: process.uptime(),
      timestamp: new Date().toISOString(),
      version: process.env.npm_package_version || 'unknown',
      checks,
    };

    const allHealthy = Object.values(checks).every(
      (check) => check.status === 'pass'
    );

    return res.status(allHealthy ? 200 : 503).json(response);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    return res.status(503).json({
      status: 'unhealthy',
      error: message,
    });
  }
}

async function checkBackend(): Promise<{
  status: string;
  response_time_ms?: number;
  error?: string;
}> {
  try {
    const start = Date.now();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1000);

    const resp = await fetch('http://localhost:8100/health', {
      signal: controller.signal as AbortSignal,
    });
    clearTimeout(timeout);

    const duration = Date.now() - start;
    return {
      status: resp.status === 200 ? 'pass' : 'fail',
      response_time_ms: duration,
    };
  } catch (err: unknown) {
    return {
      status: 'fail',
      error: err instanceof Error && err.name === 'AbortError' ? 'timeout' : (err instanceof Error ? err.message : 'Unknown'),
    };
  }
}

async function checkGrafana(): Promise<{
  status: string;
  error?: string;
}> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1000);

    const resp = await fetch('http://localhost:3001/api/health', {
      signal: controller.signal as AbortSignal,
    });
    clearTimeout(timeout);

    return {
      status: resp.ok ? 'pass' : 'fail',
    };
  } catch (err: unknown) {
    return {
      status: 'fail',
      error: err instanceof Error && err.name === 'AbortError' ? 'timeout' : (err instanceof Error ? err.message : 'Unknown'),
    };
  }
}

async function checkPrometheus(): Promise<{
  status: string;
  error?: string;
}> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 1000);

    const resp = await fetch('http://localhost:9090/-/ready', {
      signal: controller.signal as AbortSignal,
    });
    clearTimeout(timeout);

    return {
      status: resp.ok ? 'pass' : 'fail',
    };
  } catch (err: unknown) {
    return {
      status: 'fail',
      error: err instanceof Error && err.name === 'AbortError' ? 'timeout' : (err instanceof Error ? err.message : 'Unknown'),
    };
  }
}
