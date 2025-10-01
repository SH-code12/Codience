import { NavLink } from 'react-router-dom'
import './styles/WelcomePage.css'


const WelcomePage = () => {
  return (
    <div className="welcomePage">
      <h2>Welcome to &lt; Codience /&gt;</h2>
      <NavLink to="/signIn">Sign in to GitHub </NavLink>
    </div>
  );
}

export default WelcomePage
