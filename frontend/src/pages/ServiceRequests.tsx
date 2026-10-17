import { API_BASE_URL } from "../api/config";
import { useCallback, useEffect, useState } from "react";
import Icon from "../components/ui/Icon";

// ======================================================
// SERVICE REQUEST TYPE
// ======================================================

interface ServiceRequest {
  request_id: number;

  emergency_id: number;

  provider_id: number | null;

  user_id: number;

  request_status: string;

  estimated_arrival: number | null;

  notes: string | null;

  requested_at: string;

  accepted_at: string | null;

  started_at: string | null;

  arrived_at: string | null;

  completed_at: string | null;

  cancelled_at: string | null;
}

// ======================================================
// API CONFIGURATION
// ======================================================


const SERVICE_REQUESTS_URL = `${API_BASE_URL}/service-requests/`;

// ======================================================
// GET AUTH TOKEN
// ======================================================

const getAuthToken = (): string | null => {
  const possibleKeys = [
    "access_token",
    "token",
    "accessToken",
    "authToken",
    "jwt",
    "userToken",
  ];

  // ----------------------------------------------
  // LOCAL STORAGE
  // ----------------------------------------------

  for (const key of possibleKeys) {
    const value = localStorage.getItem(key);

    if (value && value.trim()) {
      return value.trim();
    }
  }

  // ----------------------------------------------
  // USER OBJECT
  // ----------------------------------------------

  const userData = localStorage.getItem("user");

  if (userData) {
    try {
      const user = JSON.parse(userData);

      const userToken =
        user?.token || user?.access_token || user?.accessToken || user?.jwt;

      if (userToken && typeof userToken === "string") {
        return userToken.trim();
      }
    } catch {
      console.warn("Unable to parse stored user data.");
    }
  }

  // ----------------------------------------------
  // SESSION STORAGE
  // ----------------------------------------------

  for (const key of possibleKeys) {
    const value = sessionStorage.getItem(key);

    if (value && value.trim()) {
      return value.trim();
    }
  }

  // ----------------------------------------------
  // USER OBJECT IN SESSION STORAGE
  // ----------------------------------------------

  const sessionUserData = sessionStorage.getItem("user");

  if (sessionUserData) {
    try {
      const user = JSON.parse(sessionUserData);

      const userToken =
        user?.token || user?.access_token || user?.accessToken || user?.jwt;

      if (userToken && typeof userToken === "string") {
        return userToken.trim();
      }
    } catch {
      console.warn("Unable to parse stored session user data.");
    }
  }

  return null;
};

// ======================================================
// ERROR MESSAGE
// ======================================================

const getErrorMessage = (error: unknown): string => {
  if (typeof error === "string") {
    return error;
  }

  if (error instanceof Error) {
    return error.message;
  }

  if (error && typeof error === "object") {
    const errorObject = error as Record<string, unknown>;

    if (typeof errorObject.detail === "string") {
      return errorObject.detail;
    }

    if (typeof errorObject.message === "string") {
      return errorObject.message;
    }

    if (typeof errorObject.error === "string") {
      return errorObject.error;
    }

    try {
      return JSON.stringify(errorObject);
    } catch {
      return "An unknown error occurred.";
    }
  }

  return "Unable to load service requests.";
};

// ======================================================
// STATUS CLASS
// ======================================================

const getStatusClass = (status: string): string => {
  switch (status?.trim().toLowerCase()) {
    case "pending":
      return "status-pending";

    case "accepted":
      return "status-accepted";

    case "on_the_way":
      return "status-started";

    case "started":
      return "status-started";

    case "arrived":
      return "status-arrived";

    case "completed":
      return "status-completed";

    case "cancelled":
      return "status-cancelled";

    case "rejected":
      return "status-rejected";

    default:
      return "status-default";
  }
};

// ======================================================
// FORMAT STATUS
// ======================================================

const formatStatus = (status: string): string => {
  if (!status) {
    return "Unknown";
  }

  return status
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
};

// ======================================================
// FORMAT DATE
// ======================================================

const formatDate = (value: string | null): string => {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

// ======================================================
// GET LATEST UPDATED TIME
// ======================================================

const getUpdatedTime = (request: ServiceRequest): string => {
  const timestamps = [
    request.cancelled_at,

    request.completed_at,

    request.arrived_at,

    request.started_at,

    request.accepted_at,

    request.requested_at,
  ].filter((value): value is string => Boolean(value));

  if (timestamps.length === 0) {
    return "Not available";
  }

  const latest = timestamps.reduce((latestValue, currentValue) => {
    const latestDate = new Date(latestValue).getTime();

    const currentDate = new Date(currentValue).getTime();

    return currentDate > latestDate ? currentValue : latestValue;
  });

  return formatDate(latest);
};

// ======================================================
// COMPONENT
// ======================================================

const ServiceRequests = () => {
  const [requests, setRequests] = useState<ServiceRequest[]>([]);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState<string | null>(null);

  const [selectedRequest, setSelectedRequest] = useState<ServiceRequest | null>(
    null,
  );

  const [cancellingRequestId, setCancellingRequestId] = useState<number | null>(
    null,
  );

  // ==================================================
  // LOAD REQUESTS
  // ==================================================

  const loadRequests = useCallback(async (showLoading = false) => {
    try {
      // Only show the loading screen
      // during the initial request.

      if (showLoading) {
        setLoading(true);

        setError(null);
      }

      const token = getAuthToken();

      if (!token) {
        throw new Error("Not authenticated. Please login again.");
      }

      const cleanToken = token.trim().replace(/^Bearer\s+/i, "");

      console.log("Fetching service requests...");

      console.log("Service request API:", SERVICE_REQUESTS_URL);

      const response = await fetch(SERVICE_REQUESTS_URL, {
        method: "GET",

        headers: {
          Accept: "application/json",

          Authorization: `Bearer ${cleanToken}`,
        },
      });

      console.log("Service request status:", response.status);

      // ------------------------------------------
      // UNAUTHORIZED
      // ------------------------------------------

      if (response.status === 401) {
        throw new Error("Not authenticated. Please login again.");
      }

      // ------------------------------------------
      // FORBIDDEN
      // ------------------------------------------

      if (response.status === 403) {
        throw new Error("You do not have permission to view service requests.");
      }

      // ------------------------------------------
      // OTHER ERRORS
      // ------------------------------------------

      if (!response.ok) {
        let message = `Request failed with status ${response.status}`;

        try {
          const errorData = await response.json();

          if (typeof errorData?.detail === "string") {
            message = errorData.detail;
          } else if (typeof errorData?.message === "string") {
            message = errorData.message;
          }
        } catch {
          // Keep default message.
        }

        throw new Error(message);
      }

      // ------------------------------------------
      // SUCCESS
      // ------------------------------------------

      const data = await response.json();

      console.log("Service requests response:", data);

      if (!Array.isArray(data)) {
        throw new Error("Invalid service request response from server.");
      }

      setRequests(data as ServiceRequest[]);
    } catch (err: unknown) {
      console.error("Service request error:", err);

      // During background polling,
      // keep the current page/data visible.

      if (showLoading) {
        setError(getErrorMessage(err));
      }
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }, []);

  // ==================================================
  // INITIAL LOAD + AUTO REFRESH
  // ==================================================

  useEffect(() => {
    // Initial load

    loadRequests(true);

    // Refresh every 5 seconds

    const intervalId = window.setInterval(() => {
      loadRequests(false);
    }, 5000);

    // Cleanup

    return () => {
      window.clearInterval(intervalId);
    };
  }, [loadRequests]);

  // ==================================================
  // CANCEL REQUEST
  // ==================================================

  const cancelRequest = async (requestId: number) => {
    const confirmed = window.confirm(
      `Are you sure you want to cancel Request #${requestId}?`,
    );

    if (!confirmed) {
      return;
    }

    try {
      setError(null);

      setCancellingRequestId(requestId);

      const token = getAuthToken();

      if (!token) {
        throw new Error("Not authenticated. Please login again.");
      }

      const cleanToken = token.trim().replace(/^Bearer\s+/i, "");

      const response = await fetch(
        `${API_BASE_URL}/service-requests/${requestId}`,
        {
          method: "DELETE",

          headers: {
            Accept: "application/json",

            Authorization: `Bearer ${cleanToken}`,
          },
        },
      );

      console.log("Cancel request status:", response.status);

      if (response.status === 401) {
        throw new Error("Not authenticated. Please login again.");
      }

      if (response.status === 403) {
        throw new Error("You do not have permission to cancel this request.");
      }

      if (response.status === 404) {
        throw new Error("Service request was not found.");
      }

      if (!response.ok) {
        let message = `Failed to cancel request. Status: ${response.status}`;

        try {
          const errorData = await response.json();

          if (typeof errorData?.detail === "string") {
            message = errorData.detail;
          } else if (typeof errorData?.message === "string") {
            message = errorData.message;
          }
        } catch {
          // Keep default error.
        }

        throw new Error(message);
      }

      console.log(`Request #${requestId} cancelled successfully.`);

      setSelectedRequest(null);

      // Immediately refresh after cancellation.

      await loadRequests(false);
    } catch (err: unknown) {
      console.error("Cancel request error:", err);

      setError(getErrorMessage(err));
    } finally {
      setCancellingRequestId(null);
    }
  };

  // ==================================================
  // ESCAPE KEY
  // ==================================================

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedRequest(null);
      }
    };

    if (selectedRequest) {
      document.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [selectedRequest]);

  // ==================================================
  // SUMMARY
  // ==================================================

  const totalRequests = requests.length;

  const pendingRequests = requests.filter(
    (request) => request.request_status?.trim().toLowerCase() === "pending",
  ).length;

  const completedRequests = requests.filter(
    (request) => request.request_status?.trim().toLowerCase() === "completed",
  ).length;

  // ==================================================
  // LOADING
  // ==================================================

  if (loading) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div>
            <span className="page-eyebrow">ROADSIDE ASSISTANCE</span>

            <h1>Service Requests</h1>

            <p>Track and manage your roadside assistance requests.</p>
          </div>
        </div>

        <div className="empty-state">
          <div className="empty-state-icon"><Icon name="refresh" size={24} /></div>

          <h2>Loading service requests...</h2>

          <p>Please wait while we retrieve your service requests.</p>
        </div>
      </div>
    );
  }

  // ==================================================
  // ERROR
  // ==================================================

  if (error && requests.length === 0) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div>
            <span className="page-eyebrow">ROADSIDE ASSISTANCE</span>

            <h1>Service Requests</h1>

            <p>Track and manage your roadside assistance requests.</p>
          </div>
        </div>

        <div className="empty-state">
          <div className="empty-state-icon"><Icon name="alert" /></div>

          <h2>Unable to load service requests</h2>

          <p
            style={{
              maxWidth: "700px",

              wordBreak: "break-word",
            }}
          >
            {error}
          </p>

          <button
            type="button"
            className="primary-button"
            onClick={() => loadRequests(true)}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // ==================================================
  // EMPTY
  // ==================================================

  if (requests.length === 0) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div>
            <span className="page-eyebrow">ROADSIDE ASSISTANCE</span>

            <h1>Service Requests</h1>

            <p>Track and manage your roadside assistance requests.</p>
          </div>

          <button
            type="button"
            className="primary-button"
            onClick={() => loadRequests(true)}
          >
            Refresh
          </button>
        </div>

        <div className="empty-state">
          <div className="empty-state-icon"><Icon name="clipboard" /></div>

          <h2>No service requests yet</h2>

          <p>You don't have any roadside assistance requests at the moment.</p>
        </div>
      </div>
    );
  }

  // ==================================================
  // MAIN PAGE
  // ==================================================

  return (
    <div className="page-container">
      {/* ============================================
            HEADER
        ============================================ */}

      <div className="page-header">
        <div>
          <span className="page-eyebrow">ROADSIDE ASSISTANCE</span>

          <h1>Service Requests</h1>

          <p>Track and manage your roadside assistance requests.</p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={() => loadRequests(true)}
          disabled={loading}
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {/* ============================================
            BACKGROUND ERROR
        ============================================ */}

      {error && (
        <div
          className="empty-state"
          style={{
            marginBottom: "20px",
          }}
        >
          <p>{error}</p>
        </div>
      )}

      {/* ============================================
            SUMMARY
        ============================================ */}

      <div className="request-summary">
        <div className="summary-card">
          <strong>{totalRequests}</strong>

          <span>Total Requests</span>
        </div>

        <div className="summary-card">
          <strong>{pendingRequests}</strong>

          <span>Pending Requests</span>
        </div>

        <div className="summary-card">
          <strong>{completedRequests}</strong>

          <span>Completed Requests</span>
        </div>
      </div>

      {/* ============================================
            REQUEST CARDS
        ============================================ */}

      <div className="service-requests-grid">
        {requests.map((request) => {
          const status = request.request_status || "unknown";

          const requestId = request.request_id;

          const normalizedStatus = status.trim().toLowerCase();

          // on_the_way can still be cancelled.

          const canCancel = [
            "pending",
            "accepted",
            "on_the_way",
            "started",
            "arrived",
          ].includes(normalizedStatus);

          const isCancelling = cancellingRequestId === requestId;

          return (
            <div className="service-request-card" key={requestId}>
              {/* ==================================
                      CARD HEADER
                  ================================== */}

              <div className="service-request-header">
                <div>
                  <span className="request-label">REQUEST #{requestId}</span>

                  <h2>Roadside Assistance</h2>
                </div>

                <span className={`request-status ${getStatusClass(status)}`}>
                  {formatStatus(status)}
                </span>
              </div>

              {/* ==================================
                      DETAILS
                  ================================== */}

              <div className="service-request-details">
                <div className="request-detail">
                  <span>Emergency ID</span>

                  <strong>#{request.emergency_id}</strong>
                </div>

                <div className="request-detail">
                  <span>Provider ID</span>

                  <strong>
                    {request.provider_id !== null
                      ? `#${request.provider_id}`
                      : "Not assigned"}
                  </strong>
                </div>

                <div className="request-detail">
                  <span>Requested</span>

                  <strong>{formatDate(request.requested_at)}</strong>
                </div>

                <div className="request-detail">
                  <span>Updated</span>

                  <strong>{getUpdatedTime(request)}</strong>
                </div>
              </div>

              {/* ==================================
                      ESTIMATED ARRIVAL
                  ================================== */}

              {request.estimated_arrival !== null &&
                request.estimated_arrival !== undefined && (
                  <div className="request-detail estimated-arrival">
                    <span>Estimated Arrival</span>

                    <strong>{request.estimated_arrival} minutes</strong>
                  </div>
                )}

              {/* ==================================
                      NOTES
                  ================================== */}

              <div className="service-request-notes">
                <span>Details</span>

                <p>{request.notes || "No additional details provided."}</p>
              </div>

              {/* ==================================
                      TIMELINE
                  ================================== */}

              <div className="service-request-timeline">
                <h3>Request Timeline</h3>

                {/* CREATED */}

                <div className="timeline-item">
                  <span className="timeline-dot active" />

                  <div>
                    <strong>Request Created</strong>

                    <small>{formatDate(request.requested_at)}</small>
                  </div>
                </div>

                {/* ACCEPTED */}

                {request.accepted_at && (
                  <div className="timeline-item">
                    <span className="timeline-dot active" />

                    <div>
                      <strong>Accepted</strong>

                      <small>{formatDate(request.accepted_at)}</small>
                    </div>
                  </div>
                )}

                {/* STARTED / ON THE WAY */}

                {request.started_at && (
                  <div className="timeline-item">
                    <span className="timeline-dot active" />

                    <div>
                      <strong>Service Started</strong>

                      <small>{formatDate(request.started_at)}</small>
                    </div>
                  </div>
                )}

                {/* ARRIVED */}

                {request.arrived_at && (
                  <div className="timeline-item">
                    <span className="timeline-dot active" />

                    <div>
                      <strong>Provider Arrived</strong>

                      <small>{formatDate(request.arrived_at)}</small>
                    </div>
                  </div>
                )}

                {/* COMPLETED */}

                {request.completed_at && (
                  <div className="timeline-item">
                    <span className="timeline-dot active" />

                    <div>
                      <strong>Completed</strong>

                      <small>{formatDate(request.completed_at)}</small>
                    </div>
                  </div>
                )}

                {/* CANCELLED */}

                {request.cancelled_at && (
                  <div className="timeline-item">
                    <span className="timeline-dot active" />

                    <div>
                      <strong>Cancelled</strong>

                      <small>{formatDate(request.cancelled_at)}</small>
                    </div>
                  </div>
                )}

                {/* REJECTED */}

                {normalizedStatus === "rejected" && (
                  <div className="timeline-item">
                    <span className="timeline-dot active" />

                    <div>
                      <strong>Rejected</strong>

                      <small>
                        Request was rejected by the service workflow.
                      </small>
                    </div>
                  </div>
                )}
              </div>

              {/* ==================================
                      ACTIONS
                  ================================== */}

              <div className="service-request-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setSelectedRequest(request)}
                >
                  View Details
                </button>

                {canCancel && (
                  <button
                    type="button"
                    className="danger-button"
                    disabled={isCancelling}
                    onClick={() => cancelRequest(requestId)}
                  >
                    {isCancelling ? "Cancelling..." : "Cancel Request"}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* ============================================
            DETAILS MODAL
        ============================================ */}

      {selectedRequest && (
        <div
          className="request-modal-overlay"
          onClick={() => setSelectedRequest(null)}
        >
          <div
            className="request-modal"
            onClick={(event) => event.stopPropagation()}
          >
            {/* ======================================
                  MODAL HEADER
              ====================================== */}

            <div className="request-modal-header">
              <div>
                <span className="request-label">
                  REQUEST #{selectedRequest.request_id}
                </span>

                <h2>Service Request Details</h2>
              </div>

              <button
                type="button"
                className="request-modal-close"
                aria-label="Close details"
                onClick={() => setSelectedRequest(null)}
              >
                ×
              </button>
            </div>

            {/* ======================================
                  STATUS
              ====================================== */}

            <div className="request-modal-status-row">
              <span>Current Status</span>

              <span
                className={`request-status ${getStatusClass(
                  selectedRequest.request_status,
                )}`}
              >
                {formatStatus(selectedRequest.request_status)}
              </span>
            </div>

            {/* ======================================
                  INFORMATION
              ====================================== */}

            <div className="request-modal-grid">
              <div className="request-modal-info">
                <span>Request ID</span>

                <strong>#{selectedRequest.request_id}</strong>
              </div>

              <div className="request-modal-info">
                <span>Emergency ID</span>

                <strong>#{selectedRequest.emergency_id}</strong>
              </div>

              <div className="request-modal-info">
                <span>Provider ID</span>

                <strong>
                  {selectedRequest.provider_id !== null
                    ? `#${selectedRequest.provider_id}`
                    : "Not assigned"}
                </strong>
              </div>

              <div className="request-modal-info">
                <span>User ID</span>

                <strong>#{selectedRequest.user_id}</strong>
              </div>

              <div className="request-modal-info">
                <span>Requested</span>

                <strong>{formatDate(selectedRequest.requested_at)}</strong>
              </div>

              <div className="request-modal-info">
                <span>Updated</span>

                <strong>{getUpdatedTime(selectedRequest)}</strong>
              </div>
            </div>

            {/* ======================================
                  ESTIMATED ARRIVAL
              ====================================== */}

            {selectedRequest.estimated_arrival !== null &&
              selectedRequest.estimated_arrival !== undefined && (
                <div className="request-modal-estimated">
                  <span>Estimated Arrival</span>

                  <strong>{selectedRequest.estimated_arrival} minutes</strong>
                </div>
              )}

            {/* ======================================
                  NOTES
              ====================================== */}

            <div className="request-modal-notes">
              <span>Details</span>

              <p>
                {selectedRequest.notes || "No additional details provided."}
              </p>
            </div>

            {/* ======================================
                  TIMELINE
              ====================================== */}

            <div className="request-modal-timeline">
              <h3>Request Timeline</h3>

              {/* CREATED */}

              <div className="timeline-item">
                <span className="timeline-dot active" />

                <div>
                  <strong>Request Created</strong>

                  <small>{formatDate(selectedRequest.requested_at)}</small>
                </div>
              </div>

              {/* ACCEPTED */}

              {selectedRequest.accepted_at && (
                <div className="timeline-item">
                  <span className="timeline-dot active" />

                  <div>
                    <strong>Accepted</strong>

                    <small>{formatDate(selectedRequest.accepted_at)}</small>
                  </div>
                </div>
              )}

              {/* STARTED / ON THE WAY */}

              {selectedRequest.started_at && (
                <div className="timeline-item">
                  <span className="timeline-dot active" />

                  <div>
                    <strong>Service Started</strong>

                    <small>{formatDate(selectedRequest.started_at)}</small>
                  </div>
                </div>
              )}

              {/* ARRIVED */}

              {selectedRequest.arrived_at && (
                <div className="timeline-item">
                  <span className="timeline-dot active" />

                  <div>
                    <strong>Provider Arrived</strong>

                    <small>{formatDate(selectedRequest.arrived_at)}</small>
                  </div>
                </div>
              )}

              {/* COMPLETED */}

              {selectedRequest.completed_at && (
                <div className="timeline-item">
                  <span className="timeline-dot active" />

                  <div>
                    <strong>Completed</strong>

                    <small>{formatDate(selectedRequest.completed_at)}</small>
                  </div>
                </div>
              )}

              {/* CANCELLED */}

              {selectedRequest.cancelled_at && (
                <div className="timeline-item">
                  <span className="timeline-dot active" />

                  <div>
                    <strong>Cancelled</strong>

                    <small>{formatDate(selectedRequest.cancelled_at)}</small>
                  </div>
                </div>
              )}

              {/* REJECTED */}

              {selectedRequest.request_status?.trim().toLowerCase() ===
                "rejected" && (
                <div className="timeline-item">
                  <span className="timeline-dot active" />

                  <div>
                    <strong>Rejected</strong>

                    <small>Request was rejected by the service workflow.</small>
                  </div>
                </div>
              )}
            </div>

            {/* ======================================
                  MODAL FOOTER
              ====================================== */}

            <div className="request-modal-footer">
              {[
                "pending",
                "accepted",
                "on_the_way",
                "started",
                "arrived",
              ].includes(
                selectedRequest.request_status?.trim().toLowerCase(),
              ) && (
                <button
                  type="button"
                  className="danger-button"
                  disabled={cancellingRequestId === selectedRequest.request_id}
                  onClick={() => cancelRequest(selectedRequest.request_id)}
                >
                  {cancellingRequestId === selectedRequest.request_id
                    ? "Cancelling..."
                    : "Cancel Request"}
                </button>
              )}

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
    </div>
  );
};

export default ServiceRequests;
