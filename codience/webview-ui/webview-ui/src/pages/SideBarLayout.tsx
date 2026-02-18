import SideBar from "../components/SideBar";
import { Outlet } from "react-router-dom";
import "./styles/SideBarLayout.css";
const SideBarLayout = () => {
  return (
    <div className="sideBarLayout">
      <SideBar />
      <Outlet />
    </div>
  );
};

export default SideBarLayout;
