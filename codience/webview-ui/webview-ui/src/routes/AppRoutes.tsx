import { Routes, Route, Navigate } from "react-router-dom";
import WelcomePage from "../pages/WelcomePage";
import UserCode from "../components/ui/UserCode";
import JiraLogin from "../pages/JiraLogin";
import JiraProjectName from "../pages/JiraProjectName";
import GetRepoName from "../pages/GetRepoName";
import SideBarLayout from "../pages/SideBarLayout";
import Home from "../pages/Home";
import ReviewersAnalytics from "../pages/ReviewersAnalytics";
import ReviewerRecommendationSettings from "../pages/ReviewerRecommendationSettings";
import Profile from "../pages/Profile";
import PrSummaryDetails from "../pages/PrSummaryDetails";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<WelcomePage />} />
      <Route path="/signIn" element={<UserCode />} />
      <Route path="/jira-login" element={<JiraLogin />} />
      <Route path="/jira-project" element={<JiraProjectName />} />
      <Route path="/getRepo" element={<GetRepoName />} />

      <Route element={<SideBarLayout />}>
        <Route path="/home" element={<Home />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/dashboard" element={<Home />}>
          <Route path="pr-summary/:prNumber" element={<PrSummaryDetails />} />
          <Route
            path="reviewer-settings/:prNumber"
            element={<ReviewerRecommendationSettings />}
          />
        </Route>
        <Route path="/reviewersAnalytics" element={<ReviewersAnalytics />} />
        <Route
          path="/reviewer-settings/:prNumber"
          element={<ReviewerRecommendationSettings />}
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
