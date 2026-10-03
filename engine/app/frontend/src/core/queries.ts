import { useQuery } from '@tanstack/react-query';
import { api } from './api';

export const useHealth = () => useQuery({ queryKey: ['health'], queryFn: api.health });
export const useFirms = () => useQuery({ queryKey: ['firms'], queryFn: api.firms });
export const useFirm = (id: string | undefined) =>
  useQuery({ queryKey: ['firm', id], queryFn: () => api.firm(id!), enabled: !!id });
export const useTalkWalkFirmYears = () =>
  useQuery({ queryKey: ['talkwalk', 'firm-years'], queryFn: api.talkwalkFirmYears });
export const useTalkWalkDocuments = (firmId?: string) =>
  useQuery({
    queryKey: ['talkwalk', 'documents', firmId],
    queryFn: () => api.talkwalkDocuments(firmId),
  });
export const useGreenness = (year?: number, provider?: string) =>
  useQuery({
    queryKey: ['greenness', year, provider],
    queryFn: () => api.greenness(year, provider),
  });
export const useGmb = () => useQuery({ queryKey: ['gmb'], queryFn: api.gmb });
export const useMethod = () => useQuery({ queryKey: ['method'], queryFn: api.method });
export const usePipelineDefault = () =>
  useQuery({ queryKey: ['pipeline', 'default'], queryFn: api.pipelineDefault });
export const usePipelineConfigs = () =>
  useQuery({ queryKey: ['pipeline', 'configs'], queryFn: api.pipelineConfigs });
export const usePipelineRun = (id: string | null) =>
  useQuery({
    queryKey: ['pipeline', 'run', id],
    queryFn: () => api.pipelineRun(id!),
    enabled: !!id,
    refetchInterval: (q) =>
      q.state.data && ['done', 'failed'].includes(q.state.data.status) ? false : 1500,
  });
export const usePipelineAgents = () =>
  useQuery({ queryKey: ['pipeline', 'agents'], queryFn: api.pipelineAgents });
