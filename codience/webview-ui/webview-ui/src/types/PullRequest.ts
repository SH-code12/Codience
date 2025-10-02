import type { RiskType } from "./RiskType";

export interface PullRequest {
  number: number;
  title: string;
  state: string;
  // auhtor: string,
  // status: string,
  createdAt: string;
  name: string;
  risk: RiskType | null;
  // priority_score: number,
}
