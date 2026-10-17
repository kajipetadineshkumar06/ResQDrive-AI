import { FormEvent, useEffect, useState } from "react";

import { useLocation, useNavigate } from "react-router-dom";

import { createEmergency } from "../api/emergencies";

import { getVehicles, type Vehicle } from "../api/vehicles";
import Icon from "../components/ui/Icon";

/* ======================================================
   CREATE EMERGENCY
====================================================== */

const CreateEmergency = () => {
  const navigate = useNavigate();
  const location = useLocation();

  type AIEmergencyState = {
    aiDiagnosis?: string;
    aiPriority?: string;
    aiService?: string;
    aiAdvice?: string;
    aiCauses?: string[];
  };

  const aiState = (location.state as AIEmergencyState | null) ?? null;

  /* ====================================================
     VEHICLES
  ==================================================== */

  const [vehicles, setVehicles] = useState<Vehicle[]>([]);

  const [vehiclesLoading, setVehiclesLoading] = useState(true);

  /* ====================================================
     FORM
  ==================================================== */

  const [vehicleId, setVehicleId] = useState("");

  const [emergencyType, setEmergencyType] = useState(
    aiState?.aiDiagnosis?.toLowerCase().includes("overheat")
      ? "Overheating"
      : aiState?.aiDiagnosis?.toLowerCase().includes("flat")
        ? "Flat Tyre"
        : aiState?.aiDiagnosis?.toLowerCase().includes("battery") ||
            aiState?.aiDiagnosis?.toLowerCase().includes("start")
          ? "Battery"
          : aiState?.aiDiagnosis
            ? "Breakdown"
            : "",
  );

  const [description, setDescription] = useState(
    aiState?.aiDiagnosis
      ? `${aiState.aiDiagnosis}${aiState.aiAdvice ? `\n\nSafety advice: ${aiState.aiAdvice}` : ""}`
      : "",
  );

  const [priority, setPriority] = useState(
    aiState?.aiPriority?.trim().toLowerCase() === "critical"
      ? "critical"
      : aiState?.aiPriority?.trim().toLowerCase() === "high"
        ? "high"
        : aiState?.aiPriority?.trim().toLowerCase() === "medium"
          ? "medium"
          : "low",
  );

  const [latitude, setLatitude] = useState("");

  const [longitude, setLongitude] = useState("");

  /* ====================================================
     UI STATE
  ==================================================== */

  const [locationLoading, setLocationLoading] = useState(false);

  const [submitting, setSubmitting] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [success, setSuccess] = useState<string | null>(null);

  /* ====================================================
     LOAD VEHICLES
  ==================================================== */

  useEffect(() => {
    const loadVehicles = async () => {
      try {
        setVehiclesLoading(true);

        setError(null);

        const data = await getVehicles();

        console.log("Emergency page vehicles:", data);

        setVehicles(data);

        /*
         * Automatically select the first
         * vehicle if available.
         */

        if (data.length > 0) {
          setVehicleId(String(data[0].vehicle_id));
        }
      } catch (err: unknown) {
        console.error("Emergency vehicle error:", err);

        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to load vehicles.");
        }
      } finally {
        setVehiclesLoading(false);
      }
    };

    loadVehicles();
  }, []);

  /* ====================================================
     GET CURRENT LOCATION
  ==================================================== */

  const getCurrentLocation = () => {
    setError(null);

    setSuccess(null);

    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser.");

      return;
    }

    setLocationLoading(true);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;

        const lng = position.coords.longitude;

        setLatitude(String(lat));

        setLongitude(String(lng));

        setLocationLoading(false);

        setSuccess("Current location detected successfully.");
      },

      (locationError) => {
        console.error("Location error:", locationError);

        let message = "Unable to get your current location.";

        if (locationError.code === locationError.PERMISSION_DENIED) {
          message =
            "Location permission was denied. Please allow location access in your browser.";
        } else if (locationError.code === locationError.POSITION_UNAVAILABLE) {
          message = "Your current location is unavailable.";
        } else if (locationError.code === locationError.TIMEOUT) {
          message = "Location request timed out. Please try again.";
        }

        setError(message);

        setLocationLoading(false);
      },

      {
        enableHighAccuracy: true,

        timeout: 15000,

        maximumAge: 0,
      },
    );
  };

  /* ====================================================
     SUBMIT EMERGENCY
  ==================================================== */

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setError(null);

    setSuccess(null);

    /* -----------------------------------------------
       Validate vehicle
    ----------------------------------------------- */

    if (!vehicleId) {
      setError("Please select a vehicle.");

      return;
    }

    /* -----------------------------------------------
       Validate emergency type
    ----------------------------------------------- */

    if (!emergencyType.trim()) {
      setError("Please select an emergency type.");

      return;
    }

    /* -----------------------------------------------
       Validate location
    ----------------------------------------------- */

    if (!latitude || !longitude) {
      setError(
        "Please get your current location before submitting the emergency.",
      );

      return;
    }

    const parsedVehicleId = Number(vehicleId);

    const parsedLatitude = Number(latitude);

    const parsedLongitude = Number(longitude);

    if (!Number.isInteger(parsedVehicleId)) {
      setError("Invalid vehicle selected.");

      return;
    }

    if (!Number.isFinite(parsedLatitude) || !Number.isFinite(parsedLongitude)) {
      setError("Invalid location coordinates.");

      return;
    }

    try {
      setSubmitting(true);

      const result = await createEmergency({
        vehicle_id: parsedVehicleId,

        emergency_type: emergencyType.trim(),

        description: description.trim() || null,

        location_lat: parsedLatitude,

        location_lng: parsedLongitude,

        priority,
      });

      console.log("Emergency created:", result);

      setSuccess(`Emergency #${result.emergency_id} created successfully.`);

      /*
       * Give the user a moment to see
       * the successful result.
       */

      setTimeout(() => {
        navigate("/service-requests");
      }, 1500);
    } catch (err: unknown) {
      console.error("Emergency creation error:", err);

      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to create emergency.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  /* ====================================================
     PAGE
  ==================================================== */

  return (
    <div className="page-container">
      {/* ================================================
          HEADER
      ================================================ */}

      <div className="page-header">
        <div>
          <span className="page-eyebrow">EMERGENCY SUPPORT</span>

          <h1>Request Emergency Help</h1>

          <p>
            Tell us about your roadside emergency so we can understand what
            assistance you need.
          </p>
        </div>

        <button
          type="button"
          className="secondary-button"
          onClick={() => navigate("/dashboard")}
        >
          Back to Dashboard
        </button>
      </div>

      {/* ================================================
          AI CONTEXT
      ================================================ */}

      {aiState?.aiDiagnosis && (
        <div
          style={{
            marginBottom: "18px",
            padding: "16px 18px",
            borderRadius: "12px",
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            color: "#1e3a8a",
          }}
        >
          <strong><Icon name="bot" size={17} /> AI-assisted emergency</strong>
          <div style={{ marginTop: "6px", lineHeight: 1.5 }}>
            <strong>Problem:</strong> {aiState.aiDiagnosis}
            {aiState.aiService && (
              <span> · <strong>Service:</strong> {aiState.aiService}</span>
            )}
            {aiState.aiPriority && (
              <span> · <strong>AI Priority:</strong> {aiState.aiPriority}</span>
            )}
          </div>
        </div>
      )}

      {/* ================================================
          FORM
      ================================================ */}

      <div className="vehicle-form-card">
        <form onSubmit={handleSubmit}>
          {/* ==========================================
              VEHICLE
          ========================================== */}

          <div className="form-group">
            <label htmlFor="vehicle">Select Vehicle</label>

            {vehiclesLoading ? (
              <div
                style={{
                  padding: "13px 14px",
                  border: "1px solid #cbd5e1",
                  borderRadius: "10px",
                  color: "#64748b",
                  background: "#f8fafc",
                }}
              >
                Loading your vehicles...
              </div>
            ) : vehicles.length === 0 ? (
              <div
                style={{
                  padding: "16px",
                  border: "1px solid #fecaca",
                  borderRadius: "10px",
                  background: "#fef2f2",
                  color: "#b91c1c",
                }}
              >
                <strong>No vehicles found.</strong>

                <p
                  style={{
                    margin: "6px 0 12px",
                  }}
                >
                  Please register a vehicle before requesting emergency
                  assistance.
                </p>

                <button
                  type="button"
                  className="primary-button"
                  onClick={() => navigate("/vehicles/add")}
                >
                  Add Vehicle
                </button>
              </div>
            ) : (
              <select
                id="vehicle"
                value={vehicleId}
                onChange={(event) => setVehicleId(event.target.value)}
                required
              >
                <option value="">Select your vehicle</option>

                {vehicles.map((vehicle) => (
                  <option key={vehicle.vehicle_id} value={vehicle.vehicle_id}>
                    {vehicle.plate_number} - {vehicle.make} {vehicle.model} (
                    {vehicle.year})
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* ==========================================
              EMERGENCY TYPE
          ========================================== */}

          <div className="form-group">
            <label htmlFor="emergency-type">Emergency Type</label>

            <select
              id="emergency-type"
              value={emergencyType}
              onChange={(event) => setEmergencyType(event.target.value)}
              required
            >
              <option value="">Select emergency type</option>

              <option value="Breakdown">Vehicle Breakdown</option>

              <option value="Flat Tyre">Flat Tyre</option>

              <option value="Battery">Battery Problem</option>

              <option value="Fuel">Fuel Problem</option>

              <option value="Engine">Engine Problem</option>

              <option value="Accident">Accident</option>

              <option value="Overheating">Engine Overheating</option>

              <option value="Lockout">Vehicle Lockout</option>

              <option value="Other">Other</option>
            </select>
          </div>

          {/* ==========================================
              DESCRIPTION
          ========================================== */}

          <div className="form-group">
            <label htmlFor="description">Describe the Problem</label>

            <textarea
              id="description"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Describe what happened and what assistance you need..."
              rows={5}
              style={{
                width: "100%",
                padding: "13px 14px",
                border: "1px solid #cbd5e1",
                borderRadius: "10px",
                background: "white",
                color: "#0f172a",
                outline: "none",
                resize: "vertical",
                font: "inherit",
              }}
            />
          </div>

          {/* ==========================================
              PRIORITY
          ========================================== */}

          <div className="form-group">
            <label htmlFor="priority">Priority</label>

            <select
              id="priority"
              value={priority}
              onChange={(event) => setPriority(event.target.value)}
            >
              <option value="critical">Critical</option>

              <option value="high">High</option>

              <option value="medium">Medium</option>

              <option value="low">Low</option>
            </select>
          </div>

          {/* ==========================================
              LOCATION
          ========================================== */}

          <div className="form-group">
            <label>Current Location</label>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "12px",
              }}
            >
              <input
                type="text"
                value={latitude}
                placeholder="Latitude"
                readOnly
              />

              <input
                type="text"
                value={longitude}
                placeholder="Longitude"
                readOnly
              />
            </div>

            <button
              type="button"
              className="secondary-button"
              onClick={getCurrentLocation}
              disabled={locationLoading}
              style={{
                marginTop: "10px",
              }}
            >
              {locationLoading
                ? "Getting Location..."
                : <><Icon name="mapPin" size={17} /> Get Current Location</>}
            </button>

            <small
              style={{
                color: "#64748b",
                lineHeight: 1.5,
              }}
            >
              Your browser will ask for permission to access your current
              location.
            </small>
          </div>

          {/* ==========================================
              ERROR
          ========================================== */}

          {error && (
            <div
              style={{
                padding: "13px 15px",
                border: "1px solid #fecaca",
                borderRadius: "10px",
                background: "#fef2f2",
                color: "#b91c1c",
                fontSize: "14px",
                lineHeight: 1.5,
              }}
            >
              {error}
            </div>
          )}

          {/* ==========================================
              SUCCESS
          ========================================== */}

          {success && (
            <div
              style={{
                padding: "13px 15px",
                border: "1px solid #bbf7d0",
                borderRadius: "10px",
                background: "#f0fdf4",
                color: "#166534",
                fontSize: "14px",
                lineHeight: 1.5,
              }}
            >
              {success}
            </div>
          )}

          {/* ==========================================
              ACTIONS
          ========================================== */}

          <div className="form-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={() => navigate("/dashboard")}
              disabled={submitting}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="primary-button"
              disabled={submitting || vehiclesLoading || vehicles.length === 0}
            >
              {submitting ? "Creating Emergency..." : "Create Emergency"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateEmergency;
