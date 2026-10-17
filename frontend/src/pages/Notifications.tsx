import { API_BASE_URL } from "../api/config";
import { useCallback, useEffect, useMemo, useState } from "react";
import AppLayout from "../components/layout/AppLayout";
import Icon, { type IconName } from "../components/ui/Icon";

interface NotificationItem {
  notification_id: number;
  emergency_id: number | null;
  provider_id: number | null;
  title: string;
  message: string;
  status: string;
  created_at: string;
}

const API_URL = API_BASE_URL;

function getAuthToken(): string | null {
  const keys = ["access_token", "token", "authToken", "jwt"];

  for (const key of keys) {
    const value = localStorage.getItem(key) || sessionStorage.getItem(key);

    if (value) {
      return value.replace(/^Bearer\s+/i, "");
    }
  }

  const userKeys = ["user", "currentUser", "auth_user"];

  for (const key of userKeys) {
    const raw = localStorage.getItem(key) || sessionStorage.getItem(key);

    if (!raw) continue;

    try {
      const parsed = JSON.parse(raw);

      const token =
        parsed?.access_token || parsed?.token || parsed?.accessToken;

      if (token) {
        return String(token).replace(/^Bearer\s+/i, "");
      }
    } catch {
      // Ignore invalid stored user data.
    }
  }

  return null;
}

function formatDate(dateString: string): string {
  if (!dateString) return "";

  const date = new Date(dateString);

  if (Number.isNaN(date.getTime())) {
    return dateString;
  }

  return date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function getNotificationIcon(title: string): IconName {
  const value = title.toLowerCase();

  if (value.includes("accepted")) return "checkCircle";
  if (value.includes("way")) return "car";
  if (value.includes("arrived")) return "mapPin";
  if (value.includes("completed")) return "checkCircle";
  if (value.includes("cancel")) return "alert";
  if (value.includes("reassign")) return "refresh";
  if (value.includes("emergency")) return "siren";

  return "bell";
}

function getNotificationClass(status: string): string {
  return status === "unread" ? "notification-card unread" : "notification-card";
}

export default function Notifications() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [markingId, setMarkingId] = useState<number | null>(null);
  const [markingAll, setMarkingAll] = useState(false);

  const loadNotifications = useCallback(async (showLoading = false) => {
    const token = getAuthToken();

    if (!token) {
      setError("Please login again.");
      setLoading(false);
      return;
    }

    if (showLoading) {
      setLoading(true);
    }

    try {
      const response = await fetch(`${API_URL}/notifications/me`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        const text = await response.text();

        throw new Error(
          text || `Failed to load notifications (${response.status})`,
        );
      }

      const data = await response.json();

      setNotifications(Array.isArray(data) ? data : []);

      setError("");
    } catch (err) {
      console.error("Notification loading error:", err);

      setError(
        err instanceof Error ? err.message : "Unable to load notifications.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNotifications(true);

    const interval = window.setInterval(() => {
      loadNotifications(false);
    }, 5000);

    return () => {
      window.clearInterval(interval);
    };
  }, [loadNotifications]);

  const unreadCount = useMemo(
    () =>
      notifications.filter((notification) => notification.status === "unread")
        .length,
    [notifications],
  );

  const markAsRead = async (notificationId: number) => {
    const token = getAuthToken();

    if (!token) return;

    setMarkingId(notificationId);

    try {
      const response = await fetch(
        `${API_URL}/notifications/read/${notificationId}`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "application/json",
          },
        },
      );

      if (!response.ok) {
        throw new Error("Unable to mark notification as read.");
      }

      setNotifications((current) =>
        current.map((notification) =>
          notification.notification_id === notificationId
            ? {
                ...notification,
                status: "read",
              }
            : notification,
        ),
      );
    } catch (err) {
      console.error(err);
    } finally {
      setMarkingId(null);
    }
  };

  const markAllAsRead = async () => {
    const token = getAuthToken();

    if (!token || unreadCount === 0) return;

    setMarkingAll(true);

    try {
      const response = await fetch(`${API_URL}/notifications/read-all`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        throw new Error("Unable to mark all notifications as read.");
      }

      setNotifications((current) =>
        current.map((notification) => ({
          ...notification,
          status: "read",
        })),
      );
    } catch (err) {
      console.error(err);
    } finally {
      setMarkingAll(false);
    }
  };

  return (
    <AppLayout>
    <div className="notifications-page">
      <div
        style={{
          maxWidth: "1100px",
          margin: "0 auto",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "20px",
            marginBottom: "28px",
            flexWrap: "wrap",
          }}
        >
          <div>
            <div
              style={{
                color: "var(--color-primary)",
                fontWeight: 800,
                fontSize: "13px",
                letterSpacing: "1.5px",
                marginBottom: "8px",
              }}
            >
              RESQDRIVE AI
            </div>

            <h1
              style={{
                margin: 0,
                fontSize: "34px",
                color: "var(--color-text)",
              }}
            >
              Notifications
            </h1>

            <p
              style={{
                marginTop: "8px",
                color: "var(--color-muted)",
                fontSize: "16px",
              }}
            >
              Stay updated about your roadside assistance request.
            </p>
          </div>

          <button
            className="notifications-mark-all"
            onClick={markAllAsRead}
            disabled={markingAll || unreadCount === 0}
          >
            {markingAll
              ? "Marking..."
              : `Mark all read${unreadCount ? ` (${unreadCount})` : ""}`}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div
            style={{
              padding: "16px",
              marginBottom: "20px",
              borderRadius: "12px",
              background: "var(--color-emergency-soft)",
              color: "var(--color-emergency-text)",
              border: "1px solid var(--color-emergency-border)",
            }}
          >
            {error}
          </div>
        )}

        {/* Loading */}
        {loading ? (
          <div
            style={{
              background: "var(--color-surface)",
              borderRadius: "18px",
              padding: "60px 20px",
              textAlign: "center",
              color: "var(--color-muted)",
            }}
          >
            Loading notifications...
          </div>
        ) : notifications.length === 0 ? (
          /* Empty */
          <div
            style={{
              background: "var(--color-surface)",
              borderRadius: "18px",
              padding: "70px 20px",
              textAlign: "center",
              border: "1px solid var(--color-border)",
            }}
          >
            <div
              style={{
                fontSize: "54px",
                marginBottom: "15px",
              }}
            >
              <Icon name="bell" size={42} />
            </div>

            <h2
              style={{
                margin: "0 0 8px",
                color: "var(--color-text)",
              }}
            >
              No notifications
            </h2>

            <p
              style={{
                margin: 0,
                color: "var(--color-muted)",
              }}
            >
              New updates about your service requests will appear here.
            </p>
          </div>
        ) : (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            {notifications.map((notification) => (
              <div
                key={notification.notification_id}
                className={getNotificationClass(notification.status)}
                style={{
                  background:
                    notification.status === "unread" ? "var(--color-primary-soft)" : "var(--color-surface)",
                  border:
                    notification.status === "unread"
                      ? "1px solid var(--color-primary-border)"
                      : "1px solid var(--color-border)",
                  borderRadius: "16px",
                  padding: "20px",
                  display: "flex",
                  gap: "16px",
                  alignItems: "flex-start",
                  boxShadow: "0 4px 16px rgba(15, 23, 42, 0.04)",
                }}
              >
                <div
                  style={{
                    width: "50px",
                    height: "50px",
                    minWidth: "50px",
                    borderRadius: "14px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    background: "var(--color-surface)",
                    fontSize: "25px",
                  }}
                >
                  <Icon name={getNotificationIcon(notification.title)} size={24} />
                </div>

                <div
                  style={{
                    flex: 1,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "9px",
                      flexWrap: "wrap",
                    }}
                  >
                    <h3
                      style={{
                        margin: 0,
                        color: "var(--color-text)",
                        fontSize: "17px",
                      }}
                    >
                      {notification.title}
                    </h3>

                    {notification.status === "unread" && (
                      <span
                        style={{
                          padding: "4px 8px",
                          borderRadius: "999px",
                          background: "var(--color-primary)",
                          color: "var(--color-surface)",
                          fontSize: "11px",
                          fontWeight: 800,
                        }}
                      >
                        NEW
                      </span>
                    )}
                  </div>

                  <p
                    style={{
                      margin: "7px 0",
                      color: "var(--color-muted)",
                      lineHeight: 1.5,
                    }}
                  >
                    {notification.message}
                  </p>

                  <div
                    style={{
                      display: "flex",
                      gap: "15px",
                      flexWrap: "wrap",
                      color: "var(--color-muted)",
                      fontSize: "13px",
                    }}
                  >
                    <span>{formatDate(notification.created_at)}</span>

                    {notification.emergency_id && (
                      <span>Emergency #{notification.emergency_id}</span>
                    )}

                    {notification.provider_id && (
                      <span>Provider #{notification.provider_id}</span>
                    )}
                  </div>
                </div>

                {notification.status === "unread" && (
                  <button
                    onClick={() => markAsRead(notification.notification_id)}
                    disabled={markingId === notification.notification_id}
                    style={{
                      border: "1px solid var(--color-border)",
                      background: "var(--color-surface)",
                      color: "var(--color-text)",
                      borderRadius: "9px",
                      padding: "9px 12px",
                      fontWeight: 700,
                      cursor: "pointer",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {markingId === notification.notification_id
                      ? "Marking…"
                      : <><Icon name="check" size={15} /> Mark read</>}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
    </AppLayout>
  );
}
