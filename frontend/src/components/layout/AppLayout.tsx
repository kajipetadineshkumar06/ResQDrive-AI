import React, { useState } from "react";

import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import SearchDialog from "./SearchDialog";
import Icon, { type IconName } from "../ui/Icon";

interface AppLayoutProps {
  children?: React.ReactNode;
}

const navigationItems = [
  {
    label: "Dashboard",
    path: "/dashboard",
    icon: "dashboard" as IconName,
  },

  {
    label: "My Vehicles",
    path: "/vehicles",
    icon: "car" as IconName,
  },

  {
    label: "Service Requests",
    path: "/service-requests",
    icon: "clipboard" as IconName,
  },

  {
    label: "Emergency",
    path: "/emergency",
    icon: "siren" as IconName,
  },

  {
    label: "AI Assistant",
    path: "/ai",
    icon: "bot" as IconName,
  },

  {
    label: "History",
    path: "/history",
    icon: "history" as IconName,
  },
];

function getPageTitle(pathname: string): string {
  if (pathname.startsWith("/vehicles")) {
    return "My Vehicles";
  }

  if (pathname.startsWith("/service-requests")) {
    return "Service Requests";
  }

  if (pathname.startsWith("/emergency")) {
    return "Emergency Assistance";
  }

  if (pathname.startsWith("/ai")) {
    return "AI Assistant";
  }

  if (pathname.startsWith("/history")) {
    return "Service History";
  }

  if (pathname.startsWith("/notifications")) {
    return "Notifications";
  }

  return "Dashboard";
}

function getUserName(): string {
  const storedUser =
    localStorage.getItem("user") ||
    localStorage.getItem("currentUser") ||
    localStorage.getItem("userData");

  if (!storedUser) {
    return "User";
  }

  try {
    const parsed = JSON.parse(storedUser);

    return (
      parsed.full_name ||
      parsed.fullName ||
      parsed.name ||
      parsed.username ||
      "User"
    );
  } catch {
    return "User";
  }
}

function getUserEmail(): string {
  const storedUser =
    localStorage.getItem("user") ||
    localStorage.getItem("currentUser") ||
    localStorage.getItem("userData");

  if (!storedUser) {
    return "Roadside Member";
  }

  try {
    const parsed = JSON.parse(storedUser);

    return parsed.email || "Roadside Member";
  } catch {
    return "Roadside Member";
  }
}

function getInitials(name: string): string {
  const cleanName = name.trim();

  if (!cleanName) {
    return "U";
  }

  const parts = cleanName.split(/\s+/);

  if (parts.length === 1) {
    return parts[0].substring(0, 2).toUpperCase();
  }

  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const navigate = useNavigate();

  const location = useLocation();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);

  const pageTitle = getPageTitle(location.pathname);

  const userName = getUserName();

  const userEmail = getUserEmail();

  const initials = getInitials(userName);

  const closeSidebar = () => {
    setSidebarOpen(false);
  };

  const goToDashboard = () => {
    closeSidebar();

    navigate("/dashboard");
  };

  const handleLogout = () => {
    localStorage.removeItem("token");

    localStorage.removeItem("access_token");

    localStorage.removeItem("user");

    localStorage.removeItem("currentUser");

    localStorage.removeItem("userData");

    closeSidebar();

    navigate("/login", {
      replace: true,
    });
  };

  return (
    <div className="app-shell">
      {/* =================================
          SIDEBAR
      ================================= */}

      <aside className={`app-sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        {/* BRAND */}

        <button
          type="button"
          className="sidebar-brand"
          onClick={goToDashboard}
          aria-label="Go to Dashboard"
          style={{
            border: "none",
            background: "transparent",
            cursor: "pointer",
            color: "inherit",
            textAlign: "left",
            width: "100%",
          }}
        >
          <span className="brand-mark">R</span>

          <span>
            <h2>ResQDrive</h2>

            <span>AI Road Assistant</span>
          </span>
        </button>

        {/* NAVIGATION */}

        <nav className="sidebar-navigation">
          <div className="navigation-label">MAIN MENU</div>

          {navigationItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? "active" : ""}`
              }
              onClick={closeSidebar}
            >
              <span className="sidebar-icon"><Icon name={item.icon} /></span>

              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* SIDEBAR BOTTOM */}

        <div className="sidebar-bottom">
          <button
            type="button"
            className="sidebar-link"
            onClick={handleLogout}
            style={{
              width: "100%",
              border: "none",
              background: "transparent",
              cursor: "pointer",
              textAlign: "left",
            }}
          >
            <span className="sidebar-icon"><Icon name="logout" /></span>

            <span>Logout</span>
          </button>

          <div className="sidebar-status">
            <span className="status-dot"></span>

            <div>
              <strong>System Online</strong>

              <small>ResQDrive services active</small>
            </div>
          </div>
        </div>
      </aside>

      {/* =================================
          MOBILE OVERLAY
      ================================= */}

      {sidebarOpen && (
        <button
          type="button"
          className="sidebar-overlay"
          onClick={closeSidebar}
          aria-label="Close navigation"
          style={{
            border: "none",
            padding: 0,
            cursor: "pointer",
          }}
        />
      )}

      {/* =================================
          MAIN
      ================================= */}

      <main className="app-main">
        {/* TOPBAR */}

        <header className="app-topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="mobile-menu-button"
              onClick={() => setSidebarOpen((previous) => !previous)}
              aria-label="Open navigation menu"
              aria-expanded={sidebarOpen}
            >
              <Icon name="menu" />
            </button>

            <div className="topbar-heading">
              <span>RESQDRIVE AI</span>

              <h1>{pageTitle}</h1>
            </div>
          </div>

          {/* TOPBAR ACTIONS */}

          <div className="topbar-actions">
            {/* SEARCH */}

            <button
              type="button"
              className="topbar-icon-button search-button"
              aria-label="Search"
              aria-haspopup="dialog"
              aria-expanded={searchOpen}
              onClick={() => setSearchOpen(true)}
            >
              <Icon name="search" />
            </button>

            {/* NOTIFICATIONS */}

            <button
              type="button"
              className="topbar-icon-button"
              aria-label="Notifications"
              onClick={() => navigate("/notifications")}
            >
              <Icon name="bell" /><span className="notification-dot"></span>
            </button>

            {/* DIVIDER */}

            <div className="topbar-divider"></div>

            {/* USER */}

            <div className="topbar-user">
              <div className="user-avatar">{initials}</div>

              <div className="user-info">
                <strong>{userName}</strong>

                <span>{userEmail}</span>
              </div>
            </div>
          </div>
        </header>

        {/* CONTENT */}

        <section className="app-content">{children || <Outlet />}</section>
      </main>
      {searchOpen && <SearchDialog onClose={() => setSearchOpen(false)} />}
    </div>
  );
};

export default AppLayout;
