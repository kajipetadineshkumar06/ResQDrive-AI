import { API_BASE_URL } from "../api/config";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Icon from "../components/ui/Icon";
import AppLayout from "../components/layout/AppLayout";

interface ServiceRequest {
  request_id: number;
  emergency_id: number;
  provider_id: number | null;
  user_id: number;
  request_status: string;

  requested_at?: string | null;
  accepted_at?: string | null;
  started_at?: string | null;
  arrived_at?: string | null;
  completed_at?: string | null;
  cancelled_at?: string | null;

  estimated_arrival?: string | null;
  notes?: string | null;
}

interface ProviderInfo {
  provider_id: number;
  name: string;
  service_type: string;
  phone?: string | null;
  is_available: boolean;
  is_tracking?: boolean;
  rating_avg?: number | null;
  experience_years?: number | null;
  verified?: boolean;
}

type ActionType = "accept" | "reject" | "start" | "arrived" | "service-start" | "complete";

const API_URL = API_BASE_URL;

const ACTIVE_STATUSES = ["accepted", "on_the_way", "arrived", "in_progress"];

const normalizeStatus = (status?: string | null): string => {
  return (status || "unknown").trim().toLowerCase();
};

const formatStatus = (status?: string | null): string => {
  const normalized = normalizeStatus(status);

  switch (normalized) {
    case "pending":
      return "Pending";

    case "accepted":
      return "Accepted";

    case "on_the_way":
      return "On The Way";

    case "started":
      return "On The Way";

    case "arrived":
      return "Arrived";

    case "in_progress":
      return "Service In Progress";

    case "completed":
      return "Completed";

    case "cancelled":
      return "Cancelled";

    case "rejected":
      return "Rejected";

    default:
      return "Unknown";
  }
};

const getStatusClass = (status?: string | null): string => {
  const normalized = normalizeStatus(status);

  switch (normalized) {
    case "pending":
      return "pending";

    case "accepted":
      return "accepted";

    case "on_the_way":
    case "started":
      return "on-the-way";

    case "arrived":
      return "arrived";

    case "in_progress":
      return "arrived";

    case "completed":
      return "completed";

    case "cancelled":
      return "cancelled";

    case "rejected":
      return "rejected";

    default:
      return "unknown";
  }
};

const formatDate = (value?: string | null): string => {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  });
};

const getAuthToken = (): string | null => {
  const keys = [
    "access_token",
    "token",
    "jwt_token",
    "authToken",
    "accessToken",
  ];

  for (const key of keys) {
    const localValue = localStorage.getItem(key);

    if (localValue) {
      return localValue;
    }

    const sessionValue = sessionStorage.getItem(key);

    if (sessionValue) {
      return sessionValue;
    }
  }

  const userKeys = ["user", "currentUser", "auth_user"];

  for (const key of userKeys) {
    const raw = localStorage.getItem(key) || sessionStorage.getItem(key);

    if (!raw) {
      continue;
    }

    try {
      const parsed = JSON.parse(raw);

      const token =
        parsed?.access_token || parsed?.accessToken || parsed?.token;

      if (token) {
        return token;
      }
    } catch {
      // Ignore invalid JSON.
    }
  }

  return null;
};

const getErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }

  return "Something went wrong.";
};

const getCleanToken = (): string => {
  const token = getAuthToken();

  if (!token) {
    throw new Error("Not authenticated. Please login again.");
  }

  return token.trim().replace(/^Bearer\s+/i, "");
};

const apiRequest = async (
  endpoint: string,
  options: RequestInit = {},
): Promise<any> => {
  const token = getCleanToken();

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });

  if (response.status === 401) {
    throw new Error("Your session has expired. Please login again.");
  }

  let data: any = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const message =
      data?.detail ||
      data?.message ||
      `Request failed with status ${response.status}`;

    throw new Error(message);
  }

  return data;
};

function ProviderDashboard() {
  const navigate = useNavigate();

  const [requests, setRequests] = useState<ServiceRequest[]>([]);

  const [provider, setProvider] = useState<ProviderInfo | null>(null);

  const [loading, setLoading] = useState(true);

  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [actionRequestId, setActionRequestId] = useState<number | null>(null);

  const [actionType, setActionType] = useState<ActionType | null>(null);

  const [selectedRequest, setSelectedRequest] = useState<ServiceRequest | null>(
    null,
  );

  const gpsWatchRef = useRef<number | null>(null);

  const lastGpsSentAtRef = useRef(0);

  const [gpsStatus, setGpsStatus] = useState("GPS idle");

  // =========================================================
  // LOAD PROVIDER INFORMATION
  // =========================================================

  const loadProvider = useCallback(async () => {
    try {
      /*
       * The provider dashboard can work without a separate
       * provider-profile endpoint because the request endpoint
       * identifies the provider from the logged-in user.
       *
       * We therefore keep provider information optional here.
       */
    } catch (error) {
      console.error("Provider profile error:", error);
    }
  }, []);

  // =========================================================
  // LOAD PROVIDER REQUESTS
  // =========================================================

  const loadRequests = useCallback(async (showInitialLoading = false) => {
    try {
      if (showInitialLoading) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }

      setError(null);

      const data = await apiRequest("/provider/requests");

      if (!Array.isArray(data)) {
        throw new Error("Invalid provider request response from server.");
      }

      setRequests(data as ServiceRequest[]);
    } catch (error: unknown) {
      console.error("Provider requests error:", error);

      if (showInitialLoading) {
        setError(getErrorMessage(error));
      }
    } finally {
      if (showInitialLoading) {
        setLoading(false);
      } else {
        setRefreshing(false);
      }
    }
  }, []);

  // =========================================================
  // INITIAL LOAD
  // =========================================================

  useEffect(() => {
    loadProvider();

    loadRequests(true);
  }, [loadProvider, loadRequests]);

  // =========================================================
  // AUTO REFRESH
  // =========================================================

  useEffect(() => {
    const interval = window.setInterval(() => {
      loadRequests(false);
    }, 5000);

    return () => {
      window.clearInterval(interval);
    };
  }, [loadRequests]);

  // =========================================================
  // ACTION HANDLER
  // =========================================================

  const performAction = async (requestId: number, type: ActionType) => {
    if (actionRequestId !== null) {
      return;
    }

    if (type === "reject") {
      const confirmed = window.confirm(`Reject service request #${requestId}?`);

      if (!confirmed) {
        return;
      }
    }

    try {
      setActionRequestId(requestId);

      setActionType(type);

      let endpoint = "";

      switch (type) {
        case "accept":
          endpoint = `/provider/request/${requestId}/accept`;
          break;

        case "reject":
          endpoint = `/provider/request/${requestId}/reject`;
          break;

        case "start":
          endpoint = `/provider/request/${requestId}/start`;
          break;

        case "arrived":
          endpoint = `/provider/request/${requestId}/arrived`;
          break;

        case "service-start":
          endpoint = `/provider/request/${requestId}/start-service`;
          break;

        case "complete":
          endpoint = `/provider/request/${requestId}/complete`;
          break;

        default:
          throw new Error("Invalid provider action.");
      }

      await apiRequest(endpoint, {
        method: "POST",
      });

      await loadRequests(false);
    } catch (error: unknown) {
      window.alert(getErrorMessage(error));
    } finally {
      setActionRequestId(null);

      setActionType(null);
    }
  };

  // =========================================================
  // COUNTS
  // =========================================================

  const pendingRequests = useMemo(
    () =>
      requests.filter(
        (request) => normalizeStatus(request.request_status) === "pending",
      ),
    [requests],
  );

  const activeRequests = useMemo(
    () =>
      requests.filter((request) =>
        ACTIVE_STATUSES.includes(normalizeStatus(request.request_status)),
      ),
    [requests],
  );

  const completedRequests = useMemo(
    () =>
      requests.filter(
        (request) => normalizeStatus(request.request_status) === "completed",
      ),
    [requests],
  );

  const cancelledRequests = useMemo(
    () =>
      requests.filter(
        (request) => normalizeStatus(request.request_status) === "cancelled",
      ),
    [requests],
  );

  const onTheWayRequest = useMemo(
    () =>
      requests.find((request) =>
        ["on_the_way", "started"].includes(
          normalizeStatus(request.request_status),
        ),
      ) || null,
    [requests],
  );

  // =========================================================
  // AUTOMATIC PROVIDER GPS
  // =========================================================
  // The backend derives the provider from the JWT, so the browser
  // only submits coordinates to the secure update endpoint.

  useEffect(() => {
    if (!onTheWayRequest) {
      setGpsStatus("GPS idle");
      return;
    }

    if (!navigator.geolocation) {
      setGpsStatus("GPS unavailable");
      return;
    }

    let stopped = false;

    const sendLocation = async (position: GeolocationPosition) => {
      const now = Date.now();

      // GPS can report several times per second. Five seconds is
      // frequent enough for a moving marker without overloading APIs.
      if (now - lastGpsSentAtRef.current < 5000) {
        return;
      }

      lastGpsSentAtRef.current = now;

      try {
        setGpsStatus("Sending live GPS...");

        await apiRequest("/provider-location/update", {
          method: "POST",
          body: JSON.stringify({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          }),
        });

        if (!stopped) {
          setGpsStatus("Live GPS active");
        }
      } catch (error) {
        console.error("Provider GPS update failed:", error);

        if (!stopped) {
          setGpsStatus("GPS update failed");
        }
      }
    };

    setGpsStatus("Requesting location access...");

    gpsWatchRef.current = navigator.geolocation.watchPosition(
      sendLocation,
      (positionError) => {
        console.error("Provider GPS error:", positionError);

        if (!stopped) {
          setGpsStatus("Location permission needed");
        }
      },
      {
        enableHighAccuracy: true,
        maximumAge: 3000,
        timeout: 15000,
      },
    );

    return () => {
      stopped = true;

      if (gpsWatchRef.current !== null) {
        navigator.geolocation.clearWatch(gpsWatchRef.current);

        gpsWatchRef.current = null;
      }
    };
  }, [onTheWayRequest?.request_id]);

  // =========================================================
  // ACTION LABEL
  // =========================================================

  const getActionLabel = (type: ActionType): string => {
    if (actionType !== type) {
      switch (type) {
        case "accept":
          return "Accept";

        case "reject":
          return "Reject";

        case "start":
          return "Start Trip";

        case "arrived":
          return "Mark Arrived";

        case "service-start":
          return "Start Service";

        case "complete":
          return "Complete Service";
      }
    }

    switch (type) {
      case "accept":
        return "Accepting...";

      case "reject":
        return "Rejecting...";

      case "start":
        return "Starting...";

      case "arrived":
        return "Updating...";

      case "service-start":
        return "Starting service...";

      case "complete":
        return "Completing...";
    }
  };

  // =========================================================
  // REQUEST ACTIONS
  // =========================================================

  const renderActions = (request: ServiceRequest) => {
    const status = normalizeStatus(request.request_status);

    const busy = actionRequestId === request.request_id;

    if (status === "pending") {
      return (
        <div className="provider-action-row">
          <button
            type="button"
            className="primary-button"
            disabled={actionRequestId !== null}
            onClick={() => performAction(request.request_id, "accept")}
          >
            {busy && actionType === "accept"
              ? getActionLabel("accept")
              : "Accept"}
          </button>

          <button
            type="button"
            className="secondary-button danger-button"
            disabled={actionRequestId !== null}
            onClick={() => performAction(request.request_id, "reject")}
          >
            {busy && actionType === "reject"
              ? getActionLabel("reject")
              : "Reject"}
          </button>
        </div>
      );
    }

    if (status === "accepted") {
      return (
        <button
          type="button"
          className="primary-button full-width-button"
          disabled={actionRequestId !== null}
          onClick={() => performAction(request.request_id, "start")}
        >
          {busy ? getActionLabel("start") : "Start Trip"}
        </button>
      );
    }

    if (status === "on_the_way" || status === "started") {
      return (
        <button
          type="button"
          className="primary-button full-width-button"
          disabled={actionRequestId !== null}
          onClick={() => performAction(request.request_id, "arrived")}
        >
          {busy ? getActionLabel("arrived") : "Mark Arrived"}
        </button>
      );
    }

    if (status === "arrived") {
      return (
        <button
          type="button"
          className="primary-button full-width-button"
          disabled={actionRequestId !== null}
          onClick={() => performAction(request.request_id, "service-start")}
        >
          {busy ? getActionLabel("service-start") : "Start Service"}
        </button>
      );
    }

    if (status === "in_progress") {
      return (
        <button
          type="button"
          className="primary-button full-width-button"
          disabled={actionRequestId !== null}
          onClick={() => performAction(request.request_id, "complete")}
        >
          {busy ? getActionLabel("complete") : "Complete Service"}
        </button>
      );
    }

    if (status === "completed") {
      return (
        <div className="provider-completed-message"><Icon name="checkCircle" size={18} /> Service completed</div>
      );
    }

    if (status === "cancelled") {
      return (
        <div className="provider-cancelled-message">Request cancelled</div>
      );
    }

    return null;
  };

  // =========================================================
  // TIMELINE
  // =========================================================

  const renderTimeline = (request: ServiceRequest) => {
    const status = normalizeStatus(request.request_status);

    if (status === "cancelled") {
      return (
        <div className="provider-timeline">
          <div className="provider-timeline-item completed">
            <span className="timeline-dot"><Icon name="check" size={14} /></span>

            <div>
              <strong>Request Created</strong>

              <small>{formatDate(request.requested_at)}</small>
            </div>
          </div>

          <div className="provider-timeline-item cancelled">
            <span className="timeline-dot"><Icon name="close" size={14} /></span>

            <div>
              <strong>Request Cancelled</strong>

              <small>{formatDate(request.cancelled_at)}</small>
            </div>
          </div>
        </div>
      );
    }

    const steps = [
      {
        key: "created",
        label: "Request Created",
        done: true,
        time: request.requested_at,
      },
      {
        key: "accepted",
        label: "Provider Accepted",
        done:
          Boolean(request.accepted_at) ||
          [
            "accepted",
            "on_the_way",
            "started",
            "arrived",
            "in_progress",
            "completed",
          ].includes(status),
        time: request.accepted_at,
      },
      {
        key: "on_the_way",
        label: "Provider On The Way",
        done:
          Boolean(request.started_at) ||
          ["on_the_way", "started", "arrived", "in_progress", "completed"].includes(status),
        time: request.started_at,
      },
      {
        key: "arrived",
        label: "Provider Arrived",
        done:
          Boolean(request.arrived_at) ||
          ["arrived", "in_progress", "completed"].includes(status),
        time: request.arrived_at,
      },
      {
        key: "in_progress",
        label: "Service In Progress",
        done: ["in_progress", "completed"].includes(status),
        time: null,
      },
      {
        key: "completed",
        label: "Service Completed",
        done: Boolean(request.completed_at) || status === "completed",
        time: request.completed_at,
      },
    ];

    return (
      <div className="provider-timeline">
        {steps.map((step) => (
          <div
            key={step.key}
            className={`provider-timeline-item ${step.done ? "completed" : ""}`}
          >
            <span className="timeline-dot"><Icon name={step.done ? "check" : "circle"} size={14} /></span>

            <div>
              <strong>{step.label}</strong>

              {step.time && <small>{formatDate(step.time)}</small>}
            </div>
          </div>
        ))}
      </div>
    );
  };

  // =========================================================
  // LOADING
  // =========================================================

  if (loading) {
    return (
      <AppLayout>
        <div className="provider-dashboard-page">
          <div className="provider-loading-card">
            <div className="provider-loading-icon"><Icon name="refresh" /></div>

            <h2>Loading Provider Dashboard</h2>

            <p>Getting your assigned roadside assistance requests...</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  // =========================================================
  // MAIN PAGE
  // =========================================================

  return (
    <AppLayout>
      <div className="provider-dashboard-page">
        {/* ================================================
            HEADER
        ================================================= */}

        <div className="provider-page-header">
          <div>
            <span className="page-eyebrow">RESQDRIVE AI</span>

            <h1>Provider Dashboard</h1>

            <p>
              Manage roadside assistance requests and respond to customers in
              real time.
            </p>
          </div>

          <div className="provider-header-actions">
            <span className="provider-gps-indicator"><Icon name="mapPin" size={15} /> {gpsStatus}</span>

            <span className="provider-live-indicator">
              <span className="live-dot" />
              Live
            </span>

            <button
              type="button"
              className="secondary-button"
              disabled={refreshing}
              onClick={() => loadRequests(false)}
            >
              {refreshing ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>

        {/* ================================================
            ERROR
        ================================================= */}

        {error && (
          <div className="provider-error-card">
            <strong>Unable to load provider requests</strong>

            <p>{error}</p>

            <button
              type="button"
              className="secondary-button"
              onClick={() => loadRequests(true)}
            >
              Try Again
            </button>
          </div>
        )}

        {/* ================================================
            PROVIDER SUMMARY
        ================================================= */}

        <section className="provider-summary-grid">
          <div className="provider-summary-card">
            <span className="summary-icon"><Icon name="clipboard" /></span>

            <div>
              <strong>{pendingRequests.length}</strong>

              <span>Pending Requests</span>
            </div>
          </div>

          <div className="provider-summary-card">
            <span className="summary-icon"><Icon name="car" /></span>

            <div>
              <strong>{activeRequests.length}</strong>

              <span>Active Services</span>
            </div>
          </div>

          <div className="provider-summary-card">
            <span className="summary-icon"><Icon name="checkCircle" /></span>

            <div>
              <strong>{completedRequests.length}</strong>

              <span>Completed</span>
            </div>
          </div>

          <div className="provider-summary-card">
            <span className="summary-icon"><Icon name="alert" /></span>

            <div>
              <strong>{cancelledRequests.length}</strong>

              <span>Cancelled</span>
            </div>
          </div>
        </section>

        {/* ================================================
            PROVIDER STATUS
        ================================================= */}

        <section className="provider-status-banner">
          <div className="provider-status-left">
            <div className="provider-avatar"><Icon name="wrench" /></div>

            <div>
              <span className="eyebrow">SERVICE PROVIDER</span>

              <h2>{provider?.name || "ResQDrive Provider"}</h2>

              <p>{provider?.service_type || "Roadside Assistance"}</p>
            </div>
          </div>

          <div className="provider-availability">
            <span className="availability-dot" />

            <span>{activeRequests.length > 0 ? "Busy" : "Available"}</span>
          </div>
        </section>

        {/* ================================================
            ACTIVE REQUEST
        ================================================= */}

        {activeRequests.length > 0 && (
          <section className="provider-section">
            <div className="provider-section-header">
              <div>
                <span className="eyebrow">CURRENT SERVICE</span>

                <h2>Active Request</h2>
              </div>
            </div>

            <div className="provider-active-grid">
              {activeRequests.map((request) => (
                <div
                  className="provider-request-card active-card"
                  key={request.request_id}
                >
                  <div className="provider-request-header">
                    <div>
                      <span className="request-label">
                        REQUEST #{request.request_id}
                      </span>

                      <h3>Roadside Assistance</h3>
                    </div>

                    <span
                      className={`request-status ${getStatusClass(
                        request.request_status,
                      )}`}
                    >
                      {formatStatus(request.request_status)}
                    </span>
                  </div>

                  <div className="provider-request-details">
                    <div>
                      <span>Emergency</span>

                      <strong>#{request.emergency_id}</strong>
                    </div>

                    <div>
                      <span>Customer</span>

                      <strong>#{request.user_id}</strong>
                    </div>

                    <div>
                      <span>Provider</span>

                      <strong>#{request.provider_id ?? "—"}</strong>
                    </div>
                  </div>

                  {renderTimeline(request)}

                  <div className="provider-request-footer">
                    {renderActions(request)}

                    <button
                      type="button"
                      className="text-button"
                      onClick={() => setSelectedRequest(request)}
                    >
                      View Details
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ================================================
            PENDING REQUESTS
        ================================================= */}

        <section className="provider-section">
          <div className="provider-section-header">
            <div>
              <span className="eyebrow">NEW ASSIGNMENTS</span>

              <h2>Pending Requests</h2>

              <p>New requests assigned to you appear automatically.</p>
            </div>
          </div>

          {pendingRequests.length === 0 ? (
            <div className="provider-empty-card">
              <div className="empty-icon"><Icon name="checkCircle" /></div>

              <h3>No pending requests</h3>

              <p>
                You're all caught up. New roadside assistance requests will
                appear here automatically.
              </p>
            </div>
          ) : (
            <div className="provider-request-grid">
              {pendingRequests.map((request) => (
                <div className="provider-request-card" key={request.request_id}>
                  <div className="provider-request-header">
                    <div>
                      <span className="request-label">
                        REQUEST #{request.request_id}
                      </span>

                      <h3>Roadside Assistance</h3>
                    </div>

                    <span className="request-status pending">Pending</span>
                  </div>

                  <div className="provider-request-details">
                    <div>
                      <span>Emergency</span>

                      <strong>#{request.emergency_id}</strong>
                    </div>

                    <div>
                      <span>Customer</span>

                      <strong>#{request.user_id}</strong>
                    </div>

                    <div>
                      <span>Provider</span>

                      <strong>#{request.provider_id ?? "—"}</strong>
                    </div>
                  </div>

                  {request.notes && (
                    <div className="provider-notes">
                      <span>Customer Notes</span>

                      <p>{request.notes}</p>
                    </div>
                  )}

                  <div className="provider-request-meta">
                    <span>Created</span>

                    <strong>{formatDate(request.requested_at)}</strong>
                  </div>

                  <div className="provider-request-footer">
                    {renderActions(request)}

                    <button
                      type="button"
                      className="text-button"
                      onClick={() => setSelectedRequest(request)}
                    >
                      View Details
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ================================================
            REQUEST HISTORY
        ================================================= */}

        <section className="provider-section">
          <div className="provider-section-header">
            <div>
              <span className="eyebrow">HISTORY</span>

              <h2>All Requests</h2>
            </div>
          </div>

          {requests.length === 0 ? (
            <div className="provider-empty-card">
              <div className="empty-icon"><Icon name="clipboard" /></div>

              <h3>No requests yet</h3>

              <p>Assigned service requests will appear here.</p>
            </div>
          ) : (
            <div className="provider-history-list">
              {requests.map((request) => (
                <div className="provider-history-item" key={request.request_id}>
                  <div className="history-request-icon"><Icon name="wrench" /></div>

                  <div className="history-request-info">
                    <strong>Request #{request.request_id}</strong>

                    <span>
                      Emergency #{request.emergency_id}
                      {" • "}
                      Customer #{request.user_id}
                    </span>

                    <small>{formatDate(request.requested_at)}</small>
                  </div>

                  <span
                    className={`request-status ${getStatusClass(
                      request.request_status,
                    )}`}
                  >
                    {formatStatus(request.request_status)}
                  </span>

                  <button
                    type="button"
                    className="text-button"
                    onClick={() => setSelectedRequest(request)}
                  >
                    Details
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ================================================
            QUICK ACTIONS
        ================================================= */}

        <section className="provider-quick-actions">
          <button
            type="button"
            className="provider-quick-action"
            onClick={() => loadRequests(false)}
          >
            <span><Icon name="refresh" /></span>

            <div>
              <strong>Refresh Requests</strong>

              <small>Get the latest request status</small>
            </div>
          </button>

          <button
            type="button"
            className="provider-quick-action"
            onClick={() => navigate("/tracking")}
          >
            <span><Icon name="mapPin" /></span>

            <div>
              <strong>Live Tracking</strong>

              <small>Provider location tracking</small>
            </div>
          </button>

          <button
            type="button"
            className="provider-quick-action"
            onClick={() => navigate("/notifications")}
          >
            <span><Icon name="bell" /></span>

            <div>
              <strong>Notifications</strong>

              <small>View service updates</small>
            </div>
          </button>
        </section>
      </div>

      {/* ====================================================
          DETAILS MODAL
      ==================================================== */}

      {selectedRequest && (
        <div
          className="provider-modal-overlay"
          onClick={() => setSelectedRequest(null)}
        >
          <div
            className="provider-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="provider-modal-header">
              <div>
                <span className="eyebrow">SERVICE REQUEST</span>

                <h2>Request #{selectedRequest.request_id}</h2>
              </div>

              <button
                type="button"
                className="modal-close-button"
                onClick={() => setSelectedRequest(null)}
              >
                ×
              </button>
            </div>

            <div className="provider-modal-status">
              <span
                className={`request-status ${getStatusClass(
                  selectedRequest.request_status,
                )}`}
              >
                {formatStatus(selectedRequest.request_status)}
              </span>
            </div>

            <div className="provider-modal-details">
              <div>
                <span>Emergency ID</span>

                <strong>#{selectedRequest.emergency_id}</strong>
              </div>

              <div>
                <span>Customer ID</span>

                <strong>#{selectedRequest.user_id}</strong>
              </div>

              <div>
                <span>Provider ID</span>

                <strong>
                  #{selectedRequest.provider_id ?? "Not assigned"}
                </strong>
              </div>

              <div>
                <span>Requested</span>

                <strong>{formatDate(selectedRequest.requested_at)}</strong>
              </div>

              {selectedRequest.estimated_arrival && (
                <div>
                  <span>Estimated Arrival</span>

                  <strong>{selectedRequest.estimated_arrival}</strong>
                </div>
              )}
            </div>

            {selectedRequest.notes && (
              <div className="provider-modal-notes">
                <span>Customer Notes</span>

                <p>{selectedRequest.notes}</p>
              </div>
            )}

            <div className="provider-modal-timeline">
              <h3>Request Timeline</h3>

              {renderTimeline(selectedRequest)}
            </div>

            <div className="provider-modal-actions">
              {renderActions(selectedRequest)}

              <button
                type="button"
                className="secondary-button"
                onClick={() => setSelectedRequest(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ====================================================
          PAGE STYLES
      ==================================================== */}

      <style>
        {`
          .provider-dashboard-page {
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px;
          }

          .provider-page-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 24px;
            margin-bottom: 28px;
          }

          .provider-page-header h1 {
            margin: 6px 0 8px;
            font-size: 34px;
            line-height: 1.1;
          }

          .provider-page-header p {
            margin: 0;
            opacity: 0.7;
          }

          .page-eyebrow,
          .eyebrow {
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            opacity: 0.65;
          }

          .provider-header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
          }

          .provider-live-indicator {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 9px 13px;
            border-radius: 999px;
            background: rgba(34, 197, 94, 0.1);
            font-size: 13px;
            font-weight: 700;
          }

          .provider-gps-indicator {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 9px 13px;
            border-radius: 999px;
            background: rgba(37, 99, 235, 0.1);
            color: #1d4ed8;
            font-size: 13px;
            font-weight: 700;
          }

          .live-dot,
          .availability-dot {
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: #22c55e;
            display: inline-block;
          }

          .provider-summary-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 16px;
            margin-bottom: 22px;
          }

          .provider-summary-card {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 20px;
            border-radius: 18px;
            border: 1px solid rgba(128, 128, 128, 0.18);
            background: rgba(255, 255, 255, 0.03);
          }

          .summary-icon {
            font-size: 25px;
          }

          .provider-summary-card strong {
            display: block;
            font-size: 27px;
            line-height: 1;
            margin-bottom: 5px;
          }

          .provider-summary-card span:last-child {
            font-size: 12px;
            opacity: 0.65;
          }

          .provider-status-banner {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
            padding: 24px;
            margin-bottom: 32px;
            border-radius: 20px;
            border: 1px solid rgba(128, 128, 128, 0.18);
            background: rgba(255, 255, 255, 0.03);
          }

          .provider-status-left {
            display: flex;
            align-items: center;
            gap: 15px;
          }

          .provider-avatar {
            width: 56px;
            height: 56px;
            display: grid;
            place-items: center;
            border-radius: 16px;
            background: rgba(128, 128, 128, 0.12);
            font-size: 25px;
          }

          .provider-status-banner h2 {
            margin: 4px 0;
            font-size: 21px;
          }

          .provider-status-banner p {
            margin: 0;
            opacity: 0.65;
            text-transform: capitalize;
          }

          .provider-availability {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 700;
          }

          .provider-section {
            margin-bottom: 38px;
          }

          .provider-section-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 18px;
          }

          .provider-section-header h2 {
            margin: 5px 0;
            font-size: 23px;
          }

          .provider-section-header p {
            margin: 0;
            opacity: 0.65;
            font-size: 14px;
          }

          .provider-request-grid,
          .provider-active-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 18px;
          }

          .provider-request-card {
            padding: 22px;
            border-radius: 20px;
            border: 1px solid rgba(128, 128, 128, 0.18);
            background: rgba(255, 255, 255, 0.03);
          }

          .active-card {
            border-width: 2px;
          }

          .provider-request-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 14px;
            margin-bottom: 20px;
          }

          .request-label {
            display: block;
            font-size: 10px;
            letter-spacing: 0.12em;
            font-weight: 800;
            opacity: 0.55;
          }

          .provider-request-header h3 {
            margin: 5px 0 0;
            font-size: 19px;
          }

          .request-status {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 7px 11px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 800;
            white-space: nowrap;
          }

          .request-status.pending {
            background: rgba(245, 158, 11, 0.12);
          }

          .request-status.accepted {
            background: rgba(59, 130, 246, 0.12);
          }

          .request-status.on-the-way {
            background: rgba(139, 92, 246, 0.12);
          }

          .request-status.arrived {
            background: rgba(20, 184, 166, 0.12);
          }

          .request-status.completed {
            background: rgba(34, 197, 94, 0.12);
          }

          .request-status.cancelled,
          .request-status.rejected {
            background: rgba(239, 68, 68, 0.12);
          }

          .provider-request-details {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 20px;
          }

          .provider-request-details > div,
          .provider-modal-details > div {
            padding: 12px;
            border-radius: 12px;
            background: rgba(128, 128, 128, 0.07);
          }

          .provider-request-details span,
          .provider-modal-details span,
          .provider-request-meta span,
          .provider-notes > span,
          .provider-modal-notes > span {
            display: block;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            opacity: 0.55;
            margin-bottom: 4px;
          }

          .provider-request-details strong,
          .provider-modal-details strong {
            font-size: 13px;
          }

          .provider-notes {
            padding: 13px;
            margin-bottom: 18px;
            border-radius: 13px;
            background: rgba(128, 128, 128, 0.07);
          }

          .provider-notes p,
          .provider-modal-notes p {
            margin: 5px 0 0;
            font-size: 13px;
            line-height: 1.5;
            opacity: 0.8;
          }

          .provider-request-meta {
            padding-top: 15px;
            margin-bottom: 18px;
            border-top: 1px solid rgba(128, 128, 128, 0.15);
          }

          .provider-request-meta strong {
            font-size: 12px;
          }

          .provider-action-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
          }

          .primary-button,
          .secondary-button {
            border: 0;
            border-radius: 11px;
            padding: 11px 16px;
            font-size: 13px;
            font-weight: 750;
            cursor: pointer;
            transition: transform 0.15s ease, opacity 0.15s ease;
          }

          .primary-button {
            background: #111827;
            color: white;
          }

          .secondary-button {
            background: rgba(128, 128, 128, 0.12);
            color: inherit;
          }

          .danger-button {
            color: #dc2626;
          }

          .primary-button:hover:not(:disabled),
          .secondary-button:hover:not(:disabled) {
            transform: translateY(-1px);
          }

          .primary-button:disabled,
          .secondary-button:disabled {
            cursor: not-allowed;
            opacity: 0.55;
          }

          .full-width-button {
            width: 100%;
          }

          .text-button {
            border: 0;
            background: transparent;
            padding: 7px 0;
            cursor: pointer;
            font-weight: 700;
            font-size: 12px;
            opacity: 0.7;
          }

          .text-button:hover {
            opacity: 1;
          }

          .provider-request-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
          }

          .provider-request-footer > .full-width-button {
            flex: 1;
          }

          .provider-completed-message,
          .provider-cancelled-message {
            flex: 1;
            padding: 11px;
            text-align: center;
            border-radius: 11px;
            font-size: 13px;
            font-weight: 750;
          }

          .provider-completed-message {
            background: rgba(34, 197, 94, 0.1);
          }

          .provider-cancelled-message {
            background: rgba(239, 68, 68, 0.1);
          }

          .provider-timeline {
            position: relative;
            margin: 18px 0;
          }

          .provider-timeline-item {
            position: relative;
            display: flex;
            align-items: flex-start;
            gap: 11px;
            min-height: 43px;
          }

          .provider-timeline-item:not(:last-child)::after {
            content: "";
            position: absolute;
            left: 8px;
            top: 21px;
            bottom: 0;
            width: 1px;
            background: rgba(128, 128, 128, 0.22);
          }

          .timeline-dot {
            position: relative;
            z-index: 1;
            width: 17px;
            height: 17px;
            display: grid;
            place-items: center;
            border-radius: 50%;
            background: rgba(128, 128, 128, 0.12);
            font-size: 10px;
            font-weight: 800;
          }

          .provider-timeline-item.completed .timeline-dot {
            background: rgba(34, 197, 94, 0.15);
          }

          .provider-timeline-item.cancelled .timeline-dot {
            background: rgba(239, 68, 68, 0.15);
          }

          .provider-timeline-item strong {
            display: block;
            font-size: 12px;
          }

          .provider-timeline-item small {
            display: block;
            margin-top: 3px;
            font-size: 10px;
            opacity: 0.55;
          }

          .provider-history-list {
            display: flex;
            flex-direction: column;
            border: 1px solid rgba(128, 128, 128, 0.18);
            border-radius: 18px;
            overflow: hidden;
          }

          .provider-history-item {
            display: grid;
            grid-template-columns: 42px 1fr auto auto;
            align-items: center;
            gap: 14px;
            padding: 16px 18px;
            border-bottom: 1px solid rgba(128, 128, 128, 0.13);
          }

          .provider-history-item:last-child {
            border-bottom: 0;
          }

          .history-request-icon {
            width: 40px;
            height: 40px;
            display: grid;
            place-items: center;
            border-radius: 12px;
            background: rgba(128, 128, 128, 0.1);
          }

          .history-request-info strong,
          .history-request-info span,
          .history-request-info small {
            display: block;
          }

          .history-request-info strong {
            font-size: 13px;
          }

          .history-request-info span {
            margin-top: 3px;
            font-size: 11px;
            opacity: 0.65;
          }

          .history-request-info small {
            margin-top: 3px;
            font-size: 10px;
            opacity: 0.45;
          }

          .provider-empty-card,
          .provider-loading-card {
            padding: 48px 24px;
            text-align: center;
            border: 1px dashed rgba(128, 128, 128, 0.25);
            border-radius: 20px;
          }

          .empty-icon,
          .provider-loading-icon {
            font-size: 30px;
            margin-bottom: 10px;
          }

          .provider-empty-card h3,
          .provider-loading-card h2 {
            margin: 0 0 8px;
          }

          .provider-empty-card p,
          .provider-loading-card p {
            max-width: 520px;
            margin: 0 auto;
            opacity: 0.65;
            line-height: 1.5;
          }

          .provider-error-card {
            margin-bottom: 22px;
            padding: 18px;
            border-radius: 16px;
            background: rgba(239, 68, 68, 0.08);
            border: 1px solid rgba(239, 68, 68, 0.18);
          }

          .provider-error-card p {
            margin: 6px 0 12px;
            font-size: 13px;
          }

          .provider-quick-actions {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin-top: 30px;
          }

          .provider-quick-action {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 17px;
            text-align: left;
            border: 1px solid rgba(128, 128, 128, 0.18);
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.03);
            cursor: pointer;
          }

          .provider-quick-action > span {
            font-size: 23px;
          }

          .provider-quick-action strong,
          .provider-quick-action small {
            display: block;
          }

          .provider-quick-action strong {
            font-size: 13px;
          }

          .provider-quick-action small {
            margin-top: 3px;
            font-size: 10px;
            opacity: 0.55;
          }

          .provider-modal-overlay {
            position: fixed;
            inset: 0;
            z-index: 1000;
            display: grid;
            place-items: center;
            padding: 20px;
            background: rgba(0, 0, 0, 0.55);
          }

          .provider-modal {
            width: min(650px, 100%);
            max-height: 90vh;
            overflow-y: auto;
            padding: 25px;
            border-radius: 22px;
            background: white;
            color: #111827;
            box-shadow: 0 25px 80px rgba(0, 0, 0, 0.25);
          }

          .provider-modal-header {
            display: flex;
            justify-content: space-between;
            gap: 15px;
          }

          .provider-modal-header h2 {
            margin: 5px 0 0;
          }

          .modal-close-button {
            width: 36px;
            height: 36px;
            border: 0;
            border-radius: 10px;
            background: rgba(128, 128, 128, 0.1);
            font-size: 23px;
            cursor: pointer;
          }

          .provider-modal-status {
            margin: 22px 0;
          }

          .provider-modal-details {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
          }

          .provider-modal-notes {
            margin-top: 15px;
            padding: 14px;
            border-radius: 13px;
            background: rgba(128, 128, 128, 0.08);
          }

          .provider-modal-timeline {
            margin-top: 22px;
          }

          .provider-modal-timeline h3 {
            margin-bottom: 12px;
            font-size: 15px;
          }

          .provider-modal-actions {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-top: 20px;
          }

          .provider-modal-actions > * {
            flex: 1;
          }

          @media (max-width: 1000px) {
            .provider-summary-grid {
              grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .provider-request-grid,
            .provider-active-grid {
              grid-template-columns: 1fr;
            }

            .provider-quick-actions {
              grid-template-columns: 1fr;
            }
          }

          @media (max-width: 700px) {
            .provider-dashboard-page {
              padding: 18px;
            }

            .provider-page-header,
            .provider-status-banner {
              flex-direction: column;
              align-items: stretch;
            }

            .provider-header-actions {
              justify-content: space-between;
            }

            .provider-summary-grid {
              grid-template-columns: 1fr 1fr;
            }

            .provider-request-details {
              grid-template-columns: 1fr;
            }

            .provider-history-item {
              grid-template-columns: 40px 1fr;
            }

            .provider-history-item .request-status,
            .provider-history-item .text-button {
              grid-column: 2;
            }

            .provider-modal-details {
              grid-template-columns: 1fr;
            }
          }
        `}
      </style>
    </AppLayout>
  );
}

export default ProviderDashboard;
