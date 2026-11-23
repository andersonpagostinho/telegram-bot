/**
 * API Client Service for Command Center
 * Handles HTTP requests, JWT authentication, and error normalization
 */

import axios, { AxiosInstance, AxiosError, AxiosResponse } from 'axios';
import {
  AgentListResponse,
  MissionListResponse,
  ExecutionListResponse,
  WebSocketTicketResponse,
  PaginationParams,
} from '../types/api';
import { normalizeApiError, NormalizedError } from './errors';

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
      (error: AxiosError) => {
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

  async issueWebSocketTicket(): Promise<WebSocketTicketResponse> {
    const response = await this.client.post<WebSocketTicketResponse>('/websocket/ticket', {});
    return response.data;
  }
}

export const apiClient = new ApiClient();
