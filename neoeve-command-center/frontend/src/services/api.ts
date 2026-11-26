/**
 * API Client Service for Command Center
 * Handles HTTP requests, JWT authentication, and error normalization
 */

import axios, { AxiosInstance, AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import {
  AgentListResponse,
  MissionListResponse,
  ExecutionListResponse,
  WebSocketTicketResponse,
  PaginationParams,
} from '../types/api';
import { normalizeApiError, NormalizedError } from './errors';
import { useAuthStore } from '../store/auth';

// Shared refresh promise to prevent multiple simultaneous refreshes
let refreshPromise: Promise<boolean> | null = null;

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_VERSION = import.meta.env.VITE_API_VERSION || 'v1';

class ApiClient {
  private client: AxiosInstance;
  private token: string | null = null;
  private tenantId: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/${API_VERSION}`,
      timeout: 30000,
      withCredentials: true, // Allow sending cookies (HttpOnly refresh_token)
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor for auth
    this.client.interceptors.request.use((config) => {
      const authHeaders = this.getHeaders();
      Object.entries(authHeaders).forEach(([key, value]) => {
        config.headers.set(key, value);
      });
      return config;
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retried?: boolean };
        const url = originalRequest.url || '';

        // 401 Unauthorized - try to refresh token (but NOT for auth endpoints)
        if (error.response?.status === 401 && !originalRequest._retried && !url.includes('/auth/')) {
          originalRequest._retried = true;

          try {
            // Share refresh promise across concurrent requests
            if (!refreshPromise) {
              refreshPromise = attemptTokenRefresh();
            }

            const refreshSuccess = await refreshPromise;
            refreshPromise = null;

            if (refreshSuccess) {
              // Retry original request with new token
              return this.client(originalRequest);
            } else {
              // Refresh failed - logout
              throw new Error('Token refresh failed');
            }
          } catch (refreshErr) {
            // Refresh failed or error occurred
            console.error('Token refresh failed:', refreshErr);
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth_user');

            const { reset } = useAuthStore.getState();
            reset();

            // Redirect to login
            if (!window.location.pathname.includes('/login')) {
              window.location.href = '/login';
            }

            const normalized = normalizeApiError({
              status: 401,
              statusText: 'Session Expired',
              data: { detail: 'Token refresh failed' },
            });
            return Promise.reject(normalized);
          }
        }

        const normalized = normalizeApiError({
          status: error.response?.status || 500,
          statusText: error.response?.statusText || 'Unknown Error',
          data: error.response?.data as any,
        });
        return Promise.reject(normalized);
      }
    );
  }

  setToken(token: string): void {
    this.token = token;
    // Extract tenant_id from JWT (payload is base64 encoded JSON, 2nd part)
    try {
      const parts = token.split('.');
      if (parts.length >= 2) {
        const payload = JSON.parse(atob(parts[1]));
        this.tenantId = payload.tenant_id || null;
      }
    } catch (e) {
      console.error('Failed to extract tenant_id from JWT', e);
    }
  }

  clearToken(): void {
    this.token = null;
    this.tenantId = null;
  }

  getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {};

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    if (this.tenantId) {
      headers['X-Tenant-ID'] = this.tenantId;
    }

    return headers;
  }

  async getAgents(params?: Partial<PaginationParams>): Promise<AgentListResponse> {
    const queryParams = {
      page: params?.page || 1,
      per_page: params?.per_page || 20,
      sort_by: params?.sort_by || 'updated_at',
      sort_order: params?.sort_order || 'desc',
    };

    const response = await this.client.get<AgentListResponse>('/agents', {
      params: queryParams,
    });

    return response.data;
  }

  async getMissions(params?: Partial<PaginationParams> & { status?: string; days?: number }): Promise<MissionListResponse> {
    const queryParams = {
      page: params?.page || 1,
      per_page: params?.per_page || 20,
      sort_by: params?.sort_by || 'created_at',
      sort_order: params?.sort_order || 'desc',
      ...(params?.status && { status: params.status }),
      ...(params?.days && { days: params.days }),
    };

    const response = await this.client.get<MissionListResponse>('/missions', {
      params: queryParams,
    });

    return response.data;
  }

  async getExecutions(
    params?: Partial<PaginationParams> & { mission_id?: string; agent_id?: string }
  ): Promise<ExecutionListResponse> {
    const queryParams = {
      page: params?.page || 1,
      per_page: params?.per_page || 20,
      sort_by: params?.sort_by || 'created_at',
      sort_order: params?.sort_order || 'desc',
      ...(params?.mission_id && { mission_id: params.mission_id }),
      ...(params?.agent_id && { agent_id: params.agent_id }),
    };

    const response = await this.client.get<ExecutionListResponse>('/executions', {
      params: queryParams,
    });

    return response.data;
  }

  async getEvents(
    params?: Partial<PaginationParams> & {
      cursor?: number;
      agent_id?: string;
      mission_id?: string;
      event_type?: string;
    }
  ): Promise<any> {
    const queryParams = {
      limit: params?.per_page || 50,
      ...(params?.cursor !== undefined && { cursor: params.cursor }),
      ...(params?.agent_id && { agent_id: params.agent_id }),
      ...(params?.mission_id && { mission_id: params.mission_id }),
      ...(params?.event_type && { event_type: params.event_type }),
    };

    const response = await this.client.get<any>('/events', {
      params: queryParams,
    });

    return response.data;
  }

  async issueWebSocketTicket(): Promise<WebSocketTicketResponse> {
    const response = await this.client.post<WebSocketTicketResponse>('/websocket/ticket', {});
    return response.data;
  }

  async login(credentials: { email: string; password: string }): Promise<any> {
    const response = await this.client.post('/auth/login', credentials);
    return response.data;
  }

  async selectTenant(data: { selection_token: string; tenant_id: string }): Promise<any> {
    const response = await this.client.post('/auth/select-tenant', data);
    return response.data;
  }

  async logout(): Promise<any> {
    const response = await this.client.post('/auth/logout', {});
    this.clearToken();
    return response.data;
  }
}

// Standalone function to attempt token refresh
async function attemptTokenRefresh(): Promise<boolean> {
  try {
    // Create temporary client to call refresh (avoid interceptor loop)
    const tempClient = axios.create({
      baseURL: `${API_BASE_URL}/api/${API_VERSION}`,
      timeout: 30000,
      withCredentials: true, // Send refresh_token cookie
    });

    const response = await tempClient.post<{ access_token: string }>(
      '/auth/refresh',
      {}
    );

    if (!response.data?.access_token) {
      console.error('No access token in refresh response');
      return false;
    }

    // Update token in store
    apiClient.setToken(response.data.access_token);

    const authStore = useAuthStore.getState();
    const currentUser = authStore.user;

    if (currentUser) {
      // Update localStorage
      localStorage.setItem('auth_token', response.data.access_token);
      authStore.setAuth(currentUser, response.data.access_token);
    }

    console.info('Token refreshed successfully via interceptor');
    return true;
  } catch (err) {
    console.error('Token refresh failed in interceptor:', err);
    return false;
  }
}

export const apiClient = new ApiClient();
