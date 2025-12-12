const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  status: number;
}

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const token = localStorage.getItem('echo_token');

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      localStorage.removeItem('echo_token');
      localStorage.removeItem('echo_user');
      window.location.href = '/login';
      throw new ApiError(401, 'Unauthorized');
    }

    if (response.status === 204) {
      return { data: null as T, error: null, status: 204 };
    }

    let data: T | null = null;
    try {
      data = await response.json();
    } catch {
      if (!response.ok) {
        throw new ApiError(response.status, 'Invalid response format');
      }
    }

    if (!response.ok) {
      const errorMsg = (data as any)?.detail || (data as any)?.message || 'Request failed';
      return { data: null, error: errorMsg, status: response.status };
    }

    return { data, error: null, status: response.status };
  } catch (err) {
    if (err instanceof ApiError) {
      return { data: null, error: err.message, status: err.status };
    }
    return { data: null, error: 'Network error', status: 0 };
  }
}

export const api = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),

  post: <T>(path: string, body?: any) =>
    request<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),

  patch: <T>(path: string, body?: any) =>
    request<T>(path, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};

export type { ApiResponse };
