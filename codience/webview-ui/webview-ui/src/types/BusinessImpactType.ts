export interface BusinessImpactType {
  weighted_score: number | string;
  tier: string;
  should_block_merge?: boolean;
  ai_summary?: string;
  score_breakdown?: {
    blast_radius?: number;
    user_exposure?: number;
    deadline?: number;
    business_impact?: number;
    formula_score?: number;
    local_model_score?: number;
  };
}
