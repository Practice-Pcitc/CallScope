import axios, { AxiosError } from "axios";

export interface ApiErrorBody {
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
  requestId: string;
}

export interface ApiErrorEnvelope {
  error: ApiErrorBody;
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
  timeout: 15_000,
  headers: {
    "Content-Type": "application/json"
  }
});

export function getApiError(error: unknown): ApiErrorBody {
  if (error instanceof AxiosError) {
    const payload = error.response?.data as ApiErrorEnvelope | undefined;
    if (payload?.error) {
      return payload.error;
    }
  }
  return {
    code: "NETWORK_ERROR",
    message: "无法连接后端服务",
    requestId: ""
  };
}

