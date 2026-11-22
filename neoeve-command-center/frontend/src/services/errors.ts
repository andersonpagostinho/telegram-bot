/**
 * API Error Normalization
 */

export interface ApiErrorDetail {
  status: number;
  statusText: string;
  data?: {
    detail?: string;
    error_type?: string;
  };
}

export interface NormalizedError {
  code: string;
  status: number;
  message: string;
  isRetryable: boolean;
}

export function normalizeApiError(error: ApiErrorDetail): NormalizedError {
  const { status, data } = error;
  const detail = data?.detail || 'Unknown error';
  const errorType = data?.error_type;

  // Use provided error_type if available, otherwise map HTTP status to code
  let code: string;
  let isRetryable = false;

  if (errorType) {
    code = errorType;
  } else {
    switch (status) {
      case 400:
        code = 'BAD_REQUEST';
        break;
      case 401:
        code = 'UNAUTHORIZED';
        break;
      case 403:
        code = 'FORBIDDEN';
        break;
      case 404:
        code = 'NOT_FOUND';
        break;
      case 408:
        code = 'REQUEST_TIMEOUT';
        isRetryable = true;
        break;
      case 429:
        code = 'RATE_LIMITED';
        isRetryable = true;
        break;
      case 500:
        code = 'SERVER_ERROR';
        isRetryable = true;
        break;
      case 502:
        code = 'BAD_GATEWAY';
        isRetryable = true;
        break;
      case 503:
        code = 'SERVICE_UNAVAILABLE';
        isRetryable = true;
        break;
      default:
        code = 'UNKNOWN_ERROR';
        isRetryable = false;
    }
  }

  return {
    code,
    status,
    message: detail,
    isRetryable,
  };
}

export function isAuthError(error: NormalizedError): boolean {
  return error.code === 'UNAUTHORIZED' || error.code === 'FORBIDDEN';
}

export function isRetryableError(error: NormalizedError): boolean {
  return error.isRetryable;
}
