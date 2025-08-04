import React, { useState, useEffect } from 'react';
import './StrategyEditor.css';

interface StrategyEditorProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (content: string) => Promise<void>;
  initialContent?: string;
}

const StrategyEditor: React.FC<StrategyEditorProps> = ({
  isOpen,
  onClose,
  onSave,
  initialContent = ''
}) => {
  const [content, setContent] = useState(initialContent);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setContent(initialContent);
  }, [initialContent]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave(content);
      onClose();
    } catch (error) {
      console.error('Erreur sauvegarde:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Ctrl+S pour sauvegarder
    if (e.ctrlKey && e.key === 's') {
      e.preventDefault();
      handleSave();
    }
    // Escape pour fermer
    if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="strategy-editor-overlay" onClick={onClose}>
      <div className="strategy-editor-modal" onClick={e => e.stopPropagation()}>
        <div className="strategy-editor-header">
          <h2>✏️ Éditeur de stratégies - strategies.ini</h2>
          <button onClick={onClose} className="close-btn">✕</button>
        </div>
        
        <div className="strategy-editor-info">
          <p>📁 Un backup sera créé automatiquement lors de la sauvegarde</p>
          <p>💡 Utilisez Ctrl+S pour sauvegarder ou Échap pour fermer</p>
        </div>

        <div className="strategy-editor-content">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            className="strategy-editor-textarea"
            placeholder="Contenu du fichier strategies.ini..."
            spellCheck={false}
            autoFocus
          />
        </div>

        <div className="strategy-editor-footer">
          <button
            onClick={onClose}
            className="btn btn-cancel"
            disabled={isSaving}
          >
            ❌ Annuler
          </button>
          <button
            onClick={handleSave}
            className="btn btn-save"
            disabled={isSaving}
          >
            {isSaving ? '⏳ Enregistrement...' : '💾 Sauvegarder'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default StrategyEditor;