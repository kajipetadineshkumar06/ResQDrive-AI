import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Icon from "../components/ui/Icon";
import * as L from "leaflet";
import "leaflet/dist/leaflet.css";
import api from "../api/axios";
import { API_BASE_URL } from "../api/config";
import { useAuth } from "../context/AuthContext";
import styles from "./Tracking.module.css";

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

interface TrackingMessage {
  event: string;
  emergency_id?: number;
  request_id?: number;
  provider_id?: number;
  status?: string;
  message?: string;
  latitude?: number;
  longitude?: number;
  distance_meters?: number | null;
  eta?: string | null;
  duration?: string | null;
  polyline?: string | null;

  // AI ETA prediction fields
  ai_eta?: string | null;
  ai_predicted_duration?: string | null;
  ai_eta_confidence?: number | null;
  ai_eta_source?: string | null;
}

interface ProviderLocation {
  provider_id: number;
  latitude: number;
  longitude: number;
  tracking: boolean;
  updated_at?: string;
}

interface EmergencyLocation {
  emergency_id: number;
  location_lat: number | string;
  location_lng: number | string;
}

const TRACKABLE_STATUSES = [
  "pending",
  "accepted",
  "on_the_way",
  "arrived",
  "in_progress",
  "completed",
];
const LIVE_STATUSES = ["accepted", "on_the_way", "arrived", "in_progress"];

function getToken(): string | null {
  return localStorage.getItem("access_token")?.trim() || null;
}

function getWebSocketUrl(emergencyId: number, token: string): string {
  const apiUrl = new URL(
    API_BASE_URL,

    window.location.origin,
  );
  const protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";

  return `${protocol}//${apiUrl.host}/ws/live-tracking/${emergencyId}?token=${encodeURIComponent(
    token,
  )}`;
}

const routeLineOptions: L.PolylineOptions = {
  color: "#2563eb",
  weight: 5,
  opacity: 0.78,
  lineCap: "round",
  lineJoin: "round",
};

function decodeGooglePolyline(encoded: string): L.LatLngTuple[] {
  if (!encoded) {
    return [];
  }

  const points: L.LatLngTuple[] = [];
  let index = 0;
  let latitude = 0;
  let longitude = 0;

  const decodeValue = (): number => {
    let result = 0;
    let shift = 0;

    while (index < encoded.length) {
      const value = encoded.charCodeAt(index++) - 63;

      if (value < 0) {
        throw new Error("Invalid Google polyline value.");
      }

      result |= (value & 0x1f) << shift;
      shift += 5;

      if (shift > 30) {
        throw new Error("Google polyline value is too long.");
      }

      if (value < 0x20) {
        return result & 1 ? ~(result >> 1) : result >> 1;
      }
    }

    throw new Error("Google polyline is truncated.");
  };

  while (index < encoded.length) {
    latitude += decodeValue();
    longitude += decodeValue();

    const decodedLatitude = latitude / 1e5;
    const decodedLongitude = longitude / 1e5;

    if (
      !Number.isFinite(decodedLatitude) ||
      !Number.isFinite(decodedLongitude) ||
      decodedLatitude < -90 ||
      decodedLatitude > 90 ||
      decodedLongitude < -180 ||
      decodedLongitude > 180
    ) {
      throw new Error("Google polyline coordinates are invalid.");
    }

    points.push([decodedLatitude, decodedLongitude]);
  }

  return points;
}

export default function Tracking() {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const locationRequestKeyRef = useRef<string | null>(null);

  const mapElementRef = useRef<HTMLDivElement | null>(null);

  const mapRef = useRef<L.Map | null>(null);
  const providerMarkerRef = useRef<L.Marker | null>(null);
  const customerMarkerRef = useRef<L.Marker | null>(null);
  const polylineRef = useRef<L.Polyline | null>(null);

  const [loading, setLoading] = useState(true);

  const [request, setRequest] = useState<ServiceRequest | null>(null);

  const [tracking, setTracking] = useState<TrackingMessage | null>(null);

  const [providerLocation, setProviderLocation] =
    useState<ProviderLocation | null>(null);

  const [emergencyLocation, setEmergencyLocation] =
    useState<EmergencyLocation | null>(null);

  const [connectionStatus, setConnectionStatus] = useState("Loading...");

  const [error, setError] = useState<string | null>(null);

  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  // =========================================================
  // LOAD ACTIVE SERVICE REQUEST
  // =========================================================

  useEffect(() => {
    if (authLoading) {
      return;
    }

    if (!user) {
      setLoading(false);
      setError("Please sign in to view live tracking.");
      return;
    }

    let cancelled = false;
    let requestInFlight = false;
    let hasLoadedOnce = false;

    async function loadRequests(showLoading = false) {
      if (requestInFlight) {
        return;
      }

      requestInFlight = true;
      try {
        if (showLoading) {
          setLoading(true);
        }

        const response = await api.get<ServiceRequest[]>("/service-requests/");

        if (cancelled) {
          return;
        }

        const requests = Array.isArray(response.data) ? response.data : [];

        const activeRequests = requests.filter((item) =>
          TRACKABLE_STATUSES.includes(item.request_status),
        );

        activeRequests.sort(
          (a, b) =>
            new Date(b.requested_at).getTime() -
            new Date(a.requested_at).getTime(),
        );

        const latestRequest = activeRequests[0] || null;

        setRequest(latestRequest);
        setError(null);

        if (!latestRequest) {
          setConnectionStatus("No active tracking");
        }
      } catch (err) {
        console.error("Failed to load service requests:", err);

        if (!cancelled && !hasLoadedOnce) {
          setError("Unable to load your service requests.");
        }
      } finally {
        requestInFlight = false;
        hasLoadedOnce = true;
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadRequests(true);
    const refreshTimer = window.setInterval(() => {
      void loadRequests();
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(refreshTimer);
    };
  }, [authLoading, user?.user_id]);

  // =========================================================
  // CUSTOMER WEBSOCKET
  // =========================================================

  useEffect(() => {
    if (!request) {
      return;
    }

    if (request.provider_id === null) {
      setConnectionStatus("Waiting for provider assignment");
      return;
    }

    if (!LIVE_STATUSES.includes(request.request_status)) {
      setConnectionStatus(
        request.request_status === "pending"
          ? "Waiting for provider to accept"
          : "Service completed",
      );
      return;
    }

    const token = getToken();

    if (!token) {
      setError("Authentication token not found. Please login again.");

      setConnectionStatus("Authentication required");

      return;
    }

    /*
     * IMPORTANT:
     * Create stable constants after the null checks.
     * This prevents TypeScript errors inside nested
     * functions and WebSocket callbacks.
     */

    const activeRequest = request;
    const authToken = token;
    const emergencyId = activeRequest.emergency_id;
    const providerId = activeRequest.provider_id;

    // Keep the provider ID non-null for every asynchronous callback below.
    // TypeScript does not preserve the earlier check once this value is captured.
    if (providerId === null) {
      return;
    }

    const verifiedProviderId: number = providerId;

    let stopped = false;

    function connectWebSocket() {
      if (stopped) {
        return;
      }

      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }

      setConnectionStatus("Connecting...");

      setError(null);

      const websocketUrl = getWebSocketUrl(emergencyId, authToken);

      console.log("Connecting customer WebSocket:", websocketUrl);

      const socket = new WebSocket(websocketUrl);

      socketRef.current = socket;

      // -------------------------------------------------------
      // OPEN
      // -------------------------------------------------------

      socket.onopen = () => {
        if (stopped) {
          return;
        }

        console.log("✅ Customer WebSocket connected");

        setConnectionStatus("Live tracking connected");
      };

      // -------------------------------------------------------
      // MESSAGE
      // -------------------------------------------------------

      socket.onmessage = (event) => {
        if (stopped) {
          return;
        }

        try {
          const message: TrackingMessage = JSON.parse(event.data);

          if (
            !message ||
            typeof message !== "object" ||
            typeof message.event !== "string"
          ) {
            throw new Error("Invalid tracking message shape.");
          }

          if (
            message.emergency_id !== undefined &&
            message.emergency_id !== emergencyId
          ) {
            return;
          }

          if (
            message.request_id !== undefined &&
            message.request_id !== activeRequest.request_id
          ) {
            return;
          }

          console.log("📍 Customer tracking message:", message);

          setTracking((previous) => ({
            ...(previous || { event: message.event }),
            ...message,
          }));

          // ---------------------------------------------------
          // TRACKING CONNECTED
          // ---------------------------------------------------

          if (message.event === "tracking_connected") {
            setConnectionStatus("Live tracking connected");
          }

          // ---------------------------------------------------
          // PROVIDER LOCATION
          // ---------------------------------------------------

          if (message.event === "provider_location") {
            setConnectionStatus("Receiving live GPS");

            setLastUpdated(new Date().toLocaleTimeString());

            if (
              typeof message.latitude === "number" &&
              Number.isFinite(message.latitude) &&
              typeof message.longitude === "number" &&
              Number.isFinite(message.longitude)
            ) {
              setProviderLocation({
                provider_id: message.provider_id ?? verifiedProviderId,
                latitude: message.latitude,
                longitude: message.longitude,
                tracking: true,
              });
            }

            // Update displayed request status
            if (message.status) {
              setRequest((previous) => {
                if (!previous) {
                  return previous;
                }

                return {
                  ...previous,
                  request_status: message.status!,
                };
              });
            }
          }
        } catch (err) {
          console.error("Invalid WebSocket message:", err);
        }
      };

      // -------------------------------------------------------
      // ERROR
      // -------------------------------------------------------

      socket.onerror = (event) => {
        console.error("❌ Customer WebSocket error:", event);

        setConnectionStatus("Connection error");
      };

      // -------------------------------------------------------
      // CLOSE
      // -------------------------------------------------------

      socket.onclose = (event) => {
        if (stopped) {
          return;
        }

        console.log("🔌 Customer WebSocket closed:", event.code, event.reason);

        setConnectionStatus("Disconnected");

        if (reconnectTimerRef.current) {
          window.clearTimeout(reconnectTimerRef.current);
        }

        reconnectTimerRef.current = window.setTimeout(() => {
          connectWebSocket();
        }, 3000);
      };
    }

    connectWebSocket();

    // -------------------------------------------------------
    // CLEANUP
    // -------------------------------------------------------

    return () => {
      stopped = true;

      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);

        reconnectTimerRef.current = null;
      }

      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [request?.request_id, request?.provider_id, request?.request_status]);

  // =========================================================
  // FETCH CURRENT PROVIDER LOCATION
  // =========================================================

  useEffect(() => {
    if (!request || request.provider_id === null) {
      return;
    }

    const providerId = request.provider_id;
    const requestKey = `${request.request_id}:${providerId}`;

    if (locationRequestKeyRef.current !== requestKey) {
      locationRequestKeyRef.current = requestKey;
      setProviderLocation(null);
      setLastUpdated(null);
    }

    // Poll REST as a fallback while the provider is travelling; WebSocket
    // remains the primary low-latency location channel.
    if (request.request_status !== "on_the_way") {
      return;
    }

    let cancelled = false;
    let requestInFlight = false;

    async function loadCurrentLocation() {
      if (requestInFlight || cancelled) {
        return;
      }

      requestInFlight = true;
      try {
        const response = await api.get<ProviderLocation>(
          `/provider-location/${providerId}`,
        );

        if (!cancelled && response.data?.tracking) {
          setProviderLocation(response.data);
          setLastUpdated(
            response.data.updated_at
              ? new Date(response.data.updated_at).toLocaleTimeString()
              : new Date().toLocaleTimeString(),
          );
        }
      } catch {
        // The WebSocket may still deliver the next GPS update.
      } finally {
        requestInFlight = false;
      }
    }

    void loadCurrentLocation();
    const locationTimer = window.setInterval(
      () => void loadCurrentLocation(),
      5000,
    );

    return () => {
      cancelled = true;
      window.clearInterval(locationTimer);
    };
  }, [request?.request_id, request?.provider_id, request?.request_status]);

  // =========================================================
  // FETCH CUSTOMER EMERGENCY LOCATION
  // =========================================================

  useEffect(() => {
    if (!request) {
      return;
    }

    const emergencyId = request.emergency_id;
    let cancelled = false;

    async function loadEmergencyLocation() {
      try {
        const response = await api.get<EmergencyLocation>(
          `/emergencies/${emergencyId}`,
        );

        if (!cancelled) {
          setEmergencyLocation(response.data);
        }
      } catch (err) {
        console.log("Customer emergency location not available yet.");
      }
    }

    loadEmergencyLocation();

    return () => {
      cancelled = true;
    };
  }, [request?.emergency_id]);

  // =========================================================
  // LIVE LEAFLET MAP
  // =========================================================

  useEffect(() => {
    if (!mapElementRef.current) {
      return;
    }

    if (!mapRef.current) {
      mapRef.current = L.map(mapElementRef.current, {
        zoomControl: true,
      }).setView([17.385, 78.4867], 13);

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 19,
      }).addTo(mapRef.current);
    }

    const map = mapRef.current;
    const bounds: L.LatLngTuple[] = [];

    if (emergencyLocation) {
      const customerPosition: L.LatLngTuple = [
        Number(emergencyLocation.location_lat),
        Number(emergencyLocation.location_lng),
      ];

      if (!customerMarkerRef.current) {
        customerMarkerRef.current = L.marker(customerPosition, {
          icon: L.divIcon({
            className: "",
            html: '<div style="transform:translate(-50%,-100%);color:#0f766e"><svg xmlns="http://www.w3.org/2000/svg" width="34" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5" fill="white"/></svg></div>',
            iconSize: [30, 38],
            iconAnchor: [15, 38],
          }),
        })
          .bindPopup("Customer emergency location")
          .addTo(map);
      } else {
        customerMarkerRef.current.setLatLng(customerPosition);
      }

      bounds.push(customerPosition);
    }

    if (providerLocation) {
      const providerPosition: L.LatLngTuple = [
        providerLocation.latitude,
        providerLocation.longitude,
      ];

      if (!providerMarkerRef.current) {
        providerMarkerRef.current = L.marker(providerPosition, {
          icon: L.divIcon({
            className: "",
            html: '<div style="transform:translate(-50%,-100%);color:#0b1220"><svg xmlns="http://www.w3.org/2000/svg" width="38" height="32" viewBox="0 0 24 24" fill="#0b1220" stroke="white" stroke-width="1.5"><path d="m5 11 1.5-4.5A2 2 0 0 1 8.4 5h7.2a2 2 0 0 1 1.9 1.5L19 11H5Z"/><path d="M3 11h18v7H3z"/><circle cx="7" cy="18" r="1.5" fill="white"/><circle cx="17" cy="18" r="1.5" fill="white"/></svg></div>',
            iconSize: [30, 38],
            iconAnchor: [15, 38],
          }),
        })
          .bindPopup("Service provider")
          .addTo(map);
      } else {
        providerMarkerRef.current.setLatLng(providerPosition);
      }

      bounds.push(providerPosition);
    }

    const clearRoutePolyline = () => {
      if (polylineRef.current) {
        polylineRef.current.remove();
        polylineRef.current = null;
      }
    };

    if (tracking?.polyline) {
      try {
        const routePoints = decodeGooglePolyline(tracking.polyline);

        if (routePoints.length >= 2) {
          if (!polylineRef.current) {
            polylineRef.current = L.polyline(
              routePoints,
              routeLineOptions,
            ).addTo(map);
          } else {
            polylineRef.current.setLatLngs(routePoints);
          }
        } else {
          clearRoutePolyline();
        }
      } catch (routeError) {
        console.warn("Unable to render Google route polyline:", routeError);
        clearRoutePolyline();
      }
    } else {
      clearRoutePolyline();
    }

    if (bounds.length === 1) {
      map.setView(bounds[0], 15);
    }

    if (bounds.length > 1) {
      map.fitBounds(bounds, {
        padding: [50, 50],
        maxZoom: 15,
      });
    }
  }, [
    providerLocation,
    emergencyLocation,
    tracking?.polyline,
    request?.request_id,
  ]);

  useEffect(() => {
    return () => {
      polylineRef.current?.remove();
      polylineRef.current = null;
      mapRef.current?.remove();
      mapRef.current = null;
      providerMarkerRef.current = null;
      customerMarkerRef.current = null;
    };
  }, []);

  // =========================================================
  // FORMAT STATUS
  // =========================================================

  function formatStatus(status: string): string {
    const normalizedStatus =
      typeof status === "string" ? status.trim().toLowerCase() : "";

    switch (normalizedStatus) {
      case "accepted":
        return "Accepted";

      case "on_the_way":
        return "On The Way";

      case "arrived":
        return "Provider Arrived";
      case "in_progress":
        return "Service In Progress";

      case "completed":
        return "Completed";

      case "cancelled":
        return "Cancelled";

      case "":
      case "unknown":
        return "Status unavailable";

      default:
        return status.trim();
    }
  }

  // =========================================================
  // FORMAT DISTANCE
  // =========================================================

  function formatDistance(meters: number | null | undefined): string {
    if (typeof meters !== "number" || !Number.isFinite(meters) || meters <= 0) {
      return "Calculating...";
    }

    if (meters < 1000) {
      return `${Math.round(meters)} m`;
    }

    return `${(meters / 1000).toFixed(2)} km`;
  }

  // =========================================================
  // FORMAT ETA
  // =========================================================

  function formatEta(eta: string | null | undefined): string {
    if (typeof eta !== "string" || !eta.trim()) {
      return "Calculating...";
    }

    const normalizedEta = eta.trim().toLowerCase();

    if (
      normalizedEta === "unknown" ||
      normalizedEta === "0" ||
      normalizedEta === "0 min"
    ) {
      return "Calculating...";
    }

    return eta.trim();
  }

  // =========================================================
  // FORMAT ROUTE DURATION
  // =========================================================

  function formatDuration(duration: string | null | undefined): string {
    if (typeof duration !== "string") {
      return "Calculating...";
    }

    const match = duration.trim().match(/^(\d+(?:\.\d+)?)s$/);

    if (!match) {
      return "Calculating...";
    }

    const seconds = Number(match[1]);

    if (!Number.isFinite(seconds) || seconds <= 0) {
      return "Calculating...";
    }

    if (seconds < 60) {
      return "< 1 min";
    }

    return `${Math.round(seconds / 60)} min`;
  }

  // =========================================================
  // FORMAT AI ETA CONFIDENCE
  // =========================================================

  function formatAiConfidence(
    confidence: number | null | undefined,
  ): string {
    if (
      typeof confidence !== "number" ||
      !Number.isFinite(confidence) ||
      confidence < 0
    ) {
      return "Calculating...";
    }

    return `${Math.round(Math.min(confidence, 100))}%`;
  }

  // =========================================================
  // LOADING SCREEN
  // =========================================================

  if (loading) {
    return (
      <div className={styles.trackingPage} aria-busy="true">
        <div
          className={`${styles.trackingStateShell} ${styles.stateCardLoading}`}
        >
          <div
            className={`${styles.trackingStateCard} ${styles.stateCardLoading}`}
          >
            <div className={styles.stateIcon} aria-hidden="true">
              <span className={styles.stateMark} />
            </div>

            <span className={styles.stateEyebrow}>Live assistance</span>

            <h1 className={styles.stateTitle}>Live tracking</h1>

            <p className={styles.stateDescription}>
              Loading your active service request...
            </p>

            <div className={styles.loadingSkeleton} aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // =========================================================
  // ERROR SCREEN
  // =========================================================

  if (error) {
    return (
      <div className={styles.trackingPage}>
        <div className={styles.trackingStateShell}>
          <div
            className={`${styles.trackingStateCard} ${styles.stateCardError}`}
            role="alert"
          >
            <div className={styles.stateIcon} aria-hidden="true">
              <span className={styles.stateMark} />
            </div>

            <span className={styles.stateEyebrow}>Request unavailable</span>

            <h1 className={styles.stateTitle}>Live tracking</h1>

            <p className={styles.stateDescription}>{error}</p>

            <button
              type="button"
              className={styles.primaryAction}
              onClick={() => window.location.reload()}
            >
              Try loading the request again
            </button>
          </div>
        </div>
      </div>
    );
  }

  // =========================================================
  // NO ACTIVE REQUEST
  // =========================================================

  if (!request) {
    return (
      <div className={styles.trackingPage}>
        <div className={styles.trackingStateShell}>
          <div
            className={`${styles.trackingStateCard} ${styles.stateCardEmpty}`}
          >
            <div className={styles.stateIcon} aria-hidden="true">
              <span className={styles.stateMark} />
            </div>

            <span className={styles.stateEyebrow}>No active assistance</span>

            <h1 className={styles.stateTitle}>Live tracking</h1>

            <p className={styles.stateDescription}>
              You don't have an active service request to track.
            </p>

            <button
              type="button"
              className={styles.primaryAction}
              onClick={() => navigate("/service-requests")}
            >
              View service requests
            </button>
          </div>
        </div>
      </div>
    );
  }

  // =========================================================
  // WAITING FOR PROVIDER
  // =========================================================

  if (request.provider_id === null) {
    return (
      <div className={styles.trackingPage}>
        <div className={`${styles.trackingFrame} ${styles.stateCardWaiting}`}>
          <div className={styles.stateHeader}>
            <div className={styles.stateIcon} aria-hidden="true">
              <span className={styles.stateMark} />
            </div>

            <div className={styles.stateHeaderCopy}>
              <span className={styles.stateEyebrow}>Provider assignment</span>

              <h1 className={styles.stateTitle}>Finding a service provider</h1>

              <p className={styles.stateDescription}>
                We are currently looking for an available provider near you.
              </p>
            </div>
          </div>

          <div
            className={styles.serviceStatus}
            role="status"
            aria-live="polite"
          >
            <div className={styles.serviceStatusCopy}>
              <span className={styles.serviceStatusLabel}>Current status</span>
              <strong>Waiting for assignment</strong>
            </div>
            <span className={styles.statusDot} aria-hidden="true" />
          </div>
        </div>
      </div>
    );
  }

  const connectionStatusClass =
    connectionStatus === "Receiving live GPS"
      ? styles.connectionStatusLive
      : connectionStatus === "Live tracking connected"
        ? styles.connectionStatusConnected
        : connectionStatus === "Connection error" ||
            connectionStatus === "Disconnected"
          ? styles.connectionStatusError
          : styles.connectionStatusWaiting;

  const requestStatusClass =
    request.request_status === "accepted"
      ? styles.statusAccepted
      : request.request_status === "on_the_way"
        ? styles.statusOnTheWay
      : request.request_status === "arrived"
        ? styles.statusArrived
        : request.request_status === "in_progress"
          ? styles.statusArrived
          : request.request_status === "completed"
            ? styles.statusCompleted
            : request.request_status === "cancelled"
              ? styles.statusCancelled
              : styles.statusUnavailable;

  // =========================================================
  // MAIN TRACKING PAGE
  // =========================================================

  return (
    <main className={styles.trackingPage}>
      <div className={styles.trackingFrame}>
        {/* LIVE HEADER */}
        <header className={styles.trackingHeader}>
          <div className={styles.headerCopy}>
            <span className={styles.sectionEyebrow}>Live assistance</span>

            <h1>Live tracking</h1>

            <p>
              Follow your service provider and arrival estimate in real time.
            </p>
          </div>

          <div className={styles.headerStatusGroup}>
            <div
              className={`${styles.connectionStatus} ${connectionStatusClass}`}
              role="status"
              aria-live="polite"
            >
              <span className={styles.statusDot} aria-hidden="true" />
              <span>{connectionStatus}</span>
            </div>

            <div
              className={`${styles.serviceStatus} ${requestStatusClass}`}
              aria-label={`Emergency status: ${formatStatus(request.request_status)}`}
            >
              <div className={styles.serviceStatusCopy}>
                <span className={styles.serviceStatusLabel}>
                  Emergency status
                </span>
                <strong>{formatStatus(request.request_status)}</strong>
              </div>
              <span className={styles.statusDot} aria-hidden="true" />
            </div>
          </div>
        </header>

        {/* REQUEST INFORMATION */}
        <dl className={styles.requestMeta}>
          <div className={styles.metaItem}>
            <dt className={styles.metaLabel}>Request</dt>
            <dd className={styles.metaValue}>#{request.request_id}</dd>
          </div>

          <div className={styles.metaItem}>
            <dt className={styles.metaLabel}>Emergency</dt>
            <dd className={styles.metaValue}>#{request.emergency_id}</dd>
          </div>

          <div className={styles.metaItem}>
            <dt className={styles.metaLabel}>Provider</dt>
            <dd className={styles.metaValue}>#{request.provider_id}</dd>
          </div>
        </dl>

        {/* PROVIDER INFORMATION AND LIVE TELEMETRY */}
        <div className={styles.trackingMainGrid}>
          <section
            className={styles.providerSection}
            aria-labelledby="provider-location-heading"
          >
            <div className={styles.sectionHeader}>
              <div>
                <span className={styles.sectionEyebrow}>Live GPS</span>
                <h2
                  className={styles.sectionTitle}
                  id="provider-location-heading"
                >
                  Provider location
                </h2>
                <p className={styles.sectionDescription}>
                  Live movement and arrival details from your assigned provider.
                </p>
              </div>

              {lastUpdated && (
                <span className={styles.updatedStamp}>
                  Updated {lastUpdated}
                </span>
              )}
            </div>

            <div className={styles.providerSummary}>
              <div className={styles.providerIdentity}>
                <span className={styles.providerMark} aria-hidden="true" />
                <div className={styles.providerIdentityCopy}>
                  <span>Assigned service provider</span>
                  <strong>Provider #{request.provider_id}</strong>
                </div>
              </div>

              <div
                className={`${styles.serviceStatus} ${requestStatusClass}`}
                aria-label={`Provider service status: ${formatStatus(request.request_status)}`}
              >
                <div className={styles.serviceStatusCopy}>
                  <span className={styles.serviceStatusLabel}>
                    Service status
                  </span>
                  <strong>{formatStatus(request.request_status)}</strong>
                </div>
                <span className={styles.statusDot} aria-hidden="true" />
              </div>
            </div>

            {providerLocation ? (
              <>
                <div className={styles.telemetryHeading}>
                  <div>
                    <span className={styles.sectionEyebrow}>
                      Arrival details
                    </span>
                    <h3>Live estimates</h3>
                  </div>
                </div>

                <div className={styles.telemetryGrid}>
                  <article
                    className={`${styles.telemetryCard} ${styles.telemetryCardFeatured}`}
                  >
                    <span className={styles.telemetryLabel}>Distance</span>
                    <strong className={styles.telemetryValue}>
                      {formatDistance(tracking?.distance_meters)}
                    </strong>
                  </article>

                  <article
                    className={`${styles.telemetryCard} ${styles.telemetryCardFeatured}`}
                  >
                    <span className={styles.telemetryLabel}>ETA</span>
                    <strong className={styles.telemetryValue}>
                      {formatEta(tracking?.eta)}
                    </strong>
                  </article>

                  <article
                    className={`${styles.telemetryCard} ${styles.telemetryCardFeatured}`}
                  >
                    <span className={styles.telemetryLabel}>Drive time</span>
                    <strong className={styles.telemetryValue}>
                      {formatDuration(tracking?.duration)}
                    </strong>
                  </article>
                </div>

                {/* AI ETA */}
                {tracking?.ai_eta ? (
                  <>
                    <div className={styles.telemetryHeading}>
                      <div>
                        <span className={styles.sectionEyebrow}>
                          ResQDrive AI
                        </span>
                        <h3>AI arrival prediction</h3>
                      </div>
                    </div>

                    <div className={styles.telemetryGrid}>
                      <article
                        className={`${styles.telemetryCard} ${styles.telemetryCardFeatured}`}
                      >
                        <span className={styles.telemetryLabel}>
                          <Icon name="bot" size={15} /> AI ETA
                        </span>
                        <strong className={styles.telemetryValue}>
                          {formatEta(tracking.ai_eta)}
                        </strong>
                      </article>

                      <article
                        className={`${styles.telemetryCard} ${styles.telemetryCardFeatured}`}
                      >
                        <span className={styles.telemetryLabel}>
                          AI Confidence
                        </span>
                        <strong className={styles.telemetryValue}>
                          {formatAiConfidence(
                            tracking.ai_eta_confidence,
                          )}
                        </strong>
                      </article>

                      <article
                        className={`${styles.telemetryCard} ${styles.telemetryCardFeatured}`}
                      >
                        <span className={styles.telemetryLabel}>
                          AI Drive time
                        </span>
                        <strong className={styles.telemetryValue}>
                          {formatDuration(
                            tracking.ai_predicted_duration,
                          )}
                        </strong>
                      </article>
                    </div>
                  </>
                ) : null}

                <div className={styles.coordinateDetails}>
                  <div className={styles.coordinateDetailsHeader}>
                    <span className={styles.coordinateDetailsTitle}>
                      Provider coordinates
                    </span>
                    <span className={styles.coordinateDetailsHint}>
                      Live GPS position
                    </span>
                  </div>

                  <div className={styles.coordinateRow}>
                    <div className={styles.coordinateItem}>
                      <span className={styles.coordinateLabel}>Latitude</span>
                      <strong className={styles.coordinateValue}>
                        {providerLocation.latitude.toFixed(6)}
                      </strong>
                    </div>

                    <div className={styles.coordinateItem}>
                      <span className={styles.coordinateLabel}>Longitude</span>
                      <strong className={styles.coordinateValue}>
                        {providerLocation.longitude.toFixed(6)}
                      </strong>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div
                className={styles.gpsEmptyState}
                role="status"
                aria-live="polite"
              >
                <span className={styles.inlineStatusMark} aria-hidden="true" />
                <div>
                  <h3>Waiting for GPS location</h3>
                  <p>
                    The provider has started the service, but their first live
                    GPS location has not arrived yet.
                  </p>
                </div>
              </div>
            )}
          </section>

          {/* LIVE MAP */}
          <section
            className={styles.mapSection}
            aria-labelledby="provider-route-heading"
          >
            <div className={styles.mapHeader}>
              <div>
                <span className={styles.sectionEyebrow}>Route overview</span>
                <h2 className={styles.sectionTitle} id="provider-route-heading">
                  Provider route
                </h2>
                <p className={styles.sectionDescription}>
                  The map updates as your provider moves toward you.
                </p>
              </div>

              <div className={styles.mapLegend} aria-label="Map markers">
                <span className={styles.legendItem}>
                  <span
                    className={`${styles.legendDot} ${styles.legendProvider}`}
                    aria-hidden="true"
                  />
                  Provider
                </span>
                <span className={styles.legendItem}>
                  <span
                    className={`${styles.legendDot} ${styles.legendCustomer}`}
                    aria-hidden="true"
                  />
                  Customer
                </span>
              </div>
            </div>

            <div
              ref={mapElementRef}
              role="region"
              aria-label="Live provider route map"
              className={styles.mapCanvas}
            />
          </section>
        </div>

        {/* FOOTER ACTIONS */}
        <div className={styles.trackingActions}>
          <button
            type="button"
            className={styles.secondaryAction}
            onClick={() => navigate("/service-requests")}
          >
            ← Service requests
          </button>

          <button
            type="button"
            className={styles.primaryAction}
            onClick={() => window.location.reload()}
          >
            Refresh live tracking
          </button>
        </div>
      </div>
    </main>
  );
}
