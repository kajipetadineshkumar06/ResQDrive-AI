import { useNavigate } from "react-router-dom";
import { useState } from "react";

const AddVehicle = () => {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    vehicleNumber: "",
    brand: "",
    model: "",
    year: "",
    fuelType: "",
    vehicleType: "",
    vehicleColor: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (
    event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      const token = localStorage.getItem("access_token");

      if (!token) {
        setError("You are not logged in. Please login again.");
        return;
      }

      if (!formData.year) {
        setError("Please enter the manufacturing year.");
        return;
      }

      const vehicleData = {
        plate_number: formData.vehicleNumber.trim().toUpperCase(),

        make: formData.brand.trim(),

        model: formData.model.trim(),

        year: Number(formData.year),

        vehicle_type: formData.vehicleType,

        fuel_type: formData.fuelType,

        vehicle_color: formData.vehicleColor.trim(),
      };

      const response = await fetch("http://localhost:8000/vehicles/", {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },

        body: JSON.stringify(vehicleData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || "Failed to save vehicle.");
      }

      console.log("Vehicle created:", data);

      navigate("/vehicles");
    } catch (error) {
      console.error("Vehicle creation error:", error);

      if (error instanceof Error) {
        setError(error.message);
      } else {
        setError("Unable to save vehicle.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      {/* =========================================
          PAGE HEADER
      ========================================= */}

      <div className="page-header">
        <div>
          <span className="page-eyebrow">VEHICLE MANAGEMENT</span>

          <h1>Add Vehicle</h1>

          <p>Register your vehicle for faster roadside assistance.</p>
        </div>
      </div>

      {/* =========================================
          FORM CARD
      ========================================= */}

      <div className="vehicle-form-card">
        <form onSubmit={handleSubmit}>
          {/* Vehicle Number */}

          <div className="form-group">
            <label htmlFor="vehicleNumber">Vehicle Number</label>

            <input
              id="vehicleNumber"
              name="vehicleNumber"
              type="text"
              placeholder="Example: TS09AB1234"
              value={formData.vehicleNumber}
              onChange={handleChange}
              required
            />
          </div>

          {/* Brand + Model */}

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="brand">Brand</label>

              <input
                id="brand"
                name="brand"
                type="text"
                placeholder="Example: Hyundai"
                value={formData.brand}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="model">Model</label>

              <input
                id="model"
                name="model"
                type="text"
                placeholder="Example: Creta"
                value={formData.model}
                onChange={handleChange}
                required
              />
            </div>
          </div>

          {/* Year + Fuel */}

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="year">Manufacturing Year</label>

              <input
                id="year"
                name="year"
                type="number"
                min="1900"
                max={new Date().getFullYear()}
                placeholder="Example: 2024"
                value={formData.year}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="fuelType">Fuel Type</label>

              <select
                id="fuelType"
                name="fuelType"
                value={formData.fuelType}
                onChange={handleChange}
                required
              >
                <option value="">Select fuel type</option>

                <option value="petrol">Petrol</option>

                <option value="diesel">Diesel</option>

                <option value="electric">Electric</option>

                <option value="hybrid">Hybrid</option>

                <option value="cng">CNG</option>
              </select>
            </div>
          </div>

          {/* Vehicle Type */}

          <div className="form-group">
            <label htmlFor="vehicleType">Vehicle Type</label>

            <select
              id="vehicleType"
              name="vehicleType"
              value={formData.vehicleType}
              onChange={handleChange}
              required
            >
              <option value="">Select vehicle type</option>

              <option value="car">Car</option>

              <option value="bike">Bike</option>

              <option value="suv">SUV</option>

              <option value="truck">Truck</option>

              <option value="other">Other</option>
            </select>
          </div>

          {/* Vehicle Color */}

          <div className="form-group">
            <label htmlFor="vehicleColor">Vehicle Color</label>

            <input
              id="vehicleColor"
              name="vehicleColor"
              type="text"
              placeholder="Example: White"
              value={formData.vehicleColor}
              onChange={handleChange}
            />
          </div>

          {/* Error */}

          {error && <div className="login-error">{error}</div>}

          {/* Actions */}

          <div className="form-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={() => navigate("/vehicles")}
              disabled={loading}
            >
              Cancel
            </button>

            <button type="submit" className="primary-button" disabled={loading}>
              {loading ? "Saving..." : "Save Vehicle"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddVehicle;
