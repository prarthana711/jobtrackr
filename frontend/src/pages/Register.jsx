import { Link, Navigate } from "react-router";
import { useAuth } from "../authContext.js";
import AuthForm from "../components/AuthForm.jsx";

export default function Register() {
  const { user, register } = useAuth();

  if (user) return <Navigate to="/dashboard" replace />;

  return (
    <AuthForm
      title="Create your account"
      submitLabel="Register"
      isNewAccount
      onSubmit={register}
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-indigo-600 hover:underline">
            Log in
          </Link>
        </>
      }
    />
  );
}