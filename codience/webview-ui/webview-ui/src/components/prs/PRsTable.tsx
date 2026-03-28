import { useEffect, useMemo, useState, useRef } from "react";
import type { PullRequest } from "../../types/PullRequest";
import "../styles/PRsTable.css";
import PRRow from "./PRRow";

type Props = {
  prs: PullRequest[] | null;
  onSelect?: (pr: PullRequest) => void;
  onRiskUpdate?: (updated: PullRequest[]) => void;
  onVisibleChange?: (visible: PullRequest[]) => void;
  // NOTE: PRsTable manages its own filter/sort controls locally
};

type FileData = {
  additions: number;
  deletions: number;
  changes: number;
};

const PRsTable = ({ prs, onSelect, onRiskUpdate, onVisibleChange }: Props) => {
  if (!prs) return null;

  const [updatedPRs, setUpdatedPRs] = useState<PullRequest[]>(() =>
    prs.map((pr) => ({
      ...pr,
      files_changed: pr.files_changed ?? 0,
      risk:
        pr.risk ??
        ({
          risk_score: "Loading...",
          risk_level: "unknown",
          comments: 0,
          files_changed: 0,
        } as any),
    })),
  );

  // Local filtering and sorting state (controls rendered above table)
  const [filterRisk, setFilterRisk] = useState<
    "all" | "low" | "medium" | "high"
  >("all");
  const [filterStatus, setFilterStatus] = useState<"all" | "open" | "closed">(
    "all",
  );
  const [sortBy, setSortBy] = useState<"none" | "risk" | "title" | "files">(
    "none",
  );
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const [selectedPR, setSelectedPR] = useState<number | null>(null);

  const repoName = localStorage.getItem("RepoName");
  const userName = localStorage.getItem("User");

  const prsRef = useRef(prs);
  prsRef.current = prs;

  const handleSelect = (pr: PullRequest) => {
    setSelectedPR(pr.number);
    onSelect?.(pr);
  };

  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const visiblePRs = useMemo(() => {
    let list = [...updatedPRs];

    // Apply risk filter
    if (filterRisk !== "all") {
      list = list.filter(
        (p) => (p.risk?.risk_level ?? "unknown") === filterRisk,
      );
    }

    // Apply status filter
    if (filterStatus !== "all") {
      list = list.filter((p) => (p.state ?? "").toLowerCase() === filterStatus);
    }

    // Sorting
    if (sortBy !== "none") {
      list.sort((a, b) => {
        let res = 0;
        if (sortBy === "risk") {
          const map = (lvl?: string) =>
            lvl === "high" ? 3 : lvl === "medium" ? 2 : lvl === "low" ? 1 : 0;
          res = map(a.risk?.risk_level) - map(b.risk?.risk_level);
        } else if (sortBy === "title") {
          res = (a.title ?? "").localeCompare(b.title ?? "");
        } else if (sortBy === "files") {
          res = (a.files_changed ?? 0) - (b.files_changed ?? 0);
        }
        return sortDir === "asc" ? res : -res;
      });
    }

    return list;
  }, [updatedPRs, filterRisk, filterStatus, sortBy, sortDir]);

  useEffect(() => {
    onVisibleChange?.(visiblePRs);
  }, [visiblePRs, onVisibleChange]);

  const totalPages = Math.max(1, Math.ceil(visiblePRs.length / pageSize));

  const startIndex = (currentPage - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const pageItems = visiblePRs.slice(startIndex, endIndex);

  const goToPage = (p: number) => {
    const next = Math.max(1, Math.min(totalPages, p));
    setCurrentPage(next);
  };

  return (
    <div>
      <div
        style={{ display: "flex", justifyContent: "flex-end", marginBottom: 8 }}
      >
        <div className="prsControls">
          <label>
            Risk:
            <select
              value={filterRisk}
              onChange={(e) => {
                setFilterRisk(e.target.value as any);
                setCurrentPage(1);
              }}
            >
              <option value="all">All</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </label>
          <label>
            Status:
            <select
              value={filterStatus}
              onChange={(e) => {
                setFilterStatus(e.target.value as any);
                setCurrentPage(1);
              }}
            >
              <option value="all">All</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
            </select>
          </label>
          <label>
            Sort:
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
            >
              <option value="none">None</option>
              <option value="risk">Risk Level</option>
              <option value="title">Title</option>
              <option value="files">Files Changed</option>
            </select>
          </label>
          <button
            className="sortDir"
            onClick={() => setSortDir((s) => (s === "asc" ? "desc" : "asc"))}
          >
            {sortDir === "asc" ? "↑" : "↓"}
          </button>
        </div>
      </div>

      <div className="prsTableContainer">
        <table className="prsTable">
          <thead>
            <tr>
              <th>PR Title</th>
              <th>Risk Score</th>
              <th>Risk Level</th>
              <th>Files Changed</th>
              <th>Comments</th>
              <th>Created At</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {pageItems.map((pr) => (
              <PRRow
                key={pr.number}
                pr={pr}
                selected={selectedPR === pr.number}
                onSelect={handleSelect}
              />
            ))}
          </tbody>
        </table>
      </div>

      <div className="prsPagination">
        <div className="paginationControls">
          <button
            onClick={() => goToPage(currentPage - 1)}
            disabled={currentPage === 1}
          >
            <p className="controls">&lt;</p>
          </button>
          <span className="pageInfo">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => goToPage(currentPage + 1)}
            disabled={currentPage === totalPages}
          >
            <p className="controls">&gt;</p>
          </button>
        </div>
        <div className="pageSizeControl">
          <label>
            Rows:
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </label>
        </div>
      </div>
    </div>
  );
};

export default PRsTable;

type RiskProps = { risk_level: string };

const RiskCell = ({ risk_level }: RiskProps) => {
  if (risk_level === "low") return <td className="riskCell low">Low</td>;
  if (risk_level === "medium") return <td className="riskCell med">Medium</td>;
  if (risk_level === "high") return <td className="riskCell high">High</td>;
  return <td className="riskCell unknown">Unknown</td>;
};
