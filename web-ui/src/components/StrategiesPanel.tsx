import React, { useState, useEffect } from 'react';
import { apiClient } from '../services/api-v2';
import type { StrategiesStatusResponse } from '../types/api';
import './StrategiesPanel.css';

interface StrategiesPanelProps {
  profileName: string;
  isVisible: boolean;
}

const StrategiesPanel: React.FC<StrategiesPanelProps> = ({ profileName, isVisible }) => {
  const [strategiesData, setStrategiesData] = useState<StrategiesStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedStrategies, setExpandedStrategies] = useState<Set<string>>(new Set());

  // Rafraîchir les données toutes les 30 secondes
  useEffect(() => {
    if (!isVisible) return;

    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await apiClient.getStrategiesStatus();
        setStrategiesData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur inconnue');
        console.error('Erreur lors de la récupération des stratégies:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000); // 30 secondes

    return () => clearInterval(interval);
  }, [isVisible]);

  const toggleStrategyExpansion = (strategyKey: string) => {
    const newExpanded = new Set(expandedStrategies);
    if (newExpanded.has(strategyKey)) {
      newExpanded.delete(strategyKey);
    } else {
      newExpanded.add(strategyKey);
    }
    setExpandedStrategies(newExpanded);
  };

  const getStatusBadge = (status: string) => {
    const badges = {
      active: { emoji: '🟢', text: 'Active', class: 'status-active' },
      completed: { emoji: '✅', text: 'Terminé', class: 'status-completed' },
      expired: { emoji: '🔴', text: 'Expiré', class: 'status-expired' },
      failed: { emoji: '❌', text: 'Échoué', class: 'status-failed' }
    };
    
    const badge = badges[status as keyof typeof badges] || { emoji: '❓', text: status, class: 'status-unknown' };
    
    return (
      <span className={`status-badge ${badge.class}`}>
        {badge.emoji} {badge.text}
      </span>
    );
  };

  const getJobStatusBadge = (status: string) => {
    const badges = {
      scheduled: { emoji: '⏳', text: 'Programmé', class: 'job-scheduled' },
      expired: { emoji: '⏰', text: 'Expiré', class: 'job-expired' },
      running: { emoji: '⚡', text: 'En cours', class: 'job-running' }
    };
    
    const badge = badges[status as keyof typeof badges] || { emoji: '❓', text: status, class: 'job-unknown' };
    
    return (
      <span className={`job-badge ${badge.class}`}>
        {badge.emoji} {badge.text}
      </span>
    );
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      return date.toLocaleString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  const cleanStrategyForChallenge = async (challengeId: string) => {
    try {
      const response = await fetch(`/api/v1/profiles/${profileName}/strategies/${challengeId}/clean`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // Rafraîchir les données après le nettoyage
      const data = await apiClient.getStrategiesStatus();
      setStrategiesData(data);
    } catch (err) {
      console.error('Erreur lors du nettoyage de la stratégie:', err);
      setError(err instanceof Error ? err.message : 'Erreur lors du nettoyage');
    }
  };

  if (!isVisible) return null;

  if (isLoading && !strategiesData) {
    return (
      <div className="strategies-panel">
        <div className="strategies-header">
          <h3>📊 Stratégies Schedulées</h3>
        </div>
        <div className="loading">Chargement des stratégies...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="strategies-panel">
        <div className="strategies-header">
          <h3>📊 Stratégies Schedulées</h3>
        </div>
        <div className="error">❌ Erreur: {error}</div>
      </div>
    );
  }

  if (!strategiesData) {
    return null;
  }

  const strategies = Object.entries(strategiesData.strategies);

  return (
    <div className="strategies-panel">
      <div className="strategies-header">
        <h3>📊 Stratégies Schedulées</h3>
        <div className="strategies-summary">
          <span className="summary-item">
            🎯 {strategiesData.total_strategies} stratégies
          </span>
          <span className="summary-item">
            ⚙️ {strategiesData.total_jobs} jobs
          </span>
          <span className="summary-item">
            {strategiesData.scheduler_running ? '🟢 Actif' : '🔴 Arrêté'}
          </span>
        </div>
      </div>

      <div className="strategies-list">
        {strategies.map(([strategyKey, strategy]) => (
          <div key={strategyKey} className="strategy-item">
            <div 
              className="strategy-header"
              onClick={() => toggleStrategyExpansion(strategyKey)}
            >
              <div className="strategy-info">
                <span className="strategy-toggle">
                  {expandedStrategies.has(strategyKey) ? '▼' : '▶'}
                </span>
                <span className="challenge-id">#{strategy.challenge_id}</span>
                <span className="strategy-name">{strategy.strategy_name}</span>
                {getStatusBadge(strategy.strategy_status)}
                <span className="progress">{strategy.progress}</span>
              </div>
              <div className="strategy-actions">
                <button 
                  className="clean-button"
                  onClick={(e) => {
                    e.stopPropagation();
                    cleanStrategyForChallenge(strategy.challenge_id);
                  }}
                  title="Nettoyer cette stratégie"
                >
                  🧹
                </button>
              </div>
            </div>

            {expandedStrategies.has(strategyKey) && (
              <div className="jobs-list">
                {strategy.jobs.length === 0 ? (
                  <div className="no-jobs">Aucun job programmé</div>
                ) : (
                  strategy.jobs.map((job) => (
                    <div key={job.job_id} className="job-item">
                      <div className="job-info">
                        <span className="job-action">🎬 {job.action}</span>
                        {getJobStatusBadge(job.status)}
                        <span className="job-next-run">
                          ⏰ {formatDate(job.next_run)}
                        </span>
                      </div>
                      <div className="job-details">
                        <small className="job-id">{job.job_id}</small>
                      </div>
                    </div>
                  ))
                )}
                
                {strategy.last_activity && (
                  <div className="last-activity">
                    <small>🕐 Dernière activité: {formatDate(strategy.last_activity)}</small>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {strategiesData.system_jobs.length > 0 && (
        <div className="system-jobs">
          <h4>⚙️ Jobs Système</h4>
          <div className="system-jobs-list">
            {strategiesData.system_jobs.map((job) => (
              <div key={job.id} className="system-job-item">
                <span className="job-name">{job.name}</span>
                <span className="job-next-run">
                  ⏰ {formatDate(job.next_run_time)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="timestamp">
        <small>🕐 Dernière mise à jour: {formatDate(strategiesData.status_timestamp)}</small>
      </div>
    </div>
  );
};

export default StrategiesPanel;