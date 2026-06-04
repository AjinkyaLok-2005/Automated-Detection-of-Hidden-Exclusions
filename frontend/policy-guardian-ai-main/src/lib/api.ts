import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 300000, // 5 min for large PDFs
});

// ── Types matching FastAPI AnalysisResponse schema ──

export interface ClauseResult {
  clause_text: string;
  label_id: number;
  label_name: string;
  confidence: number;
  risk_weight: number;
  is_contradiction: boolean;
  contradiction_score: number;
  section_heading: string;
  page_number: number;
  source_file: string;
}

export interface HiddenCondition {
  detection_type: string;
  severity: string;
  risk_reason: string;
  coverage_text: string;
  exclusion_text: string;
  contradiction_score: number;
  similarity_score: number;
  same_document: boolean;
}

export interface RiskScoreBreakdown {
  clause_risk_score: number;
  contradiction_risk_score: number;
  hidden_risk_score: number;
}

export interface AnalysisResponse {
  filename: string;
  total_clauses: number;
  processing_time_s: number;

  risk_score: number;
  risk_level: string;
  risk_breakdown: RiskScoreBreakdown;

  label_distribution: Record<string, number>;
  exclusion_count: number;
  coverage_count: number;
  condition_count: number;
  normal_count: number;

  contradiction_count: number;
  high_conf_contradictions: number;
  avg_contradiction_confidence: number;

  hidden_conditions_total: number;
  hidden_high_severity: number;
  hidden_medium_severity: number;
  hidden_low_severity: number;

  coverage_clauses: ClauseResult[];
  exclusion_clauses: ClauseResult[];
  condition_clauses: ClauseResult[];
  hidden_conditions: HiddenCondition[];

  report_txt_url: string | null;
}

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  version: string;
  message: string;
}

export async function uploadAndAnalyze(
  file: File,
  onProgress?: (pct: number) => void
): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post<AnalysisResponse>('/analyze_policy', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (e.total && onProgress) {
        onProgress(Math.round((e.loaded * 100) / e.total));
      }
    },
  });

  return response.data;
}

export async function checkHealth(): Promise<HealthResponse> {
  const response = await api.get<HealthResponse>('/health');
  return response.data;
}

export function getDownloadUrl(path: string): string {
  return `${API_BASE}${path}`;
}

export default api;
