import { useAuth } from "../../context/AuthContext";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import SearchDialog from "./SearchDialog";
import Icon from "../ui/Icon";

interface TopbarProps {
  onMenuClick: () => void;
}

const Topbar = ({ onMenuClick }: TopbarProps) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchOpen, setSearchOpen] = useState(false);

  const userName = user?.full_name || "User";

  const firstLetter = userName.charAt(0).toUpperCase();

  return (
    <header className="app-topbar">
      <div className="topbar-left">
        <button
          className="mobile-menu-button"
          onClick={onMenuClick}
          aria-label="Open navigation"
        >
          <Icon name="menu" />
        </button>

        <div className="topbar-heading">
          <span>Overview</span>
          <h1>Dashboard</h1>
        </div>
      </div>

      <div className="topbar-actions">
        <button className="topbar-icon-button" aria-label="Search" onClick={() => setSearchOpen(true)}>
          <Icon name="search" />
        </button>

        <button className="topbar-icon-button" aria-label="Notifications" onClick={() => navigate("/notifications")}>
          <Icon name="bell" />
          <span className="notification-dot" />
        </button>

        <div className="topbar-divider" />

        <div className="topbar-user">
          <div className="user-avatar">{firstLetter}</div>

          <div className="user-info">
            <strong>{userName}</strong>
            <span>Customer</span>
          </div>
        </div>
      </div>
      {searchOpen && <SearchDialog onClose={() => setSearchOpen(false)} />}
    </header>
  );
};

export default Topbar;
