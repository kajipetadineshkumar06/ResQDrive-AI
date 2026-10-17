// ======================================================
// api/serviceRequests.ts
// ======================================================

import api from "./axios";

// ======================================================
// SERVICE REQUEST TYPE
// ======================================================

export interface ServiceRequest {
  request_id: number;

  emergency_id: number;

  provider_id: number;

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
// GET MY SERVICE REQUESTS
// ======================================================

export const getMyServiceRequests = async (): Promise<ServiceRequest[]> => {
  const response = await api.get<ServiceRequest[]>("/service-requests/");

  return Array.isArray(response.data) ? response.data : [];
};

// ======================================================
// GET SINGLE SERVICE REQUEST
// ======================================================

export const getServiceRequest = async (
  requestId: number,
): Promise<ServiceRequest> => {
  const response = await api.get<ServiceRequest>(
    `/service-requests/${requestId}`,
  );

  return response.data;
};

// ======================================================
// CANCEL SERVICE REQUEST
// ======================================================

export const cancelServiceRequest = async (requestId: number) => {
  const response = await api.delete(`/service-requests/${requestId}`);

  return response.data;
};
