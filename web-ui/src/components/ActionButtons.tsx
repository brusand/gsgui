import React, { useState } from 'react';
import type { Strategy } from '../types/api';
import VoteInputDialog from './VoteInputDialog';
import StrategySelectionDialog from './StrategySelectionDialog';
import './ActionButtons.css';

interface ActionButtonsProps {
  selectedCount: number;
  totalCount: number;
  strategies: Strategy[];
  isLoading: boolean;
  onRefresh: () => void;
  onFill: (voteCount: number) => void;
  onTurbo: () => void;
  onApplyStrategy: (strategy: string) => void;
  onShowActiveStrategies: () => void;
  onEditStrategies: () => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
  onShowLogs: () => void;
  onShowStrategies: () => void;
  onDeepPurge: () => void;
  onToggleAutoRefresh: () => void;
  autoRefreshEnabled: boolean;
  autoRefreshInterval: number;
}

const ActionButtons: React.FC<ActionButtonsProps> = ({
  selectedCount,
  totalCount,
  strategies,
  isLoading,
  onRefresh,
  onFill,
  onTurbo,
  onApplyStrategy,
  onShowActiveStrategies,
  onEditStrategies,
  onSelectAll,
  onSelectNone,
  onShowLogs,
  onShowStrategies,
  onDeepPurge,
  onToggleAutoRefresh,
  autoRefreshEnabled,
  autoRefreshInterval
}) => {
  const [showVoteDialog, setShowVoteDialog] = useState<boolean>(false);
  const handleStrategyClick = () => {
    onApplyStrategy('__open_editor__');
  };

  const handleFillClick = (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    if (selectedCount > 0) {
      setShowVoteDialog(true);
    }
  };

  const handleVoteConfirm = (voteCount: number) => {
    setShowVoteDialog(false);
    onFill(voteCount);
  };

  const handleVoteCancel = () => {
    setShowVoteDialog(false);
  };

  return (
    <div className="action-buttons">
      <div className="button-row">
        {/* Boutons de sélection */}
        <button
          onClick={onSelectAll}
          disabled={isLoading || totalCount === 0}
          className="btn btn-secondary"
          title="Sélectionner tous les challenges"
        >
          ☑️ All
        </button>

        <button
          onClick={onSelectNone}
          disabled={isLoading || selectedCount === 0}
          className="btn btn-secondary"
          title="Désélectionner tous les challenges"
        >
          ⬜ None
        </button>

        {/* Bouton Refresh */}
        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="btn btn-primary"
          title="Recharger les challenges depuis GuruShots"
        >
          {isLoading ? '⏳' : '🔄'} Refresh
        </button>

        {/* Bouton Boost Detector */}
        <button
          onClick={onToggleAutoRefresh}
          disabled={isLoading}
          className={`btn ${autoRefreshEnabled ? 'btn-success' : 'btn-secondary'}`}
          title={`Boost detector ${autoRefreshEnabled ? 'activé' : 'désactivé'} (toutes les ${autoRefreshInterval} minutes)`}
        >
          {autoRefreshEnabled ? '⚡' : '🔍'} Boost detector ({autoRefreshInterval}m) {autoRefreshEnabled ? 'ON' : 'OFF'}
        </button>
      </div>

      <div className="strategy-row">
        {/* Bouton Fill */}
        <button
          onClick={handleFillClick}
          disabled={selectedCount === 0 || isLoading}
          className="btn btn-success"
          title={`Ouvrir la boîte de dialogue pour saisir le nombre de votes sur ${selectedCount} challenge(s)`}
        >
          ⚡ Fill
          {selectedCount > 0 && ` (${selectedCount})`}
        </button>

        {/* Bouton Turbo */}
        <button
          onClick={onTurbo}
          disabled={selectedCount === 0 || isLoading}
          className="btn btn-warning"
          title={`Activer le mode turbo sur ${selectedCount} challenge(s)`}
        >
          🚀 Turbo
          {selectedCount > 0 && ` (${selectedCount})`}
        </button>

        {/* Bouton Stratégie */}
        <button
          onClick={handleStrategyClick}
          disabled={isLoading}
          className="btn btn-info"
          title={selectedCount > 0
            ? `Appliquer une stratégie sur ${selectedCount} challenge(s) sélectionné(s)`
            : 'Appliquer une stratégie one-shot (saisie d\'URL)'}
        >
          📅 Stratégie
          {selectedCount > 0 && ` (${selectedCount})`}
        </button>

        {/* Bouton Stratégies en cours */}
        <button
          onClick={onShowActiveStrategies}
          disabled={isLoading}
          className="btn btn-purple"
          title="Voir les stratégies actuellement en cours d'exécution"
        >
          📋 Stratégies en cours
        </button>

        {/* Bouton Edition */}
        <button
          onClick={onEditStrategies}
          disabled={isLoading}
          className="btn btn-dark"
          title="Éditer les stratégies disponibles"
        >
          ✏️ Edition
        </button>

        {/* Bouton Stratégies Schedulées */}
        <button
          onClick={onShowStrategies}
          disabled={isLoading}
          className="btn btn-info"
          title="Voir les stratégies schedulées et leurs jobs"
        >
          📊 Stratégies
        </button>

        {/* Bouton Logs */}
        <button
          onClick={onShowLogs}
          disabled={isLoading}
          className="btn btn-logs"
          title="Voir les logs du frontend dans une fenêtre dédiée"
        >
          📋 Logs
        </button>

        {/* Bouton Purge Profonde */}
        <button
          onClick={onDeepPurge}
          disabled={isLoading}
          className="btn btn-danger"
          title="⚠️ ATTENTION: Supprime TOUTES les stratégies et jobs APScheduler. Action irréversible!"
          style={{ 
            backgroundColor: '#dc3545', 
            borderColor: '#dc3545',
            fontWeight: 'bold',
            marginLeft: '10px'
          }}
        >
          🗑️ Purge Profonde
        </button>
      </div>

      {/* Informations sur la sélection */}
      <div className="selection-info">
        {selectedCount === 0 ? (
          <span className="info-text">🔸 Sélectionnez des challenges pour activer les actions</span>
        ) : (
          <span className="info-text">
            ✅ {selectedCount} challenge(s) sélectionné(s)
          </span>
        )}
      </div>

      {/* Dialog de saisie du nombre de votes */}
      <VoteInputDialog
        isOpen={showVoteDialog}
        selectedCount={selectedCount}
        onConfirm={handleVoteConfirm}
        onCancel={handleVoteCancel}
      />

    </div>
  );
};

export default ActionButtons;