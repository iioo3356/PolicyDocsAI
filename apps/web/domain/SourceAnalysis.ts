export type SourceAnalysis = {
  source_id: string;
  status: string;
  stage: string;
  progress: number;
  current_file?: string | null;
  current_policy_title?: string | null;
  processed_files: number;
  total_files: number;
  candidates: { id: string; title: string; category: string; confidence: number }[];
};
