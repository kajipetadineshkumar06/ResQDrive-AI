import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import AppLayout from "../components/layout/AppLayout";
import Icon from "../components/ui/Icon";
import { useAuth } from "../context/AuthContext";
import api from "../api/axios";

import { getVehicles, type Vehicle } from "../api/vehicles";

// ======================================================
// SERVICE REQUEST TYPE
// ======================================================

interface ServiceRequest {
  request_id: number;

  emergency_id: number;

  provider_id: number;

  user_id: number;

  request_status: string;

  estimated_arrival?: number | null;

  notes?: string | null;

  requested_at: string;

  accepted_at?: string | null;

  started_at?: string | null;

  arrived_at?: string | null;

  completed_at?: string | null;

  cancelled_at?: string | null;
}

// ======================================================
// DASHBOARD
// ======================================================

const Dashboard = () => {
  const { user } = useAuth();

  const navigate = useNavigate();

  // ====================================================
  // VEHICLES
  // ====================================================

  const [vehicles, setVehicles] = useState<Vehicle[]>([]);

  const [vehiclesLoading, setVehiclesLoading] = useState(true);

  // ====================================================
  // SERVICE REQUESTS
  // ====================================================

  const [serviceRequests, setServiceRequests] = useState<ServiceRequest[]>([]);

  const [requestsLoading, setRequestsLoading] = useState(true);

  // ====================================================
  // LOAD VEHICLES
  // ====================================================

  useEffect(() => {
    const loadVehicles = async () => {
      try {
        setVehiclesLoading(true);

        const data = await getVehicles();

        console.log("Dashboard vehicles:", data);

        setVehicles(data);
      } catch (error) {
        console.error("Dashboard vehicle error:", error);

        setVehicles([]);
      } finally {
        setVehiclesLoading(false);
      }
    };

    loadVehicles();
  }, []);

  // ====================================================
  // LOAD SERVICE REQUESTS
  // ====================================================

  useEffect(() => {
    let isMounted = true;

    const loadServiceRequests = async () => {
      try {
        const response = await api.get<ServiceRequest[]>("/service-requests/");

        if (!isMounted) {
          return;
        }

        console.log("Dashboard service requests:", response.data);

        if (Array.isArray(response.data)) {
          setServiceRequests(response.data);
        } else {
          setServiceRequests([]);
        }
      } catch (error) {
        console.error("Dashboard service request error:", error);
      } finally {
        if (isMounted) {
          setRequestsLoading(false);
        }
      }
    };

    // ==================================================
    // INITIAL LOAD
    // ==================================================

    setRequestsLoading(true);

    loadServiceRequests();

    // ==================================================
    // AUTO REFRESH EVERY 5 SECONDS
    // ==================================================

    const intervalId = window.setInterval(loadServiceRequests, 5000);

    // ==================================================
    // CLEANUP
    // ==================================================

    return () => {
      isMounted = false;

      window.clearInterval(intervalId);
    };
  }, []);

  // ====================================================
  // REQUEST STATISTICS
  // ====================================================

  const totalRequests = serviceRequests.length;

  const pendingRequests = serviceRequests.filter(
    (request) => request.request_status?.trim().toLowerCase() === "pending",
  ).length;

  const completedRequests = serviceRequests.filter(
    (request) => request.request_status?.trim().toLowerCase() === "completed",
  ).length;

  // ====================================================
  // ACTIVE REQUESTS
  // ====================================================

  const activeRequests = serviceRequests.filter((request) => {
    const status = request.request_status?.trim().toLowerCase();

    return (
      status === "accepted" ||
      status === "on_the_way" ||
      status === "started" ||
      status === "arrived"
    );
  }).length;

  // ====================================================
  // RECENT REQUESTS
  // ====================================================

  const recentRequests = [...serviceRequests]
    .sort(
      (a, b) =>
        new Date(b.requested_at).getTime() - new Date(a.requested_at).getTime(),
    )
    .slice(0, 3);

  // ====================================================
  // FORMAT DATE
  // ====================================================

  const formatDate = (dateString: string) => {
    if (!dateString) {
      return "N/A";
    }

    const date = new Date(dateString);

    if (Number.isNaN(date.getTime())) {
      return dateString;
    }

    return date.toLocaleString("en-IN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // ====================================================
  // STATUS CLASS
  // ====================================================

  const getStatusClass = (status: string) => {
    const normalized = status?.trim().toLowerCase();

    if (normalized === "pending") {
      return "status-pending";
    }

    if (normalized === "accepted") {
      return "status-accepted";
    }

    // Backend status:
    // on_the_way
    //
    // Reuse existing started CSS.

    if (normalized === "on_the_way") {
      return "status-started";
    }

    if (normalized === "started") {
      return "status-started";
    }

    if (normalized === "arrived") {
      return "status-arrived";
    }

    if (normalized === "completed") {
      return "status-completed";
    }

    if (normalized === "cancelled") {
      return "status-cancelled";
    }

    if (normalized === "rejected") {
      return "status-rejected";
    }

    return "status-default";
  };

  // ====================================================
  // FORMAT STATUS
  // ====================================================

  const formatStatus = (status: string) => {
    if (!status) {
      return "Unknown";
    }

    return status
      .replace(/_/g, " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  };

  // ====================================================
  // RENDER
  // ====================================================

  return (
    <AppLayout>
      <div className="dashboard-page">
        {/* ==========================================
            PAGE INTRO
        ========================================== */}

        <section className="dashboard-intro">
          <div>
            <span className="eyebrow">RESQDRIVE AI PLATFORM</span>

            <h2>Welcome back, {user?.full_name || "User"}</h2>

            <p>
              Monitor your vehicles, assistance requests, roadside emergencies
              and AI-powered services from one place.
            </p>
          </div>

          <div className="system-indicator">
            <span className="status-dot" />

            <span>All systems operational</span>
          </div>
        </section>

        {/* ==========================================
            STATISTICS
        ========================================== */}

        <section className="stats-grid">
          {/* VEHICLES */}

          <div className="stat-card">
            <div className="stat-card-top">
              <span className="stat-icon blue"><Icon name="car" /></span>

              <span className="stat-label">VEHICLES</span>
            </div>

            <strong>{vehiclesLoading ? "..." : vehicles.length}</strong>

            <p>Registered vehicles</p>
          </div>

          {/* REQUESTS */}

          <div className="stat-card">
            <div className="stat-card-top">
              <span className="stat-icon purple"><Icon name="clipboard" /></span>

              <span className="stat-label">REQUESTS</span>
            </div>

            <strong>{requestsLoading ? "..." : totalRequests}</strong>

            <p>Total service requests</p>
          </div>

          {/* ACTIVE */}

          <div className="stat-card">
            <div className="stat-card-top">
              <span className="stat-icon green">●</span>

              <span className="stat-label">ACTIVE</span>
            </div>

            <strong>{requestsLoading ? "..." : activeRequests}</strong>

            <p>Active assistance</p>
          </div>

          {/* AI ASSIST */}

          <div className="stat-card">
            <div className="stat-card-top">
              <span className="stat-icon orange"><Icon name="bot" /></span>

              <span className="stat-label">AI ASSIST</span>
            </div>

            <strong>24/7</strong>

            <p>AI availability</p>
          </div>
        </section>

        {/* ==========================================
            MAIN GRID
        ========================================== */}

        <section className="dashboard-main-grid">
          {/* EMERGENCY */}

          <div className="emergency-panel">
            <div className="emergency-content">
              <span className="emergency-badge">EMERGENCY SUPPORT</span>

              <h3>Need roadside assistance?</h3>

              <p>
                Get immediate help for vehicle breakdowns, accidents, flat
                tyres, battery problems and other roadside emergencies.
              </p>

              <button
                className="emergency-button"
                onClick={() => navigate("/emergency/create")}
              >
                Request Emergency Help
              </button>
            </div>

            <div className="emergency-visual">
              <div className="emergency-circle"><Icon name="siren" size={38} /></div>
            </div>
          </div>

          {/* QUICK ACTIONS */}

          <div className="quick-actions-card">
            <div className="section-heading">
              <div>
                <span className="eyebrow">QUICK ACTIONS</span>

                <h3>What would you like to do?</h3>
              </div>
            </div>

            <div className="quick-actions">
              {/* ADD VEHICLE */}

              <button
                className="quick-action"
                onClick={() => navigate("/vehicles/add")}
              >
                <span><Icon name="plus" /></span>

                <div>
                  <strong>Add Vehicle</strong>

                  <small>Register your vehicle</small>
                </div>
              </button>

              {/* SERVICE REQUEST */}

              <button
                className="quick-action"
                onClick={() => navigate("/service-requests")}
              >
                <span><Icon name="clipboard" /></span>

                <div>
                  <strong>Service Request</strong>

                  <small>View roadside requests</small>
                </div>
              </button>

              {/* ASK AI */}

              <button className="quick-action" onClick={() => navigate("/ai")}>
                <span><Icon name="bot" /></span>

                <div>
                  <strong>Ask AI</strong>

                  <small>Diagnose a vehicle problem</small>
                </div>
              </button>

              {/* TRACK PROVIDER */}

              <button
                className="quick-action"
                onClick={() => navigate("/tracking")}
              >
                <span><Icon name="mapPin" /></span>

                <div>
                  <strong>Track Provider</strong>

                  <small>View live service location</small>
                </div>
              </button>
            </div>
          </div>
        </section>

        {/* ==========================================
            LOWER GRID
        ========================================== */}

        <section className="dashboard-lower-grid">
          {/* RECENT REQUESTS */}

          <div className="dashboard-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">ACTIVITY</span>

                <h3>Recent service requests</h3>
              </div>

              <button
                className="text-button"
                onClick={() => navigate("/service-requests")}
              >
                View all
              </button>
            </div>

            {/* LOADING */}

            {requestsLoading && (
              <div className="empty-state">
                <div className="empty-icon"><Icon name="refresh" /></div>

                <h4>Loading requests...</h4>

                <p>Getting your latest roadside assistance activity.</p>
              </div>
            )}

            {/* EMPTY */}

            {!requestsLoading && recentRequests.length === 0 && (
              <div className="empty-state">
                <div className="empty-icon"><Icon name="clipboard" /></div>

                <h4>No service requests yet</h4>

                <p>
                  Your recent roadside assistance requests will appear here.
                </p>
              </div>
            )}

            {/* RECENT REQUESTS */}

            {!requestsLoading && recentRequests.length > 0 && (
              <div className="recent-requests-list">
                {recentRequests.map((request) => (
                  <div
                    className="recent-request-item"
                    key={request.request_id}
                    onClick={() => navigate("/service-requests")}
                  >
                    <div className="recent-request-icon"><Icon name="wrench" /></div>

                    <div className="recent-request-info">
                      <strong>Service Request #{request.request_id}</strong>

                      <small>
                        Emergency #{request.emergency_id}
                        {" • "}
                        Provider #{request.provider_id}
                      </small>

                      <small>{formatDate(request.requested_at)}</small>
                    </div>

                    <span
                      className={`request-status ${getStatusClass(
                        request.request_status,
                      )}`}
                    >
                      {formatStatus(request.request_status)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* AI PANEL */}

          <div className="dashboard-panel ai-panel">
            <div className="ai-header">
              <div className="ai-icon"><Icon name="sparkles" /></div>

              <div>
                <span className="eyebrow">INTELLIGENT ASSISTANCE</span>

                <h3>ResQDrive AI</h3>
              </div>
            </div>

            <p>
              Describe your vehicle problem and our AI assistant can help
              identify possible causes and recommend the appropriate roadside
              service.
            </p>

            <button className="primary-button" onClick={() => navigate("/ai")}>
              Start AI Diagnosis
            </button>
          </div>
        </section>

        {/* ==========================================
            REQUEST OVERVIEW
        ========================================== */}

        <section className="dashboard-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">REQUEST OVERVIEW</span>

              <h3>Service request status</h3>
            </div>
          </div>

          <div className="request-overview-grid">
            <div>
              <strong>{requestsLoading ? "..." : pendingRequests}</strong>

              <span>Pending</span>
            </div>

            <div>
              <strong>{requestsLoading ? "..." : activeRequests}</strong>

              <span>Active</span>
            </div>

            <div>
              <strong>{requestsLoading ? "..." : completedRequests}</strong>

              <span>Completed</span>
            </div>
          </div>
        </section>
      </div>
    </AppLayout>
  );
};

export default Dashboard;
