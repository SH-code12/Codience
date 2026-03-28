import { Routes, Route, Navigate } from "react-router-dom";
import WelcomePage from "../pages/WelcomePage";
import UserCode from "../components/ui/UserCode";
import GetRepoName from "../pages/GetRepoName";
import SideBarLayout from "../pages/SideBarLayout";
import Home from "../pages/Home";
import ReviewersAnalytics from "../pages/ReviewersAnalytics";
import SignUpPage from "../pages/SignUpPage";
import LoginPage from "../pages/LoginPage";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<WelcomePage />} />
      <Route path="/signIn" element={<UserCode />} />
      <Route path="/signUp" element={<SignUpPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/getRepo" element={<GetRepoName />} />

      <Route element={<SideBarLayout />}>
        <Route path="/home" element={<Home />} />
        <Route path="/dashboard" element={<Home />} />
        <Route path="/reviewersAnalytics" element={<ReviewersAnalytics />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
