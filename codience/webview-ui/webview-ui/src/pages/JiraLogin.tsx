import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./styles/JiraLogin.css";
import jiraService from "../services/jiraService.ts";

const JiraLogin = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const exchangeStartedRef = useRef(false);

  const exchangeCode = async (code: string) => {
    if (exchangeStartedRef.current) {
      return;
    }

    exchangeStartedRef.current = true;
    setLoading(true);
    setError(null);

    try {
      const data = await jiraService.exchangeCode(code);

      jiraService.storeSession(data);

      navigate("/jira-project", {
        state: {
          projects: data.projects ?? [],
        },
      });
    } catch (exchangeError: any) {
      exchangeStartedRef.current = false;
      setError(exchangeError?.message || "Failed to exchange Jira authorization code.");
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    try {
      setLoading(true);
      setError(null);

      const url = await jiraService.fetchLoginUrl();

      window.location.assign(url);
    } catch (loginError: any) {
      setError(loginError?.message || "Failed to start Jira login.");
    } finally {
      setLoading(false);
    }
  };

  const handleAuthenticateLater = () => {
    jiraService.clearSession();
    navigate("/home");
  };

  useEffect(() => {
    const searchForCode = () => {
      const code = jiraService.getCodeFromSearch();

      if (code) {
        void exchangeCode(code);
        return true;
      }

      return false;
    };

    if (searchForCode()) {
      return;
    }

    const intervalId = window.setInterval(() => {
      searchForCode();
    }, 500);

    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

  return (
    <div className="jiraLoginPage">
      <div className="deviceCodeContainer">
        <button
          type="button"
          className="jiraLoginButton"
          onClick={handleLogin}
          disabled={loading}
        >
          {loading ? "Opening Jira..." : "Continue to Jira"}
        </button>

        <button
          type="button"
          className="jiraLoginSecondaryButton"
          onClick={handleAuthenticateLater}
          disabled={loading}
        >
          Authenticate with Jira later
        </button>

        {error && <p className="errorText">{error}</p>}
      </div>
    </div>
  );
};

export default JiraLogin;