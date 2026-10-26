import { Link, Navigate, Route, Routes } from "react-router";
import Layout from "./components/Layout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import Applications from "./pages/Applications.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import JobDetail from "./pages/JobDetail.jsx";
import Jobs from "./pages/Jobs.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Resumes from "./pages/Resumes.jsx";

function NotFound() {
  return (
    <div className="p-8 text-center">
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <Link to="/dashboard" className="mt-4 inline-block font-medium text-indigo-600 hover:underline">
        Back to your dashboard
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Everything inside here requires a logged-in user */}
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/jobs/:jobId" element={<JobDetail />} />
          <Route path="/applications" element={<Applications />} />
          <Route path="/resumes" element={<Resumes />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}