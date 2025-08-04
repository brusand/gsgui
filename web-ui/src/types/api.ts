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