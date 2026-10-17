import axios from "axios";
import { API_BASE_URL } from "./config";

const API_URL = API_BASE_URL;

// ======================================================
// GET AUTH TOKEN
// ======================================================

const getAuthToken = (): string | null => {
  const possibleKeys = [
    "access_token",
    "token",
    "accessToken",
    "authToken",
    "jwt",
    "userToken",
  ];

  // ====================================================
  // LOCAL STORAGE
  // ====================================================

  for (const key of possibleKeys) {
    const value = localStorage.getItem(key);

    if (value && value.trim()) {
      return value.trim();
    }
  }

  // ====================================================
  // USER OBJECT IN LOCAL STORAGE
  // ====================================================

  const userData = localStorage.getItem("user");

  if (userData) {
    try {
      const user = JSON.parse(userData);

      const token =
        user?.token || user?.access_token || user?.accessToken || user?.jwt;

      if (token && typeof token === "string") {
        return token.trim();
      }
    } catch (error) {
      console.warn("Unable to parse stored user data.", error);
    }
  }

  // ====================================================
  // SESSION STORAGE
  // ====================================================

  for (const key of possibleKeys) {
    const value = sessionStorage.getItem(key);

    if (value && value.trim()) {
      return value.trim();
    }
  }

  // ====================================================
  // USER OBJECT IN SESSION STORAGE
  // ====================================================

  const sessionUserData = sessionStorage.getItem("user");

  if (sessionUserData) {
    try {
      const user = JSON.parse(sessionUserData);

      const token =
        user?.token || user?.access_token || user?.accessToken || user?.jwt;

      if (token && typeof token === "string") {
        return token.trim();
      }
    } catch (error) {
      console.warn("Unable to parse session user data.", error);
    }
  }

  return null;
};

// ======================================================
// CLEAN BEARER TOKEN
// ======================================================

const cleanToken = (token: string): string => {
  const trimmedToken = token.trim();

  if (trimmedToken.toLowerCase().startsWith("bearer ")) {
    return trimmedToken.substring(7).trim();
  }

  return trimmedToken;
};

// ======================================================
// AXIOS INSTANCE
// ======================================================

const api = axios.create({
  baseURL: API_URL,

  headers: {
    "Content-Type": "application/json",
  },
});

// ======================================================
// REQUEST INTERCEPTOR
// ======================================================

api.interceptors.request.use(
  (config) => {
    const token = getAuthToken();

    if (token) {
      const cleanAuthToken = cleanToken(token);

      if (cleanAuthToken) {
        config.headers = config.headers || {};

        config.headers.Authorization = `Bearer ${cleanAuthToken}`;
      }
    }

    return config;
  },

  (error) => {
    return Promise.reject(error);
  },
);

// ======================================================
// RESPONSE INTERCEPTOR
// ======================================================

api.interceptors.response.use(
  (response) => {
    return response;
  },

  (error) => {
    // -----------------------------------------------
    // IMPORTANT
    // -----------------------------------------------
    // Do NOT automatically delete the token here.
    //
    // A 401 from one endpoint should not immediately
    // destroy the user's stored authentication state.
    // -----------------------------------------------

    if (error.response?.status === 401) {
      console.error("API authentication failed:", {
        url: error.config?.url,

        method: error.config?.method,

        status: error.response?.status,

        response: error.response?.data,
      });
    }

    return Promise.reject(error);
  },
);

export default api;
