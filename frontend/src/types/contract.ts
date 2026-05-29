export interface NamedEntity {
  text: string;
  label: string;
}

export interface ContractIssue {
  description: string;
  risk_level?: string;
  legal_basis?: string;
  clause_snippet?: string;
  similarity?: number;
  // New fields from LLM judge
  confidence?: number;
  exact_quote?: string;
  legal_citation?: string;
  detection_method?: string; // "rule_based" | "llm" | "ocr_error"
}

export interface ContractAnalysisResult {
  word_count: number;
  sentences: number;
  key_terms: string[];
  entities: NamedEntity[];
  issues: ContractIssue[];
}

export interface ContractAnalysisResponse {
  filename: string;
  contract_id: number;
  processing_method: string;
  ocr_used: string;
  processing_time_seconds: number;
  analysis: ContractAnalysisResult;
}

export interface ErrorResponse {
  detail: string;
  status_code?: number;
}

export type UploadState = 'idle' | 'uploading' | 'analyzing' | 'success' | 'error';