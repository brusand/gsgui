import React, { useState, useEffect, useRef } from 'react';

interface Props {
  isOpen: boolean;
  isLoading?: boolean;
  error?: string;
  onConfirm: (challengeUrl: string) => void;
  onCancel: () => void;
}

const ChallengeUrlDialog: React.FC<Props> = ({ isOpen, isLoading, error, onConfirm, onCancel }) => {
  const [url, setUrl] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setUrl('');
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleConfirm = () => {
    const slug = url.trim();
    if (slug) onConfirm(slug);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleConfirm();
    if (e.key === 'Escape') onCancel();
  };

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <div className="dialog-container" onClick={e => e.stopPropagation()} style={{ maxWidth: 420 }}>
        <div className="dialog-header">
          <h3>📅 Stratégie one-shot</h3>
          <p style={{ margin: '4px 0 0', fontSize: 13, color: '#aaa' }}>
            Aucun challenge sélectionné — entrez l'URL slug du challenge cible
          </p>
        </div>

        <div className="dialog-body" style={{ padding: '16px 20px' }}>
          <label style={{ display: 'block', marginBottom: 6, fontSize: 13, color: '#ccc' }}>
            URL slug du challenge
          </label>
          <input
            ref={inputRef}
            type="text"
            value={url}
            onChange={e => setUrl(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="ex: frame-it-4"
            style={{
              width: '100%', boxSizing: 'border-box',
              padding: '8px 12px', fontSize: 14,
              background: '#2a2a2a', border: '1px solid #555',
              borderRadius: 6, color: '#fff',
            }}
            disabled={isLoading}
          />
          {error && (
            <p style={{ color: '#ff6b6b', fontSize: 12, marginTop: 6 }}>❌ {error}</p>
          )}
          <p style={{ color: '#888', fontSize: 11, marginTop: 8 }}>
            Trouvable dans l'URL GuruShots : gurushots.com/challenges/<strong>frame-it-4</strong>/photos
          </p>
        </div>

        <div className="dialog-footer">
          <button className="btn btn-secondary" onClick={onCancel} disabled={isLoading}>
            Annuler
          </button>
          <button
            className="btn btn-info"
            onClick={handleConfirm}
            disabled={!url.trim() || isLoading}
          >
            {isLoading ? '⏳ Recherche…' : '🔍 Charger'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChallengeUrlDialog;
