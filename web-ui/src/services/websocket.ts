import type { WebSocketMessage } from '../types/api';

export class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 3000;
  private listeners: Map<string, ((data: any) => void)[]> = new Map();

  constructor(url: string = '/ws/logs') {
    this.url = url;
  }

  // Nouvelle méthode pour se connecter avec un profile_id spécifique
  connectWithProfile(profileName: string): Promise<void> {
    const profileId = profileName.toLowerCase();
    const newUrl = `/ws/logs/${profileId}`;
    
    // Fermer l'ancienne connexion si elle existe
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('🔄 Closing existing WebSocket connection before new profile connection');
      this.ws.close();
      this.ws = null;
    }
    
    this.url = newUrl;
    return this.connect();
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Construire l'URL WebSocket complète
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${this.url}`;
        console.log('🔌 Connecting to WebSocket:', wsUrl);
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('✅ WebSocket connected');
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('🔥 WebSocket message reçu:', data);
            
            // Gérer les différents types de messages
            
            // Format connection_manager (encapsulé avec data)
            if (data.type === 'broadcast_log' && data.data && data.data.message) {
              console.log('🔥 Format connection_manager détecté');
              const adaptedMessage: WebSocketMessage = {
                type: 'log',
                data: {
                  message: data.data.message,
                  level: data.data.level || 'info',
                  profile_id: data.user_id
                },
                timestamp: data.data.timestamp || data.timestamp
              };
              this.handleMessage(adaptedMessage);
            }
            // Format legacy (direct)
            else if (data.type === 'broadcast_log' && data.message) {
              // Messages BROADCAST_LOG (Fill)
              const adaptedMessage: WebSocketMessage = {
                type: 'log',
                data: {
                  message: data.message,
                  level: data.level || 'info',
                  profile_id: data.profile_id
                },
                timestamp: data.timestamp
              };
              this.handleMessage(adaptedMessage);
            } else if (data.type === 'turbo_log' && data.message) {
              // Messages TURBO_LOG (Turbo)
              const adaptedMessage: WebSocketMessage = {
                type: 'log',
                data: {
                  message: data.message,
                  level: data.level || 'info',
                  profile_id: data.profile_id
                },
                timestamp: data.timestamp
              };
              this.handleMessage(adaptedMessage);
            } else if (data.type === 'challenge_update') {
              // Messages CHALLENGE_UPDATE (Refresh)
              const adaptedMessage: WebSocketMessage = {
                type: 'challenge_update',
                data: data.challenge,
                timestamp: data.timestamp || new Date().toISOString()
              };
              this.handleMessage(adaptedMessage);
            } else if (data.message && data.type) {
              // Format legacy: { timestamp, type, message, profile_id }
              const adaptedMessage: WebSocketMessage = {
                type: 'log',
                data: {
                  message: data.message,
                  level: data.type,
                  profile_id: data.profile_id
                },
                timestamp: data.timestamp
              };
              this.handleMessage(adaptedMessage);
            } else {
              // Format déjà correct ou autre format
              this.handleMessage(data);
            }
          } catch (error) {
            console.error('❌ Error parsing WebSocket message:', error);
          }
        };

        this.ws.onclose = (event) => {
          console.log('🔌 WebSocket disconnected:', event.code);
          this.handleReconnect();
        };

        this.ws.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
          reject(error);
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  private handleMessage(message: WebSocketMessage) {
    const listeners = this.listeners.get(message.type) || [];
    listeners.forEach(listener => listener(message.data));
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`🔄 Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      setTimeout(() => {
        this.connect().catch(error => {
          console.error('❌ Reconnection failed:', error);
        });
      }, this.reconnectInterval);
    } else {
      console.error('❌ Max reconnection attempts reached');
    }
  }

  on(type: string, listener: (data: any) => void) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type)!.push(listener);
  }

  off(type: string, listener: (data: any) => void) {
    const listeners = this.listeners.get(type);
    if (listeners) {
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('⚠️ WebSocket not connected');
    }
  }

  disconnect() {
    console.log('🔌 Disconnecting WebSocket...');
    if (this.ws) {
      // Supprimer les event listeners pour éviter les callbacks indésirables
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      
      // Fermer la connexion
      this.ws.close();
      this.ws = null;
    }
    
    // Réinitialiser les tentatives de reconnexion
    this.reconnectAttempts = 0;
    this.listeners.clear();
    
    console.log('✅ WebSocket disconnected properly');
  }

  // Méthode pour émettre des logs locaux (non-WebSocket)
  emitLocalLog(message: string, level: 'info' | 'success' | 'warning' | 'error' = 'info') {
    const localMessage: WebSocketMessage = {
      type: 'log' as const,
      data: { message, level },
      timestamp: new Date().toISOString()
    };
    this.handleMessage(localMessage);
  }
}

export const wsService = new WebSocketService();