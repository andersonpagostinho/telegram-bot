import { describe, it, expect, beforeEach, vi } from 'vitest';
import { apiClient } from '../services/api';
import { normalizeApiError } from '../services/errors';

describe('API Client', () => {
  beforeEach(() => {
    // Clear any stored token
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe('Authentication', () => {
    it('should include JWT token in Authorization header', () => {
      const token = 'test-jwt-token-123';
      apiClient.setToken(token);

      const headers = apiClient.getHeaders();
      expect(headers['Authorization']).toBe(`Bearer ${token}`);
    });

    it('should include tenant_id header from JWT', () => {
      const token = 'test-jwt-token-123';
      apiClient.setToken(token);

      const headers = apiClient.getHeaders();
      expect(headers['X-Tenant-ID']).toBeDefined();
    });

    it('should not include Authorization header when no token set', () => {
      const headers = apiClient.getHeaders();
      expect(headers['Authorization']).toBeUndefined();
    });
  });

  describe('API Methods', () => {
    it('should have getAgents method', () => {
      expect(apiClient.getAgents).toBeDefined();
      expect(typeof apiClient.getAgents).toBe('function');
    });

    it('should have getMissions method', () => {
      expect(apiClient.getMissions).toBeDefined();
      expect(typeof apiClient.getMissions).toBe('function');
    });

    it('should have getExecutions method', () => {
      expect(apiClient.getExecutions).toBeDefined();
      expect(typeof apiClient.getExecutions).toBe('function');
    });

    it('should have issueWebSocketTicket method', () => {
      expect(apiClient.issueWebSocketTicket).toBeDefined();
      expect(typeof apiClient.issueWebSocketTicket).toBe('function');
    });
  });

  describe('Error Handling', () => {
    it('should normalize 401 Unauthorized error', () => {
      const error = normalizeApiError({
        status: 401,
        statusText: 'Unauthorized',
        data: { detail: 'Invalid credentials' },
      });

      expect(error.code).toBe('UNAUTHORIZED');
      expect(error.status).toBe(401);
      expect(error.message).toContain('Invalid credentials');
    });

    it('should normalize 403 Forbidden error', () => {
      const error = normalizeApiError({
        status: 403,
        statusText: 'Forbidden',
        data: { detail: 'Access denied' },
      });

      expect(error.code).toBe('FORBIDDEN');
      expect(error.status).toBe(403);
    });

    it('should normalize 404 Not Found error', () => {
      const error = normalizeApiError({
        status: 404,
        statusText: 'Not Found',
        data: { detail: 'Resource not found' },
      });

      expect(error.code).toBe('NOT_FOUND');
      expect(error.status).toBe(404);
    });

    it('should normalize 500 Server error', () => {
      const error = normalizeApiError({
        status: 500,
        statusText: 'Internal Server Error',
        data: { detail: 'Server error' },
      });

      expect(error.code).toBe('SERVER_ERROR');
      expect(error.status).toBe(500);
    });

    it('should include original error type if provided', () => {
      const error = normalizeApiError({
        status: 400,
        statusText: 'Bad Request',
        data: { detail: 'Validation failed', error_type: 'VALIDATION_ERROR' },
      });

      expect(error.code).toBe('VALIDATION_ERROR');
    });
  });
});
