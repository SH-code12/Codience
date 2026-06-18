import axios from "axios";

const JIRA_LOGIN_URL = "http://localhost:5051/api/Jira/login";
const JIRA_EXCHANGE_URL = "http://localhost:5051/api/Jira/exchange";

export interface JiraLoginResponse {
  url?: string;
}

export interface JiraProject {
  key: string;
  name: string;
}

export interface JiraExchangeResponse {
  accessToken: string;
  cloudId: string;
  projects?: JiraProject[];
}

export const jiraService = {
  async fetchLoginUrl(): Promise<string> {
    const response = await axios.get<JiraLoginResponse>(JIRA_LOGIN_URL);

    if (!response.data?.url) {
      throw new Error("Jira login response did not include a redirect URL.");
    }

    return response.data.url;
  },

  async exchangeCode(code: string): Promise<JiraExchangeResponse> {
    const response = await axios.post<JiraExchangeResponse>(JIRA_EXCHANGE_URL, {
      code,
    });

    if (!response.data.accessToken || !response.data.cloudId) {
      throw new Error("Jira exchange response did not include token data.");
    }

    return response.data;
  },

  storeSession(data: JiraExchangeResponse) {
    localStorage.setItem("JiraAccessToken", data.accessToken);
    localStorage.setItem("JiraCloudId", data.cloudId);
  },

  storeProjectKey(projectKey: string) {
    localStorage.setItem("JiraProjectKey", projectKey);
  },

  clearSession() {
    localStorage.removeItem("JiraAccessToken");
    localStorage.removeItem("JiraCloudId");
    localStorage.removeItem("JiraProjectKey");
  },

  getCodeFromSearch(search: string = window.location.search) {
    return new URLSearchParams(search).get("code");
  },
};

export default jiraService;