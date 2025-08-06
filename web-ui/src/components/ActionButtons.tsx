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
  onShowLogs
}) => {
  const [showVoteDialog, setShowVoteDialog] = useState<boolean>(false);
  const [showStrategyDialog, setShowStrategyDialog] = useState<boolean>(false);

  const handleStrategyClick = () => {
    if (selectedCount > 0) {
      setShowStrategyDialog(true);
    }
  };

  const handleStrategyConfirm = (strategy: string) => {
    setShowStrategyDialog(false);
    onApplyStrategy(strategy);
  };

  const handleStrategyCancel = () => {
    setShowStrategyDialog(false);
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
          disabled={selectedCount === 0 || isLoading}
          className="btn btn-info"
          title={`Sélectionner et appliquer une stratégie sur ${selectedCount} challenge(s)`}
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

        {/* Bouton Logs */}
        <button
          onClick={onShowLogs}
          disabled={isLoading}
          className="btn btn-logs"
          title="Voir les logs du frontend dans une fenêtre dédiée"
        >
          📋 Logs
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

      {/* Dialog de sélection de stratégie */}
      <StrategySelectionDialog
        isOpen={showStrategyDialog}
        strategies={strategies}
        selectedCount={selectedCount}
        onConfirm={handleStrategyConfirm}
        onCancel={handleStrategyCancel}
      />
    </div>
  );
};

export default ActionButtons;