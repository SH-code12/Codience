import { NavLink } from "react-router-dom";
import "./styles/SideBar.css";
const SideBar = () => {
  return (
    <div className="sideBar">
      <h2 className="logo">Codience</h2>
      <nav className="navBar">
        <NavLink to="/home">Home</NavLink>
        <NavLink to="/dashboard">Dashboard</NavLink>
        <NavLink to="/reviewers">Reviewers Analytics</NavLink>
        <NavLink to="/profile">Profile</NavLink>
        <NavLink to="/getRepo">Change Repo</NavLink>
      </nav>
      <button className="signOut">Sign Out</button>
    </div>
  );
};

export default SideBar;
