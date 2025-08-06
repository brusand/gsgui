import axios from 'axios';
import type { AxiosInstance } from 'axios';
import type { Profile, Strategy, ApiResponse, ChallengesResponse } from '../types/api';

class GSGUIApiClient {
  private api: AxiosInstance;
  // private baseURL: string;

  constructor(baseURL: string = '/api/v1') {
    // this.baseURL = baseURL;
    this.api = axios.create({
      baseURL,
      timeout: 120000, // 2 minutes pour le turbo qui peut être long
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      },
    });
  }

  // Profiles
  async getProfiles(): Promise<Profile[]> {
    try {
      console.log('🌐 Appel API: GET /api/v1/profiles');
      const response = await this.api.get<{ profiles: Profile[] }>('/profiles');
      console.log('📡 Réponse brute:', response);
      console.log('📦 Données reçues:', response.data);
      console.log('👥 Profils extraits:', response.data.profiles);
      
      if (!response.data || !response.data.profiles) {
        throw new Error('Format de réponse invalide: pas de propriété "profiles"');
      }
      
      if (!Array.isArray(response.data.profiles)) {
        throw new Error('Format de réponse invalide: "profiles" n\'est pas un tableau');
      }
      
      return response.data.profiles;
    } catch (error) {
      console.error('❌ Erreur dans getProfiles():', error);
      if (error instanceof Error) {
        console.error('Message d\'erreur:', error.message);
        console.error('Stack trace:', error.stack);
      }
      throw error; // Re-throw pour que le composant puisse gérer l'erreur
    }
  }

  async createProfile(name: string, token: string): Promise<ApiResponse<void>> {
    const response = await this.api.post('/profiles/add', {}, {
      params: { profile_name: name, xtoken: token }
    });
    return response.data;
  }

  async switchProfile(profileName: string): Promise<ApiResponse<void>> {
    // Le backend n'a pas d'endpoint d'activation - le profil est actif quand on l'utilise
    return { success: true, message: `Profil ${profileName} sélectionné` };
  }

  // Challenges
  async getChallenges(profileName?: string): Promise<ChallengesResponse> {
    const params = profileName ? { profile_name: profileName } : {};
    const response = await this.api.get<ChallengesResponse>('/challenges/', { params });
    return response.data;
  }

  async refreshChallenges(profileName?: string): Promise<ChallengesResponse> {
    const params = profileName ? { profile_name: profileName } : {};
    const response = await this.api.get<ChallengesResponse>('/challenges/', { params });
    return response.data;
  }

  // Actions
  async fillChallenges(challengeIds: string[], votes: number = 80, profileName: string = 'bruno'): Promise<ApiResponse<void>> {
    const url = `/actions/fill?profile_name=${profileName}`;
    console.log('🚀 CALLING FIXED FILL ENDPOINT:', url);
    const response = await this.api.post(url, {
      challenge_ids: challengeIds,
      votes_per_challenge: votes
    });
    return response.data;
  }

  async activateTurbo(challengeIds: string[], profileName: string = 'bruno'): Promise<ApiResponse<void>> {
    if (challengeIds.length !== 1) {
      throw new Error('Le turbo ne peut être activé que sur un seul challenge à la fois');
    }
    
    // Utiliser profile_id (lowercase) pour l'endpoint backend
    const profileId = profileName.toLowerCase();
    const url = `/profiles/${profileId}/turbo/execute`;
    console.log('🚀 Turbo endpoint:', url);
    console.log('Challenge ID:', challengeIds[0]);

    const response = await this.api.post(url, {
      challenge_ids: challengeIds,
      challenge_id: challengeIds[0],  // Pour backward compatibility
      challenge_title: challengeIds[0],
      challenge_time_left: '1j',
      algorithm: ''
    });
    console.log('✅ Turbo response:', response.data);
    return response.data;
  }

  // Strategies
  async getStrategies(): Promise<Strategy[]> {
    const response = await this.api.get<{ strategies: Strategy[] }>('/strategies/list');
    return response.data.strategies;
  }

  async applyStrategy(challengeIds: string[], strategy: string, profileName: string = 'bruno'): Promise<ApiResponse<void>> {
    const profileId = profileName.toLowerCase();
    
    // Appliquer la stratégie à chaque challenge (comme gs_backend_ui)
    const results = [];
    for (const challengeId of challengeIds) {
      try {
        const response = await this.api.post(`/profiles/${profileId}/strategies`, {
          challenge_id: challengeId,
          strategy_name: strategy,
          scheduled_at: new Date(Date.now() + 2 * 60 * 1000).toISOString(), // Dans 2 minutes
          challenge_title: challengeId // Titre sera résolu côté backend
        });
        results.push({ challengeId, success: true, data: response.data });
      } catch (error) {
        results.push({ challengeId, success: false, error });
      }
    }
    
    // Retourner un résumé global
    const successCount = results.filter(r => r.success).length;
    return {
      success: successCount > 0,
      message: `Stratégie ${strategy} appliquée à ${successCount}/${challengeIds.length} challenge(s)`
    };
  }

  async getActiveStrategies(profileName?: string): Promise<any> {
    const params = profileName ? { profile_name: profileName } : {};
    const response = await this.api.get('/strategies/active', { params });
    return response.data;
  }

  async cleanupStrategies(profileName?: string, challengeIds?: string[]): Promise<ApiResponse<void>> {
    const params = profileName ? { profile_name: profileName } : {};
    const response = await this.api.delete('/strategies/cleanup', {
      params,
      data: { challenge_ids: challengeIds }
    });
    return response.data;
  }

  // Stratégies - Édition du fichier strategies.ini
  async getStrategiesConfig(): Promise<{ content: string; path: string }> {
    const response = await this.api.get('/strategies/config');
    return response.data;
  }

  async updateStrategiesConfig(content: string): Promise<{ status: string; message: string; backup: string }> {
    const response = await this.api.post('/strategies/config', { content });
    return response.data;
  }

  // Health check
  async healthCheck(): Promise<boolean> {
    try {
      await this.api.get('/profiles');
      return true;
    } catch {
      return false;
    }
  }
}

export const apiClient = new GSGUIApiClient();
export default GSGUIApiClient;