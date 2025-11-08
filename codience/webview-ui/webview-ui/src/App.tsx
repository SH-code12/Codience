import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./App.css";
import UserCode from "./components/UserCode";
import WelcomePage from "./pages/WelcomePage";
import Home from "./pages/Home";
import GetRepoName from "./pages/GetRepoName";
import SideBarLayout from "./pages/SideBarLayout";

function App() {
  return (
    <>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<WelcomePage />} />
          <Route path="/signIn" element={<UserCode />} />
          <Route path="/getRepo" element={<GetRepoName />} />

          <Route element={<SideBarLayout />}>
            <Route path="/home" element={<Home />} />
            <Route path="/dashboard" element={<Home />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
