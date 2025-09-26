export interface PullRequest {
    pr_id: number,
    pr_title: string,
    repo_id: number,
    auhtor: string,
    status: string,
    risk_score: number,
    priority_score: number,
}