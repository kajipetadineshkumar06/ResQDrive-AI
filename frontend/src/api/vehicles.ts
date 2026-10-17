export interface Vehicle {
  vehicle_id: number;
  user_id: number;
  plate_number: string;
  make: string;
  model: string;
  year: number;
  vehicle_type: string;
  fuel_type: string;
  vehicle_color: string;
  vehicle_image?: string | null;
}

export const getVehicles = async (): Promise<Vehicle[]> => {
  const token = localStorage.getItem("access_token");

  if (!token) {
    throw new Error("You are not logged in.");
  }

  const response = await fetch("http://localhost:8000/vehicles/", {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  const data = await response.json();

  console.log("GET /vehicles/ status:", response.status);
  console.log("GET /vehicles/ response:", data);

  if (!response.ok) {
    throw new Error(data.detail || "Failed to load vehicles.");
  }

  if (!Array.isArray(data)) {
    throw new Error("Invalid vehicle data received from server.");
  }

  return data;
};
