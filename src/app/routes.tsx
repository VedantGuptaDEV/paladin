import { createBrowserRouter, Navigate, Outlet } from "react-router";
import Sidebar from "../components/Sidebar";
import Dashboard from "../pages/Dashboard/Dashboard";
import Session from "../pages/Session/Session";
import Approvals from "../pages/Approvals/Approvals";
import Activity from "../pages/Activity/Activity";
import Policies from "../pages/Policies/Policies";
import Settings from "../pages/Settings/Settings";
import PaladinTUI from "../pages/TUI/PaladinTUI";

function Root() {
  return (
    <div style={{ display: "flex", height: "100vh", background: "var(--bg-0)", overflow: "hidden" }}>
      <Sidebar />
      <main
        style={{
          flex: 1,
          marginLeft: 216,
          overflowY: "auto",
          height: "100vh",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Outlet />
      </main>
    </div>
  );
}

export const router = createBrowserRouter([
  {
    path: "/tui",
    Component: PaladinTUI,
  },
  {
    path: "/",
    Component: Root,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", Component: Dashboard },
      { path: "session/:id", Component: Session },
      { path: "approvals", Component: Approvals },
      { path: "activity", Component: Activity },
      { path: "policies", Component: Policies },
      { path: "settings", Component: Settings },
    ],
  },
]);
