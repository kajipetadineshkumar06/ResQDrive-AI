import { Navigate, Route, Routes } from "react-router-dom";

import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Vehicles from "./pages/Vehicles";
import AddVehicle from "./pages/AddVehicle";
import CreateEmergency from "./pages/CreateEmergency";
import ServiceRequests from "./pages/ServiceRequests";
import Notifications from "./pages/Notifications";
import ProviderDashboard from "./pages/ProviderDashboard";
import Tracking from "./pages/Tracking";
import AIDiagnosis from "./pages/AIDiagnosis";
import History from "./pages/History";

import ProtectedRoute from "./components/ProtectedRoute";

function ComingSoon({ title }: { title: string }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "#f6f8fc",
        padding: "30px",
      }}
    >
      <div
        style={{
          background: "#ffffff",
          borderRadius: "20px",
          padding: "50px",
          textAlign: "center",
          boxShadow: "0 10px 35px rgba(0,0,0,0.08)",
        }}
      >
        <h1>{title}</h1>

        <p
          style={{
            color: "#6b7280",
          }}
        >
          This feature is coming next.
        </p>
      </div>
    </div>
  );
}

function App() {
  return (
    <Routes>
      {/* =========================
          PUBLIC ROUTES
      ========================= */}

      <Route path="/login" element={<Login />} />

      <Route path="/register" element={<Register />} />

      {/* =========================
          PROTECTED ROUTES
      ========================= */}

      <Route element={<ProtectedRoute />}>
        {/* CUSTOMER */}

        <Route path="/dashboard" element={<Dashboard />} />

        <Route path="/vehicles" element={<Vehicles />} />

        <Route path="/vehicles/add" element={<AddVehicle />} />

        <Route path="/emergency" element={<CreateEmergency />} />

        <Route path="/emergency/create" element={<CreateEmergency />} />

        <Route path="/service-requests" element={<ServiceRequests />} />

        <Route
          path="/requests"
          element={<Navigate to="/service-requests" replace />}
        />

        <Route path="/notifications" element={<Notifications />} />

        {/* AI */}

        <Route path="/ai" element={<AIDiagnosis />} />
        <Route path="/ai-assistant" element={<Navigate to="/ai" replace />} />

        <Route path="/history" element={<History />} />

        {/* PROVIDER */}

        <Route path="/provider" element={<ProviderDashboard />} />

        <Route
          path="/provider/dashboard"
          element={<ProviderDashboard />}
        />

        {/* TRACKING */}

        <Route path="/tracking" element={<Tracking />} />

        {/* FUTURE */}

        <Route
          path="/settings"
          element={<ComingSoon title="Settings" />}
        />
      </Route>

      {/* =========================
          DEFAULT ROUTES
      ========================= */}

      <Route
        path="/"
        element={<Navigate to="/dashboard" replace />}
      />

      <Route
        path="*"
        element={<Navigate to="/dashboard" replace />}
      />
    </Routes>
  );
}

export default App;
