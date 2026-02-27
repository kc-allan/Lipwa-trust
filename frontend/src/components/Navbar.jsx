import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import "./Navbar.css";

export default function Navbar() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    try {
      await fetch("http://localhost:8000/auth/logout", { method: "POST", credentials: "include" });
    } catch (_) {}
    setUser(null);
    navigate("/");
  };

  const links = user?.is_merchant
    ? [{ to: "/merchant", label: "Dashboard" }]
    : user?.is_supplier
    ? [{ to: "/supplier", label: "Dashboard" }]
    : [{ to: "/onboard", label: "Get Started" }];

  return (
    <nav className="navbar">
      <Link to="/" className="navbar-logo">⬡ Lipwa Trust</Link>

      <div className="navbar-links">
        {links.map(l => (
          <Link
            key={l.to}
            to={l.to}
            className={`navbar-link ${location.pathname === l.to ? "active" : ""}`}
          >
            {l.label}
          </Link>
        ))}
      </div>

      <div className="navbar-right">
        {user && (
          <>
            <div className="navbar-user">
              <div className="navbar-avatar">
                {user.email[0].toUpperCase()}
              </div>
              <span className="navbar-email">{user.email}</span>
            </div>
            <button className="navbar-logout" onClick={handleLogout}>
              Sign out
            </button>
          </>
        )}
      </div>
    </nav>
  );
}
