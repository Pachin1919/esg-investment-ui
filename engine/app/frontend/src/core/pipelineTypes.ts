// Types for the method snapshot and the agentic pipeline (agents, tools, runs).
import type { TalkWalkDocument, TalkWalkYear } from './types';

export interface MethodSnapshot {
  rubric_version: string;
  model: string;
  system_prompt: string;
  talk_fields: string[];
  walk_fields: string[];
  talk_weights: Record<string, number>;
  walk_weights: Record<string, number>;
  form_weights: Record<string, number>;
  sections_10k: Record<string, string>;
  min_section_chars: number;
  climate_terms: string[];
  env_terms: string[];
  forward_terms: string[];
  realised_terms: string[];
  custom_score_weights: Record<string, number>;
  sample: { start_year: number; end_year: number; emissions_lag_months: number };
  greenness: { formula: string; e_weight_range: number[]; e_score: string; e_weight: string };
  gmb: { sorted: string; regression: string };
  cost: { usd_per_section: number; usd_per_review: number; basis: string };
}
export interface AgentSpec {
  name: string;
  model: string;
  effort: string;
  role_prompt: string;
}
export type StageKind =
  | 'find_reports'
  | 'find_about_page'
  | 'find_news'
  | 'collect_documents'
  | 'collect_hard_data'
  | 'preprocess'
  | 'score_talkwalk'
  | 'dictionary_measures'
  | 'review'
  | 'aggregate';
export interface StageSpec {
  id: string;
  kind: StageKind;
  name: string;
  description: string;
  enabled: boolean;
  agent: AgentSpec | null;
  params: Record<string, unknown>;
}
export interface PipelineSpec {
  name: string;
  version: string;
  description: string;
  universe: 'us' | 'hk';
  forms: string[];
  start: string;
  max_8k: number;
  stages: StageSpec[];
}
export type RunMode = 'dry_run' | 'cache_only' | 'live';
export interface RunSummary {
  id: string;
  status: 'queued' | 'running' | 'done' | 'failed';
  mode: RunMode;
  tickers: string[];
  started: string;
  finished: string | null;
  error: string | null;
  spec_name: string;
  stages: Record<string, { status: string; seconds?: number; [k: string]: unknown }>;
}
export interface RunDetail extends RunSummary {
  log: { t: string; stage: string; msg: string }[];
  results: {
    firm_years?: TalkWalkYear[];
    documents?: TalkWalkDocument[];
    memos?: { firm_id: string; year: number; memo: string; flags: string[]; model: string }[];
    dir?: string;
  };
  spec: PipelineSpec;
}
export interface Estimate {
  sections: number;
  firm_years: number;
  scorer_usd: number;
  review_usd: number;
  total_usd: number;
}
export interface SavedConfig {
  file: string;
  name: string;
  description?: string;
  stages?: number;
  spec?: PipelineSpec;
  error?: string;
}

export interface ToolInfo {
  name: string;
  description: string;
  kind: 'api' | 'scrape' | 'compute' | 'llm' | 'storage';
  cost: 'free' | 'network' | 'paid';
  params: Record<string, string>;
  module: string;
}
export interface AgentInfo {
  id: string;
  kind: StageKind;
  name: string;
  role: string;
  description: string;
  llm: boolean;
  default_model: string | null;
  default_effort: string;
  default_role_prompt: string;
  inputs: string[];
  outputs: string[];
  tools: ToolInfo[];
  folder: string;
}
