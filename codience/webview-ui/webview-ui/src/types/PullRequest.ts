import type { RiskType } from "./RiskType";

export interface PullRequest {
  number: number;
  title: string;
  state: string;
  createdAt: string;
  name: string;
  files_changed: number;
  risk: RiskType | null;
}
