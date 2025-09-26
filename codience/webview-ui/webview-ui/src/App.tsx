import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "./App.css";
import SideBar from "./components/SideBar";
import Home from "./pages/Home";
import Welcome from "./components/Welcome";

function App() {
  return (
    <>
      <BrowserRouter>
        <SideBar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={<Welcome />} />
          <Route path="*" element={<Navigate to='/'replace /> } />
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
