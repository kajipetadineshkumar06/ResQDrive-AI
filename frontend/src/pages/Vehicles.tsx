import { useEffect, useState } from "react";

import { useNavigate } from "react-router-dom";
import Icon from "../components/ui/Icon";
import { API_BASE_URL } from "../api/config";

interface Vehicle {
  vehicle_id: number;

  user_id: number;

  plate_number: string;

  make: string | null;

  model: string | null;

  year: number | null;

  vehicle_type: string | null;

  fuel_type: string | null;

  vehicle_color: string | null;

  vehicle_image?: string | null;
}

const Vehicles = () => {
  const navigate = useNavigate();

  const [vehicles, setVehicles] = useState<Vehicle[]>([]);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  const fetchVehicles = async () => {
    try {
      setLoading(true);

      setError("");

      const token = localStorage.getItem("access_token");

      if (!token) {
        setError("You are not logged in.");

        setLoading(false);

        return;
      }

      const response = await fetch(`${API_BASE_URL}/vehicles/`, {
        method: "GET",

        headers: {
          Authorization: `Bearer ${token}`,

          "Content-Type": "application/json",
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || "Failed to load vehicles.");
      }

      let vehicleList: Vehicle[] = [];

      /*
       * Backend can return:
       *
       * 1. Array
       *
       * 2. { vehicles: [] }
       *
       * 3. { data: [] }
       */

      if (Array.isArray(data)) {
        vehicleList = data;
      } else if (Array.isArray(data?.vehicles)) {
        vehicleList = data.vehicles;
      } else if (Array.isArray(data?.data)) {
        vehicleList = data.data;
      }

      setVehicles(vehicleList);
    } catch (error) {
      console.error("Vehicle fetch error:", error);

      if (error instanceof Error) {
        setError(error.message);
      } else {
        setError("Unable to load vehicles.");
      }

      setVehicles([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVehicles();
  }, []);

  return (
    <div className="page-container">
      {/* =================================
          PAGE HEADER
      ================================= */}

      <div className="page-header">
        <div>
          <span className="page-eyebrow">VEHICLE MANAGEMENT</span>

          <h1>My Vehicles</h1>

          <p>Manage your registered vehicles and vehicle information.</p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={() => navigate("/vehicles/add")}
        >
          + Add Vehicle
        </button>
      </div>

      {/* =================================
          LOADING
      ================================= */}

      {loading && (
        <div className="empty-state">
          <div className="empty-state-icon"><Icon name="car" /></div>

          <h2>Loading vehicles...</h2>

          <p>Please wait while we load your vehicles.</p>
        </div>
      )}

      {/* =================================
          ERROR
      ================================= */}

      {!loading && error && (
        <div className="empty-state">
          <div className="empty-state-icon"><Icon name="alert" /></div>

          <h2>Unable to load vehicles</h2>

          <p>{error}</p>

          <button
            type="button"
            className="primary-button"
            onClick={fetchVehicles}
          >
            Try Again
          </button>
        </div>
      )}

      {/* =================================
          NO VEHICLES
      ================================= */}

      {!loading && !error && vehicles.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon"><Icon name="car" /></div>

          <h2>No vehicles registered</h2>

          <p>
            Add your vehicle to quickly request roadside assistance when you
            need it.
          </p>

          <button
            type="button"
            className="primary-button"
            onClick={() => navigate("/vehicles/add")}
          >
            Add Your First Vehicle
          </button>
        </div>
      )}

      {/* =================================
          VEHICLE CARDS
      ================================= */}

      {!loading && !error && vehicles.length > 0 && (
        <div className="vehicles-grid">
          {vehicles.map((vehicle) => (
            <div className="vehicle-card" key={vehicle.vehicle_id}>
              {/* CARD HEADER */}

              <div className="vehicle-card-header">
                <div className="vehicle-icon"><Icon name="car" /></div>

                <div>
                  <h2>
                    {vehicle.make || "Unknown"} {vehicle.model || "Vehicle"}
                  </h2>

                  <span className="vehicle-number">{vehicle.plate_number}</span>
                </div>
              </div>

              {/* VEHICLE DETAILS */}

              <div className="vehicle-details">
                <div className="vehicle-detail">
                  <span>Year</span>

                  <strong>{vehicle.year || "N/A"}</strong>
                </div>

                <div className="vehicle-detail">
                  <span>Type</span>

                  <strong>{vehicle.vehicle_type || "N/A"}</strong>
                </div>

                <div className="vehicle-detail">
                  <span>Fuel</span>

                  <strong>{vehicle.fuel_type || "N/A"}</strong>
                </div>

                <div className="vehicle-detail">
                  <span>Color</span>

                  <strong>{vehicle.vehicle_color || "Not specified"}</strong>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Vehicles;
