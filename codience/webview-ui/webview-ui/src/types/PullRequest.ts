import type { RiskType } from "./RiskType";
import type { BusinessImpactType } from "./BusinessImpactType";

export interface PullRequest {
  number: number;
  title: string;
  state: string;
  createdAt: string;
  name: string;
  files_changed: number | string;
  risk: RiskType | null;
  business_impact: BusinessImpactType | null;
}
