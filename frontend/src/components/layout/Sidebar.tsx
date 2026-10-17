import { NavLink } from "react-router-dom";
import Icon, { type IconName } from "../ui/Icon";

interface SidebarProps {
  mobileOpen: boolean;
  onClose: () => void;
}

const Sidebar = ({ mobileOpen, onClose }: SidebarProps) => {
  const navigation = [
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
      label: "Live Tracking",
      path: "/tracking",
      icon: "mapPin" as IconName,
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
    {
      label: "Notifications",
      path: "/notifications",
      icon: "bell" as IconName,
    },
  ];

  return (
    <>
      {mobileOpen && <div className="sidebar-overlay" onClick={onClose} />}

      <aside className={`app-sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        {/* =====================================
            BRAND
        ===================================== */}

        <div className="sidebar-brand">
          <div className="brand-mark">R</div>

          <div>
            <h2>ResQDrive</h2>

            <span>AI Mobility</span>
          </div>
        </div>

        {/* =====================================
            NAVIGATION
        ===================================== */}

        <nav className="sidebar-navigation">
          <p className="navigation-label">MAIN MENU</p>

          {navigation.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={onClose}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? "active" : ""}`
              }
            >
              <span className="sidebar-icon"><Icon name={item.icon} /></span>

              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* =====================================
            BOTTOM
        ===================================== */}

        <div className="sidebar-bottom">
          <NavLink
            to="/settings"
            onClick={onClose}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? "active" : ""}`
            }
          >
            <span className="sidebar-icon"><Icon name="settings" /></span>

            <span>Settings</span>
          </NavLink>

          {/* SYSTEM STATUS */}

          <div className="sidebar-status">
            <span className="status-dot" />

            <div>
              <strong>System Online</strong>

              <small>All services operational</small>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
