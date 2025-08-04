import React, { useState } from 'react';
import './VoteInputDialog.css';

interface VoteInputDialogProps {
  isOpen: boolean;
  selectedCount: number;
  onConfirm: (voteCount: number) => void;
  onCancel: () => void;
}

const VoteInputDialog: React.FC<VoteInputDialogProps> = ({
  isOpen,
  selectedCount,
  onConfirm,
  onCancel
}) => {
  const [voteCount, setVoteCount] = useState<number>(80);

  const handleConfirm = () => {
    if (voteCount >= 1 && voteCount <= 999) {
      onConfirm(voteCount);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleConfirm();
    } else if (e.key === 'Escape') {
      onCancel();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="vote-dialog-overlay">
      <div className="vote-dialog">
        <div className="vote-dialog-header">
          <h3>⚡ Fill - Nombre de votes</h3>
        </div>
        
        <div className="vote-dialog-content">
          <p>
            Nombre de votes à exécuter pour{' '}
            <strong>{selectedCount}</strong> challenge(s) sélectionné(s):
          </p>
          
          <div className="vote-input-container">
            <input
              type="number"
              value={voteCount}
              onChange={(e) => setVoteCount(Number(e.target.value))}
              onKeyPress={handleKeyPress}
              min={1}
              max={999}
              step={1}
              className="vote-input"
              autoFocus
            />
            <span className="vote-input-label">votes</span>
          </div>
          
          <div className="vote-info">
            <p className="vote-range">Valeurs autorisées: 1 à 999 votes</p>
            <p className="vote-total">
              Total: <strong>{voteCount * selectedCount}</strong> votes
            </p>
          </div>
        </div>
        
        <div className="vote-dialog-actions">
          <button
            onClick={onCancel}
            className="btn btn-secondary"
          >
            ❌ Annuler
          </button>
          <button
            onClick={handleConfirm}
            disabled={voteCount < 1 || voteCount > 999}
            className="btn btn-success"
          >
            ✅ Confirmer
          </button>
        </div>
      </div>
    </div>
  );
};

export default VoteInputDialog;