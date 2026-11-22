/**
 * API Response Types (mirror backend schemas)
 */

export interface PaginationParams {
  page: number;
  per_page: number;
  sort_by?: string;
  sort_order: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  per_page: number;
  data: T[];
}

export interface AgentBase {
  agent_id: string;
  agent_role: string;
  runtime: string;
}

export interface AgentStatus {
  status: 'IDLE' | 'WORKING' | 'ANALYZING' | 'TESTING' | 'REVIEWING' | 'BLOCKED' | 'COMPLETED' | 'ERROR';
  connectivity_status: 'ONLINE' | 'OFFLINE' | 'STALE' | 'UNKNOWN';
  last_event_at?: string;
  last_execution_at?: string;
  last_error?: string;
}

export interface AgentMetrics {
  metrics_summary?: Record<string, unknown>;
  current_mission_id?: string;
  current_task_id?: string;
}

export interface AgentResponse extends AgentBase, AgentStatus, AgentMetrics {
  updated_at: string;
}

export interface AgentListResponse {
  total: number;
  agents: AgentResponse[];
}

export interface MissionBase {
  mission_id: string;
  name: string;
  project_id: string;
  tenant_id: string;
}

export interface MissionStatus {
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'BLOCKED';
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface MissionProgress {
  progress_summary?: Record<string, unknown>;
  result_summary?: Record<string, unknown>;
}

export interface MissionResponse extends MissionBase, MissionStatus, MissionProgress {}

export interface MissionListResponse {
  total: number;
  missions: MissionResponse[];
}

export interface ExecutionBase {
  execution_id: string;
  mission_id: string;
  task_id?: string;
  agent_id: string;
  runtime: string;
}

export interface ExecutionTimeline {
  status: 'QUEUED' | 'RESERVED' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  queued_at?: string;
  reserved_at?: string;
  started_at?: string;
  completed_at?: string;
  validated_at?: string;
  recorded_at?: string;
}

export interface ExecutionDurations {
  queue_time_ms?: number;
  init_time_ms?: number;
  execution_time_ms?: number;
  validation_time_ms?: number;
  total_duration_ms?: number;
}

export interface ExecutionResults {
  result?: Record<string, unknown>;
  error?: string;
}

export interface ExecutionResponse extends ExecutionBase, ExecutionTimeline, ExecutionDurations, ExecutionResults {}

export interface ExecutionListResponse {
  total: number;
  executions: ExecutionResponse[];
}

export interface WebSocketTicketResponse {
  ticket: string;
  url: string;
  expires_at: string;
}

export interface ErrorResponse {
  detail: string;
  status_code: number;
  error_type?: string;
}
