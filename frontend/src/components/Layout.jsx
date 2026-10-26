import { Link, NavLink, Outlet, useNavigate } from "react-router";
import { useAuth } from "../authContext.js";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/jobs", label: "Jobs" },
  { to: "/applications", label: "Applications" },
  { to: "/resumes", label: "Resumes" },
];

// NavLink tells us whether its link matches the current page
function navClass({ isActive }) {
  return `whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium ${
    isActive ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-100"
  }`;
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <Link to="/dashboard" className="text-lg font-semibold text-indigo-600">
            JobTrackr
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <span className="hidden text-slate-500 sm:inline">{user?.email}</span>
            <button className="btn" onClick={handleLogout}>
              Log out
            </button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-5xl gap-1 overflow-x-auto px-4 pb-2" aria-label="Main">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} className={navClass}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}