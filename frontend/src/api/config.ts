const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();

if (import.meta.env.PROD) {
  if (!configuredApiUrl || /replace[_-]/i.test(configuredApiUrl)) {
    throw new Error("VITE_API_URL must be set to the deployed backend URL.");
  }

  let parsedApiUrl: URL;
  try {
    parsedApiUrl = new URL(configuredApiUrl);
  } catch {
    throw new Error("VITE_API_URL must be an absolute HTTPS URL in production.");
  }

  if (parsedApiUrl.protocol !== "https:" || parsedApiUrl.username || parsedApiUrl.password) {
    throw new Error("VITE_API_URL must be an absolute HTTPS URL in production.");
  }
}

export const API_BASE_URL = (
  configuredApiUrl || "http://127.0.0.1:8000"
).replace(/\/+$/, "");