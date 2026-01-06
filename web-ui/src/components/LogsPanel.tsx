import React, { useEffect, useRef, useState } from 'react';
import { wsService } from '../services/websocket';
import './LogsPanel.css';

interface LogEntry {
  timestamp: string;
  message: string;
  level: 'info' | 'warning' | 'error' | 'success';
}

interface LogsPanelProps {
  profileName: string;
}

const LogsPanel: React.FC<LogsPanelProps> = ({ profileName }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [autoScroll, setAutoScroll] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Connexion WebSocket avec le profil sélectionné pour recevoir les logs turbo et fill
    wsService.connectWithProfile(profileName)
      .then(() => {
        setIsConnected(true);
        addLog(`WebSocket connecté avec profil ${profileName}`, 'success');
      })
      .catch((error) => {
        setIsConnected(false);
        addLog(`Erreur WebSocket: ${error.message}`, 'error');
      });

    // Écouter les messages de logs
    wsService.on('log', handleLogMessage);

    return () => {
      wsService.off('log', handleLogMessage);
      wsService.disconnect();
    };
  }, [profileName]);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const handleLogMessage = (data: any) => {
    addLog(data.message || JSON.stringify(data), data.level || 'info');
  };

  const addLog = (message: string, level: LogEntry['level'] = 'info') => {
    const newLog: LogEntry = {
      timestamp: new Date().toLocaleTimeString(),
      message,
      level
    };

    setLogs(prev => {
      const updated = [...prev, newLog];
      // Garder seulement les 1000 derniers logs pour éviter les problèmes de mémoire
      return updated.slice(-1000);
    });
  };

  const clearLogs = () => {
    setLogs([]);
  };

  const getLogIcon = (level: LogEntry['level']) => {
    switch (level) {
      case 'success': return '✅';
      case 'warning': return '⚠️';
      case 'error': return '❌';
      default: return 'ℹ️';
    }
  };

  const getLogClass = (level: LogEntry['level']) => {
    return `log-entry log-${level}`;
  };

  return (
    <div className="logs-panel">
      <div className="logs-header">
        <h3>📋 Logs Temps Réel</h3>
        <div className="logs-controls">
          <div className="connection-status">
            <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
              {isConnected ? '🟢' : '🔴'}
            </span>
            <span className="status-text">
              {isConnected ? 'Connecté' : 'Déconnecté'}
            </span>
          </div>
          
          <label className="auto-scroll-toggle">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            Auto-scroll
          </label>
          
          <button onClick={clearLogs} className="btn btn-secondary">
            🗑️ Clear
          </button>
        </div>
      </div>

      <div className="logs-content">
        {logs.length === 0 ? (
          <div className="no-logs">
            <p>📝 Aucun log pour le moment...</p>
            <p className="logs-hint">
              {isConnected 
                ? 'Les logs apparaîtront ici en temps réel'
                : 'Vérifiez que le backend est démarré sur le port 8001'
              }
            </p>
          </div>
        ) : (
          <div className="logs-list">
            {logs.map((log, index) => (
              <div key={index} className={getLogClass(log.level)}>
                <span className="log-time">[{log.timestamp}]</span>
                <span className="log-icon">{getLogIcon(log.level)}</span>
                <span className="log-message">{log.message}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
};

export default LogsPanel;