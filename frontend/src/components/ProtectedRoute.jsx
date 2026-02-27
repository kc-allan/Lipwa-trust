import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children, role }) {
  const { user, loading } = useAuth();

  if (loading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", color: "var(--text-muted)" }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
        <div style={{ width: 32, height: 32, border: "2px solid var(--border)", borderTopColor: "var(--gold)", borderRadius: "50%", animation: "spin 0.8s linear infinite" }} />
        <p>Loading…</p>
      </div>
    </div>
  );

  if (!user) return <Navigate to="/login" />;

  // No role required (e.g. onboarding page) — any logged-in user can access
  if (!role) return children;

  if (role === "MERCHANT" && !user.is_merchant) return <Navigate to="/onboard" />;
  if (role === "SUPPLIER" && !user.is_supplier) return <Navigate to="/onboard" />;
  if (role === "ADMIN" && (user.is_merchant || user.is_supplier)) return <Navigate to="/" />;
  // Admin: roleless users should go to onboarding, not admin
  if (role === "ADMIN" && !user.is_merchant && !user.is_supplier) return <Navigate to="/onboard" />;

  return children;
}
