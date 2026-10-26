import { Link, Navigate, useLocation } from "react-router";
import { useAuth } from "../authContext.js";
import AuthForm from "../components/AuthForm.jsx";

export default function Login() {
  const { user, login } = useAuth();
  const location = useLocation();
  const destination = location.state?.from?.pathname ?? "/jobs";

  // Already logged in (or just logged in): go where they were headed
  if (user) return <Navigate to={destination} replace />;

  return (
    <AuthForm
      title="Log in to JobTrackr"
      submitLabel="Log in"
      onSubmit={login}
      footer={
        <>
          New here?{" "}
          <Link to="/register" className="font-medium text-indigo-600 hover:underline">
            Create an account
          </Link>
        </>
      }
    />
  );
}