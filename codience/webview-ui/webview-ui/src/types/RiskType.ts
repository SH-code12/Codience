export interface RiskType {
  risk_score: number | string;
  risk_level: string;
  comments?: number;
  files_changed?: number;
}
