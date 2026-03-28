import { NavLink } from "react-router-dom";
import "../styles/SideBar.css";
import logo from "../../assets/codience logo (3).png";

const SideBar = () => {
  return (
    <div className="sideBar">
      <img src={logo} alt="Codience Logo" className="logo" />

      <nav className="navBar">
        <NavLink to="/home">Home</NavLink>
        <NavLink to="/dashboard">Dashboard</NavLink>
        <NavLink to="/reviewersAnalytics">Reviewers Analytics</NavLink>
        <NavLink to="/profile">Profile</NavLink>
        <NavLink to="/getRepo">Change Repo</NavLink>
      </nav>

      <button className="signOut">Sign Out</button>
    </div>
  );
};

export default SideBar;
