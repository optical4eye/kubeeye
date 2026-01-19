// Основные интерфейсы для frontend

// Импорты из подпапок
export * from './cluster';
export * from './secret';

// Типы для отчетов и инспекций
export interface Report {
  result_id: string;
  cluster_name: string;
  inspection_type: string;
  timestamp: string;
  total_items?: number;
  passed_count?: number;
  critical_count?: number;
  warning_count?: number;
  info_count?: number;
  // Legacy fields for table display
  critical?: number;
  warning?: number;
  info?: number;
  passed?: number;
  status?: string;
  result_data: any; // Полные данные отчета - могут быть сложными
  execution_duration?: number;
  triggered_by: 'user' | 'scheduler';
  inspectors_used?: string[];
}

export interface InspectionResultData {
  cluster_name: string;
  inspection_type: string;
  timestamp: string;
  result_id: string;
  inspection_results?: Record<string, InspectorResult>;
  items?: InspectionItem[];
}

export interface InspectorResult {
  items: InspectionItem[];
  summary?: Record<string, any>;
}

export interface InspectionItem {
  name: string;
  status: 'passed' | 'failed' | 'warning' | 'error' | 'info';
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  description?: string;
  details?: string;
  solution?: string;
  category?: string;
  tags?: string[];
}

// Типы для задач
export interface Task {
  task_id: string;
  name: string;
  description?: string;
  cluster: string; // Legacy field name used in frontend
  cluster_name?: string;
  task_type: 'cron' | 'once' | 'hourly' | 'daily' | 'weekly' | 'monthly';
  cron_expr?: string;
  run_datetime?: string;
  rules?: Record<string, string[]>;
  tags?: Record<string, string[]>;
  enabled: boolean;
  last_run?: string;
  last_status?: 'success' | 'failed' | 'running';
  next_run?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ScheduledTaskCreateRequest {
  name: string;
  description?: string;
  cluster: string;
  cron_expr?: string;
  rules?: Record<string, string[]>;
  tags?: Record<string, string[]>;
  enabled: boolean;
  task_type?: string;
  run_datetime?: string;
}

// Типы для правил
export interface Rule {
  id: string;
  name: string;
  description?: string;
  category: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  enabled: boolean;
  config?: Record<string, any>;
  tags?: string[];
}

export interface RuleUpdateRequest {
  enabled?: boolean;
  config?: Record<string, any>;
}

// Типы для сетевых проверок
export interface NetworkCheck {
  id?: string;
  source_node: string;
  target_node: string;
  port: number;
  protocol: 'tcp' | 'udp';
  status: 'success' | 'failed' | 'timeout';
  response_time?: number;
  error_message?: string;
  timestamp: string;
}

// API Response types
export interface ApiResponse<T> {
  data?: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  limit: number;
  offset: number;
}

// Form types
export interface InspectionFormData {
  cluster_name: string;
  selected_rules?: Record<string, string[]>;
  selected_tags?: Record<string, string[]>;
  inspection_type: 'immediate' | 'scheduled';
}

export interface TaskFormData {
  name: string;
  description?: string;
  cluster: string;
  cron_expr?: string;
  rules?: Record<string, string[]>;
  tags?: Record<string, string[]>;
  enabled: boolean;
  task_type?: string;
  run_datetime?: string;
}
