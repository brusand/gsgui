import React, { useState, useEffect } from 'react';
import './IniEditor.css';

interface IniEditorProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (content: string) => Promise<void>;
  initialContent?: string;
}

const IniEditor: React.FC<IniEditorProps> = ({ isOpen, onClose, onSave, initialContent = '' }) => {
  const [content, setContent] = useState(initialContent);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => { setContent(initialContent); }, [initialContent]);

  const handleSave = async () => {
    setIsSaving(true);
    try { await onSave(content); onClose(); }
    catch (e) { console.error('Erreur sauvegarde:', e); }
    finally { setIsSaving(false); }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.ctrlKey && e.key === 's') { e.preventDefault(); handleSave(); }
    if (e.key === 'Escape') onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="ini-overlay" onClick={onClose}>
      <div className="ini-modal" onClick={e => e.stopPropagation()}>
        <div className="ini-header">
          <h2>✏️ Éditeur brut — strategies.ini</h2>
          <button onClick={onClose} className="ini-close">✕</button>
        </div>
        <div className="ini-info">
          <span>📁 Backup automatique à la sauvegarde</span>
          <span>💡 Ctrl+S · Échap</span>
        </div>
        <textarea
          value={content}
          onChange={e => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          className="ini-textarea"
          spellCheck={false}
          autoFocus
        />
        <div className="ini-footer">
          <button onClick={onClose} className="ini-btn ini-btn-cancel" disabled={isSaving}>Annuler</button>
          <button onClick={handleSave} className="ini-btn ini-btn-save" disabled={isSaving}>
            {isSaving ? '⏳ Enregistrement...' : '💾 Sauvegarder'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default IniEditor;
