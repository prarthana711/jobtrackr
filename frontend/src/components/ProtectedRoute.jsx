import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth } from "../authContext.js";

export default function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  // While we check a stored token, don't flash the login page at a logged-in user
  if (loading) return <p className="p-8 text-slate-500">Loading...</p>;

  // Remember where they were going, so login can send them back
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;

  return <Outlet />;
}