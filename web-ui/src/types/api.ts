// Types pour l'API GSGUI
export interface Challenge {
  id: string;
  title: string;
  end_time: string;
  time_left_display: string;
  votes: number;
  rank: number;
  level: number;
  exposure: number;
  gps: number;
  selected_strategy?: string;
  turbo_status: 'none' | 'running' | 'completed' | 'failed' | 'timer' | 'unknown' | 'pending' | 'available' | 'won' | 'used';
  boost_status?: string;
  status: 'active' | 'fill' | 'scheduled' | 'expired';
  url: string;
  // Legacy fields for compatibility
  wins?: number;
  time_left?: string;
}

export interface Profile {
  name: string;
  has_token: boolean;
  is_active?: boolean;
  id?: string; // Pour les endpoints qui utilisent profile_id
}

export interface Strategy {
  name: string;
  description: string;
  schedule: string;
}

export interface ApiResponse<T> {
  data?: T;
  message?: string;
  success: boolean;
}

export interface ChallengesResponse {
  challenges: Challenge[];
  profile: string;
}

export interface WebSocketMessage {
  type: 'log' | 'challenge_update' | 'profile_change';
  data: any;
  timestamp: string;
}

// Types pour les stratégies hiérarchiques
export interface ScheduledJob {
  job_id: string;
  action: string;
  status: 'scheduled' | 'expired' | 'running';
  next_run: string | null;
  trigger: string;
  job_name: string;
}

export interface StrategyStatus {
  challenge_id: string;
  strategy_name: string;
  strategy_status: 'active' | 'completed' | 'expired' | 'failed';
  jobs: ScheduledJob[];
  total_jobs: number;
  scheduled_jobs: number;
  expired_jobs: number;
  last_activity: string | null;
  progress: string;
}

export interface SystemJob {
  id: string;
  name: string;
  next_run_time: string | null;
  trigger: string;
}

export interface StrategiesStatusResponse {
  success: boolean;
  scheduler_running: boolean;
  total_strategies: number;
  total_jobs: number;
  strategies: { [key: string]: StrategyStatus };
  system_jobs: SystemJob[];
  status_timestamp: string;
}