import React, { useState } from 'react';
import type { Strategy } from '../types/api';
import './StrategySelectionDialog.css';

interface StrategySelectionDialogProps {
  isOpen: boolean;
  strategies: Strategy[];
  selectedCount: number;
  onConfirm: (strategy: string) => void;
  onCancel: () => void;
}

const StrategySelectionDialog: React.FC<StrategySelectionDialogProps> = ({
  isOpen,
  strategies,
  selectedCount,
  onConfirm,
  onCancel
}) => {
  const [selectedStrategy, setSelectedStrategy] = useState<string>('');

  if (!isOpen) return null;

  const handleConfirm = () => {
    if (selectedStrategy) {
      onConfirm(selectedStrategy);
      setSelectedStrategy(''); // Reset pour la prochaine fois
    }
  };

  const handleCancel = () => {
    setSelectedStrategy('');
    onCancel();
  };

  return (
    <div className="dialog-overlay">
      <div className="dialog-content strategy-dialog">
        <div className="dialog-header">
          <h3>📅 Choix de stratégie</h3>
          <button 
            className="dialog-close" 
            onClick={handleCancel}
            aria-label="Fermer"
          >
            ×
          </button>
        </div>

        <div className="dialog-body">
          <p className="dialog-info">
            Sélectionnez la stratégie à appliquer aux <strong>{selectedCount}</strong> challenge(s) sélectionné(s) :
          </p>

          <div className="strategy-list">
            {strategies.map((strategy) => (
              <label key={strategy.name} className="strategy-option">
                <input
                  type="radio"
                  name="strategy"
                  value={strategy.name}
                  checked={selectedStrategy === strategy.name}
                  onChange={(e) => setSelectedStrategy(e.target.value)}
                />
                <div className="strategy-details">
                  <div className="strategy-name">{strategy.name}</div>
                  <div className="strategy-description">{strategy.description}</div>
                </div>
              </label>
            ))}
          </div>

          {strategies.length === 0 && (
            <div className="no-strategies">
              <p>❌ Aucune stratégie disponible</p>
              <p>Vérifiez que le backend est démarré et que les stratégies sont configurées.</p>
            </div>
          )}
        </div>

        <div className="dialog-footer">
          <button 
            className="btn btn-secondary" 
            onClick={handleCancel}
          >
            Annuler
          </button>
          <button 
            className="btn btn-primary" 
            onClick={handleConfirm}
            disabled={!selectedStrategy}
          >
            Appliquer la stratégie
          </button>
        </div>
      </div>
    </div>
  );
};

export default StrategySelectionDialog;