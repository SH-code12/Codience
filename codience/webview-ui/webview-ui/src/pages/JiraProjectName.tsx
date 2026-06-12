import { useLocation, useNavigate } from "react-router-dom";
import { useMemo, useState } from "react";
import "./styles/GetRepoName.css";
import jiraService, { type JiraProject } from "../services/jiraService";

interface JiraProjectLocationState {
  projects?: JiraProject[];
}

const JiraProjectName = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState("");
  const [selectedProject, setSelectedProject] = useState<JiraProject | null>(null);
  const [error, setError] = useState<string | null>(null);

  const projects = (location.state as JiraProjectLocationState | null)?.projects ?? [];

  const matches = useMemo(() => {
    const search = query.trim().toLowerCase();

    if (!search) return [];

    return projects.filter((project) => {
      const projectName = project.name?.toLowerCase() ?? "";

      return projectName.includes(search);
    });
  }, [projects, query]);

  const pickProject = (project: JiraProject) => {
    setSelectedProject(project);
    setQuery(project.name);
    setError(null);
  };

  const submit = () => {
    if (!selectedProject) {
      setError("Select a Jira project first.");
      return;
    }

    jiraService.storeProjectKey(selectedProject.key);
    navigate("/home");
  };

  return (
    <div className="getRepoName">
      <div className="repoNameContainer">
        <h3>Select Jira Project</h3>

        <div className="repoSearchBox">
          <input
            type="text"
            value={query}
            onChange={(e) => {
              const value = e.currentTarget.value;
              setQuery(value);
              setSelectedProject(null);
              setError(null);
            }}
            placeholder="Project Name..."
            aria-label="Search Jira projects"
            autoComplete="off"
          />

          {query.trim().length > 0 && (
            <div className="repoMenu" role="listbox" aria-label="Jira project suggestions">
              {projects.length === 0 && (
                <div className="repoMenuState">No Jira projects returned.</div>
              )}
              {projects.length > 0 && matches.length === 0 && (
                <div className="repoMenuState">No matching Jira projects found.</div>
              )}
              {matches.map((project) => {
                return (
                  <button
                    key={project.key}
                    type="button"
                    className="repoMenuItem"
                    onMouseDown={(event) => {
                      event.preventDefault();
                      pickProject(project);
                    }}
                  >
                    <span className="repoMenuItemTitle">{project.name}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <button onClick={submit} disabled={!selectedProject}>
          Continue
        </button>

        {error && <div className="repoMenuState repoMenuError">{error}</div>}
      </div>
    </div>
  );
};

export default JiraProjectName;