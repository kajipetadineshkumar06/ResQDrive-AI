import api from "./axios";

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  user_id: number;
  full_name: string;
  email: string;
  phone: string;
}

// Login
export const loginUser = async (
  email: string,
  password: string,
): Promise<LoginResponse> => {
  const formData = new URLSearchParams();

  formData.append("username", email);
  formData.append("password", password);

  const response = await api.post<LoginResponse>("/auth/login", formData, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });

  return response.data;
};

// Get currently logged-in user
export const getCurrentUser = async (): Promise<UserProfile> => {
  const response = await api.get<UserProfile>("/auth/me");

  return response.data;
};

// Logout
export const logoutUser = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
};
