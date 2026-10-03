// Typed client for the FastAPI service in src/esgx/api.
import type {
  Firm,
  FirmProfile,
  GmbResponse,
  GreennessResponse,
  Health,
  TalkWalkDocument,
  TalkWalkYear,
} from './types';
import type {
  AgentInfo,
  Estimate,
  MethodSnapshot,
  PipelineSpec,
  RunDetail,
  RunMode,
  RunSummary,
  SavedConfig,
  ToolInfo,
} from './pipelineTypes';

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '';

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const j = (await res.json()) as { detail?: string };
      if (j.detail) detail = j.detail;
    } catch {
      /* keep status text */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

async function get<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
): Promise<T> {
  const url = new URL(BASE + path, window.location.origin);
  Object.entries(params ?? {}).forEach(
    ([k, v]) => v !== undefined && url.searchParams.set(k, String(v)),
  );
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<Health>('/api/health'),
  firms: () => get<Firm[]>('/api/firms'),
  firm: (id: string) => get<FirmProfile>(`/api/firms/${encodeURIComponent(id)}`),
  talkwalkFirmYears: () => get<TalkWalkYear[]>('/api/talkwalk/firm-years'),
  talkwalkDocuments: (firmId?: string) =>
    get<TalkWalkDocument[]>('/api/talkwalk/documents', { firm_id: firmId }),
  greenness: (year?: number, provider?: string) =>
    get<GreennessResponse>('/api/greenness', { year, provider }),
  gmb: () => get<GmbResponse>('/api/gmb'),
  search: (q: string) => get<Firm[]>('/api/search', { q }),
  method: () => get<MethodSnapshot>('/api/method'),
  pipelineDefault: () => get<PipelineSpec>('/api/pipeline/default'),
  pipelineConfigs: () => get<SavedConfig[]>('/api/pipeline/configs'),
  pipelineSave: (name: string, spec: PipelineSpec) =>
    post<{ saved: string }>('/api/pipeline/configs', { name, spec }),
  pipelineEstimate: (spec: PipelineSpec, tickers: string[]) =>
    post<Estimate>('/api/pipeline/estimate', { spec, tickers }),
  pipelineStart: (spec: PipelineSpec, tickers: string[], mode: RunMode, confirm_cost = false) =>
    post<RunSummary>('/api/pipeline/runs', { spec, tickers, mode, confirm_cost }),
  pipelineRuns: () => get<RunSummary[]>('/api/pipeline/runs'),
  pipelineRun: (id: string) => get<RunDetail>(`/api/pipeline/runs/${id}`),
  pipelineAgents: () => get<AgentInfo[]>('/api/pipeline/agents'),
  pipelineTools: () => get<ToolInfo[]>('/api/pipeline/tools'),
};

export type * from './types';
export type * from './pipelineTypes';
