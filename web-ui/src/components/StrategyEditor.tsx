import React, { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { apiClient } from '../services/api-v2';
import CommandRow, { type CommandDef } from './CommandRow';
import './StrategyEditor.css';

export interface ChallengeRef { id: string; title: string; }

interface Template {
  name: string;
  description: string;
  commands: Array<{ type: string; args: Record<string, any> }>;
  is_instance: boolean;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  profileId: string;
  selectedChallenges: ChallengeRef[];
  onApplied?: () => void;
}

function withIds(cmds: Array<{ type: string; args: Record<string, any> }>): CommandDef[] {
  return cmds.map(c => ({ ...c, id: uuidv4() }));
}

const StrategyEditor: React.FC<Props> = ({
  isOpen, onClose, profileId, selectedChallenges, onApplied
}) => {
  const [schema, setSchema]           = useState<Record<string, any>>({});
  const [templates, setTemplates]     = useState<Template[]>([]);
  const [commands, setCommands]       = useState<CommandDef[]>([]);
  const [description, setDescription] = useState('');
  const [scheduleWhen, setScheduleWhen] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [applying, setApplying]       = useState(false);
  const [runningOnce, setRunningOnce] = useState(false);
  const [newTemplateName, setNewTemplateName] = useState('');
  const [showNewTemplate, setShowNewTemplate] = useState(false);
  const [status, setStatus]           = useState<{ type: 'ok'|'err'|'info'; msg: string } | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    apiClient.getCommandSchema().then(r => setSchema(r.schema)).catch(console.error);
    apiClient.getTemplates(false).then(r => setTemplates(r.templates)).catch(console.error);
  }, [isOpen]);

  const flash = (type: 'ok'|'err'|'info', msg: string, dur = 4000) => {
    setStatus({ type, msg });
    if (dur > 0) setTimeout(() => setStatus(null), dur);
  };

  const loadTemplate = useCallback((name: string) => {
    const tpl = templates.find(t => t.name === name);
    if (!tpl) return;
    setCommands(withIds(tpl.commands));
    setDescription(tpl.description);
    setScheduleWhen((tpl as any).schedule_when || '');
    setSelectedTemplate(name);
  }, [templates]);

  const moveCommand = (from: number, to: number) => {
    setCommands(prev => {
      const next = [...prev];
      const [item] = next.splice(from, 1);
      next.splice(to, 0, item);
      return next;
    });
  };

  const addCommand = () => {
    setCommands(prev => [...prev, { id: uuidv4(), type: 'vote', args: {} }]);
  };

  // Sauvegarde une instance dans strategies.ini + applique au challenge
  const saveAndApplyOne = async (challenge: ChallengeRef, templateName: string): Promise<boolean> => {
    const instanceName = `${templateName}__${profileId}__${challenge.id}`;
    try {
      // 1. Sauvegarder l'instance dans strategies.ini
      await apiClient.updateTemplate(instanceName, description, commands, scheduleWhen);
      // 2. Appliquer au challenge via l'endpoint existant
      await apiClient.applyStrategy([challenge.id], instanceName, profileId);
      return true;
    } catch (e: any) {
      console.error(`Erreur apply ${challenge.title}:`, e);
      return false;
    }
  };

  const handleSaveAsTemplate = async () => {
    const name = newTemplateName.trim();
    if (!name) { flash('err', 'Nom du template requis'); return; }
    if (commands.length === 0) { flash('err', 'Stratégie vide'); return; }
    try {
      await apiClient.updateTemplate(name, description, commands, scheduleWhen);
      flash('ok', `✅ Template "${name}" sauvegardé`);
      setNewTemplateName('');
      setShowNewTemplate(false);
      setSelectedTemplate(name);
      // Recharger la liste des templates
      apiClient.getTemplates(false).then(r => setTemplates(r.templates)).catch(console.error);
    } catch (e: any) {
      flash('err', `Erreur: ${e.message}`);
    }
  };

  const handleRunOnce = async () => {
    if (selectedChallenges.length === 0) { flash('err', 'Aucun challenge sélectionné'); return; }
    if (commands.length === 0) { flash('err', 'La stratégie est vide'); return; }
    setRunningOnce(true);
    flash('info', `Exécution one-shot sur ${selectedChallenges.length} challenge(s)…`, 0);
    let ok = 0;
    for (const challenge of selectedChallenges) {
      try {
        await apiClient.runCommandsOnce(profileId, challenge.id, commands);
        ok++;
      } catch (e: any) {
        console.error(`Erreur one-shot ${challenge.title}:`, e);
      }
    }
    setRunningOnce(false);
    if (ok === selectedChallenges.length) {
      flash('ok', `⚡ One-shot lancé sur ${ok} challenge(s)`);
      setTimeout(() => { onApplied?.(); onClose(); }, 1200);
    } else {
      flash('err', `⚠️ ${ok}/${selectedChallenges.length} challenges traités`);
    }
  };

  const handleValidate = async () => {
    if (selectedChallenges.length === 0) {
      flash('err', 'Aucun challenge sélectionné');
      return;
    }
    if (commands.length === 0) {
      flash('err', 'La stratégie est vide');
      return;
    }
    setApplying(true);
    flash('info', `Application sur ${selectedChallenges.length} challenge(s)…`, 0);

    // Si un nouveau nom est saisi, auto-sauvegarder le template avant d'instancier
    const newName = newTemplateName.trim();
    if (newName) {
      try {
        await apiClient.updateTemplate(newName, description, commands, scheduleWhen);
        setNewTemplateName('');
        setShowNewTemplate(false);
        setSelectedTemplate(newName);
        apiClient.getTemplates(false).then(r => setTemplates(r.templates)).catch(console.error);
      } catch (e: any) {
        flash('err', `Erreur sauvegarde template: ${e.message}`);
        setApplying(false);
        return;
      }
    }
    const templateName = newName || selectedTemplate || 'custom';

    let ok = 0;
    for (const challenge of selectedChallenges) {
      const success = await saveAndApplyOne(challenge, templateName);
      if (success) ok++;
    }

    setApplying(false);
    if (ok === selectedChallenges.length) {
      flash('ok', `✅ Stratégie appliquée à ${ok} challenge(s)`);
      setTimeout(() => { onApplied?.(); onClose(); }, 1200);
    } else {
      flash('err', `⚠️ ${ok}/${selectedChallenges.length} challenges traités — voir console`);
    }
  };

  if (!isOpen) return null;

  const templateOptions = templates.filter(t => !t.is_instance);

  return (
    <div className="se-overlay" onClick={onClose}>
      <div className="se-modal" onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="se-header">
          <h2>📅 Éditeur de stratégie</h2>
          <div className="se-challenges-badges">
            {selectedChallenges.map(c => (
              <span key={c.id} className="se-challenge-badge" title={c.id}>{c.title}</span>
            ))}
          </div>
          <button className="se-close" onClick={onClose}>✕</button>
        </div>

        {/* Toolbar : template picker + description */}
        <div className="se-toolbar">
          <div className="se-field">
            <label>Template</label>
            <div className="se-template-row">
              <select value={selectedTemplate} onChange={e => loadTemplate(e.target.value)}>
                <option value="">— choisir un template —</option>
                {templateOptions.map(t => (
                  <option key={t.name} value={t.name}>{t.name}</option>
                ))}
              </select>
              <button
                className="se-new-tpl-btn"
                onClick={() => setShowNewTemplate(v => !v)}
                title="Créer un nouveau template"
              >+</button>
            </div>
          </div>
          {showNewTemplate && (
            <div className="se-field se-new-tpl-field">
              <label>Nouveau template</label>
              <div className="se-template-row">
                <input
                  type="text"
                  placeholder="nom_du_template"
                  value={newTemplateName}
                  onChange={e => setNewTemplateName(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSaveAsTemplate()}
                  autoFocus
                />
                <button className="se-save-tpl-btn" onClick={handleSaveAsTemplate}>💾</button>
              </div>
            </div>
          )}
          <div className="se-field se-field-grow">
            <label>Description</label>
            <input
              type="text" value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Description de la stratégie…"
            />
          </div>
          <div className="se-field se-field-grow">
            <label>
              Programmation conditionnelle (optionnel)
              <span className="se-hint" title="Ex: votes>2200000|players>2000 (programme quand condition remplie)">ℹ️</span>
            </label>
            <input
              type="text" value={scheduleWhen}
              onChange={e => setScheduleWhen(e.target.value)}
              placeholder="votes>2200000|players>2000,deadline=end-1h0m0s"
            />
          </div>
        </div>

        {/* Commandes */}
        <div className="se-commands">
          {commands.length === 0 && (
            <div className="se-empty">Choisissez un template ou ajoutez une commande.</div>
          )}
          {commands.map((cmd, i) => (
            <CommandRow
              key={cmd.id}
              cmd={cmd}
              schema={schema}
              index={i}
              total={commands.length}
              onChange={updated => setCommands(prev => prev.map(c => c.id === updated.id ? updated : c))}
              onMove={moveCommand}
              onDelete={id => setCommands(prev => prev.filter(c => c.id !== id))}
            />
          ))}
          <button className="se-add-btn" onClick={addCommand}>+ Ajouter une commande</button>
        </div>

        {/* Status */}
        {status && <div className={`se-status se-status-${status.type}`}>{status.msg}</div>}

        {/* Footer */}
        <div className="se-footer">
          <button className="se-btn se-btn-cancel" onClick={onClose} disabled={applying}>Annuler</button>
          <div className="se-footer-right">
            <span className="se-apply-info">
              {selectedChallenges.length} challenge{selectedChallenges.length > 1 ? 's' : ''} sélectionné{selectedChallenges.length > 1 ? 's' : ''}
            </span>
            <button
              className="se-btn se-btn-oneshot"
              onClick={handleRunOnce}
              disabled={runningOnce || applying || commands.length === 0}
              title="Exécute les commandes une fois maintenant, sans sauvegarder de stratégie persistante"
            >
              {runningOnce ? '⏳ Exécution…' : '⚡ One-shot'}
            </button>
            <button
              className="se-btn se-btn-validate"
              onClick={handleValidate}
              disabled={applying || runningOnce || commands.length === 0}
            >
              {applying ? '⏳ Application…' : `✅ Valider et appliquer`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StrategyEditor;
