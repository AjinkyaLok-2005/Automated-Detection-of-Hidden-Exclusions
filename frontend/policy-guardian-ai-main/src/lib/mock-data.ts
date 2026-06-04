import type { AnalysisResponse } from './api';

// Mock data updated to match the real API response schema
export const mockAnalysis: AnalysisResponse = {
  filename: 'health_insurance_premium_2024.pdf',
  total_clauses: 47,
  processing_time_s: 12.34,

  risk_score: 0.73,
  risk_level: 'High',
  risk_breakdown: {
    clause_risk_score: 0.65,
    contradiction_risk_score: 0.82,
    hidden_risk_score: 0.71,
  },

  label_distribution: { Coverage: 6, Exclusion: 5, Condition: 4, Normal: 32 },
  exclusion_count: 5,
  coverage_count: 6,
  condition_count: 4,
  normal_count: 32,

  contradiction_count: 3,
  high_conf_contradictions: 2,
  avg_contradiction_confidence: 0.77,

  hidden_conditions_total: 3,
  hidden_high_severity: 1,
  hidden_medium_severity: 1,
  hidden_low_severity: 1,

  coverage_clauses: [
    { clause_text: 'The insurer shall cover all hospitalization expenses including room rent, nursing, and surgical fees up to the sum insured.', label_id: 1, label_name: 'Coverage', confidence: 0.96, risk_weight: 0.1, is_contradiction: true, contradiction_score: 0.87, section_heading: 'COVERAGE', page_number: 3, source_file: 'health_insurance_premium_2024.pdf' },
    { clause_text: 'Outpatient diagnostic tests prescribed by an in-network physician are covered at 80% of the billed amount.', label_id: 1, label_name: 'Coverage', confidence: 0.94, risk_weight: 0.1, is_contradiction: false, contradiction_score: 0, section_heading: 'COVERAGE', page_number: 5, source_file: 'health_insurance_premium_2024.pdf' },
    { clause_text: 'Emergency ambulance services within a 50-mile radius of the insured\'s residence are fully covered.', label_id: 1, label_name: 'Coverage', confidence: 0.91, risk_weight: 0.1, is_contradiction: true, contradiction_score: 0.79, section_heading: 'EMERGENCY SERVICES', page_number: 7, source_file: 'health_insurance_premium_2024.pdf' },
    { clause_text: 'Mental health counseling sessions are covered up to 20 visits per policy year.', label_id: 1, label_name: 'Coverage', confidence: 0.89, risk_weight: 0.1, is_contradiction: true, contradiction_score: 0.65, section_heading: 'MENTAL HEALTH', page_number: 8, source_file: 'health_insurance_premium_2024.pdf' },
    { clause_text: 'Prescription medications listed in the formulary are covered with applicable copayments.', label_id: 1, label_name: 'Coverage', confidence: 0.93, risk_weight: 0.1, is_contradiction: false, contradiction_score: 0, section_heading: 'PRESCRIPTIONS', page_number: 10, source_file: 'health_insurance_premium_2024.pdf' },
    { clause_text: 'Preventive care including annual physicals and vaccinations are covered at no additional cost.', label_id: 1, label_name: 'Coverage', confidence: 0.97, risk_weight: 0.1, is_contradiction: false, contradiction_score: 0, section_heading: 'PREVENTIVE CARE', page_number: 4, source_file: 'health_insurance_premium_2024.pdf' },
  ],
  exclusion_clauses: [
    { clause_text: 'Pre-existing conditions diagnosed within 48 months prior to the policy start date are excluded from coverage for the first 24 months.', label_id: 2, label_name: 'Exclusion', confidence: 0.98, risk_weight: 0.7, is_contradiction: true, contradiction_score: 0.87, section_heading: 'EXCLUSIONS', page_number: 12, source_file: 'health_insurance_premium_2024.pdf' },
    { clause_text: 'Cosmetic surgery and elective procedures not deemed medically necessary are excluded.', label_id: 2, label_name: 'Exclusion', confidence: 0.95, risk_weight: 0.7, is_contradiction: false, contradiction_score: 0, section_heading: 'EXCLUSIONS', page_number: 14, source_file: 'health_insurance_premium_2024.pdf' },
    { clause_text: 'Treatment received outside the approved provider network without prior authorization is not covered.', label_id: 2, label_name: 'Exclusion', confidence: 0.92, risk_weight: 0.7, is_contradiction: true, contradiction_score: 0.79, section_heading: 'EXCLUSIONS', page_number: 15, source_file: 'health_insurance_premium_2024.pdf' },
    { clause_text: 'Injuries sustained while participating in extreme sports or hazardous activities are excluded.', label_id: 2, label_name: 'Exclusion', confidence: 0.90, risk_weight: 0.7, is_contradiction: false, contradiction_score: 0, section_heading: 'EXCLUSIONS', page_number: 16, source_file: 'health_insurance_premium_2024.pdf' },
    { clause_text: 'Experimental or investigational treatments not approved by regulatory authorities are excluded.', label_id: 2, label_name: 'Exclusion', confidence: 0.94, risk_weight: 0.7, is_contradiction: true, contradiction_score: 0.65, section_heading: 'EXCLUSIONS', page_number: 17, source_file: 'health_insurance_premium_2024.pdf' },
  ],
  condition_clauses: [
    { clause_text: 'The policyholder must notify the insurer within 48 hours of any hospitalization to be eligible for cashless treatment.', label_id: 3, label_name: 'Condition', confidence: 0.93, risk_weight: 0.4, is_contradiction: false, contradiction_score: 0, section_heading: 'CONDITIONS', page_number: 20, source_file: 'health_insurance_premium_2024.pdf' },
    { clause_text: 'Claims must be submitted within 30 days of discharge along with all original medical documents.', label_id: 3, label_name: 'Condition', confidence: 0.91, risk_weight: 0.4, is_contradiction: false, contradiction_score: 0, section_heading: 'CONDITIONS', page_number: 21, source_file: 'health_insurance_premium_2024.pdf' },
    { clause_text: 'Annual health check-up is mandatory to maintain the no-claim bonus benefit.', label_id: 3, label_name: 'Condition', confidence: 0.88, risk_weight: 0.4, is_contradiction: false, contradiction_score: 0, section_heading: 'CONDITIONS', page_number: 22, source_file: 'health_insurance_premium_2024.pdf' },
    { clause_text: 'The insured must obtain pre-authorization for any planned surgical procedure exceeding $5,000.', label_id: 3, label_name: 'Condition', confidence: 0.90, risk_weight: 0.4, is_contradiction: false, contradiction_score: 0, section_heading: 'CONDITIONS', page_number: 23, source_file: 'health_insurance_premium_2024.pdf' },
  ],
  hidden_conditions: [
    {
      detection_type: 'NLI Contradiction',
      severity: 'High',
      risk_reason: 'Coverage for all hospitalization is directly contradicted by the 48-month pre-existing condition exclusion.',
      coverage_text: 'The insurer shall cover all hospitalization expenses including room rent.',
      exclusion_text: 'Pre-existing conditions diagnosed within 48 months prior are excluded for the first 24 months.',
      contradiction_score: 0.87,
      similarity_score: 0.82,
      same_document: true,
    },
    {
      detection_type: 'Semantic Match',
      severity: 'Medium',
      risk_reason: 'Emergency coverage is undermined by strict network provider restrictions.',
      coverage_text: 'Emergency ambulance services within a 50-mile radius are fully covered.',
      exclusion_text: 'Treatment received outside the approved provider network without prior authorization is not covered.',
      contradiction_score: 0.79,
      similarity_score: 0.75,
      same_document: true,
    },
    {
      detection_type: 'NLI Contradiction',
      severity: 'Low',
      risk_reason: 'Mental health coverage may be limited by experimental treatment exclusion.',
      coverage_text: 'Mental health counseling sessions are covered up to 20 visits per policy year.',
      exclusion_text: 'Experimental or investigational treatments not approved by regulatory authorities are excluded.',
      contradiction_score: 0.65,
      similarity_score: 0.60,
      same_document: true,
    },
  ],

  report_txt_url: '/api/v1/report/risk_report_health_insurance.txt',
};

export const recentAnalyses: Array<{
  id: string;
  fileName: string;
  date: string;
  riskScore: number;
  riskLevel: string;
}> = [
  { id: '1', fileName: 'health_insurance_premium_2024.pdf', date: '2026-04-14', riskScore: 0.73, riskLevel: 'High' },
  { id: '2', fileName: 'auto_coverage_standard.pdf', date: '2026-04-13', riskScore: 0.42, riskLevel: 'Medium' },
  { id: '3', fileName: 'home_owners_policy_v3.pdf', date: '2026-04-12', riskScore: 0.18, riskLevel: 'Low' },
  { id: '4', fileName: 'life_insurance_term_30.pdf', date: '2026-04-11', riskScore: 0.91, riskLevel: 'Very High' },
  { id: '5', fileName: 'travel_insurance_intl.pdf', date: '2026-04-10', riskScore: 0.55, riskLevel: 'Medium' },
  { id: '6', fileName: 'pet_insurance_comprehensive.pdf', date: '2026-04-09', riskScore: 0.31, riskLevel: 'Low' },
];
