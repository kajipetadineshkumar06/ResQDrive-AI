import api from "./axios";

/* ======================================================
   EMERGENCY TYPE
====================================================== */

export interface Emergency {
  emergency_id: number;
  user_id: number;
  vehicle_id: number;

  emergency_type: string;

  description: string | null;

  location_lat: number;
  location_lng: number;

  priority: string;

  status: string;

  recommended_service: string | null;

  created_at: string;

  resolved_at: string | null;
}

/* ======================================================
   CREATE EMERGENCY REQUEST
====================================================== */

export interface EmergencyCreate {
  vehicle_id: number;

  emergency_type: string;

  description?: string | null;

  location_lat: number;

  location_lng: number;

  priority?: string;
}

/* ======================================================
   CREATE EMERGENCY
====================================================== */

export const createEmergency = async (
  emergency: EmergencyCreate,
): Promise<Emergency> => {
  try {
    const response = await api.post<Emergency>("/emergencies/", {
      vehicle_id: emergency.vehicle_id,

      emergency_type: emergency.emergency_type,

      description: emergency.description || null,

      location_lat: emergency.location_lat,

      location_lng: emergency.location_lng,

      priority: emergency.priority || "high",
    });

    console.log("POST /emergencies/ status:", response.status);

    console.log("POST /emergencies/ response:", response.data);

    return response.data;
  } catch (error: any) {
    console.error("Create emergency error:", error);

    const message =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.message ||
      "Failed to create emergency.";

    throw new Error(message);
  }
};

/* ======================================================
   GET MY EMERGENCIES
====================================================== */

export const getMyEmergencies = async (): Promise<Emergency[]> => {
  try {
    const response = await api.get<Emergency[]>("/emergencies/");

    console.log("GET /emergencies/ status:", response.status);

    console.log("GET /emergencies/ response:", response.data);

    if (!Array.isArray(response.data)) {
      throw new Error("Invalid emergency data received from server.");
    }

    return response.data;
  } catch (error: any) {
    console.error("Get emergencies error:", error);

    const message =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.message ||
      "Failed to load emergencies.";

    throw new Error(message);
  }
};

/* ======================================================
   GET SINGLE EMERGENCY
====================================================== */

export const getEmergency = async (emergencyId: number): Promise<Emergency> => {
  try {
    const response = await api.get<Emergency>(`/emergencies/${emergencyId}`);

    return response.data;
  } catch (error: any) {
    console.error("Get emergency error:", error);

    const message =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.message ||
      "Failed to load emergency.";

    throw new Error(message);
  }
};

/* ======================================================
   UPDATE EMERGENCY
====================================================== */

export const updateEmergency = async (
  emergencyId: number,
  status: string,
): Promise<Emergency> => {
  try {
    const response = await api.put<Emergency>(`/emergencies/${emergencyId}`, {
      status,
    });

    return response.data;
  } catch (error: any) {
    console.error("Update emergency error:", error);

    const message =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.message ||
      "Failed to update emergency.";

    throw new Error(message);
  }
};

/* ======================================================
   DELETE EMERGENCY
====================================================== */

export const deleteEmergency = async (emergencyId: number) => {
  try {
    const response = await api.delete(`/emergencies/${emergencyId}`);

    return response.data;
  } catch (error: any) {
    console.error("Delete emergency error:", error);

    const message =
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.message ||
      "Failed to delete emergency.";

    throw new Error(message);
  }
};
