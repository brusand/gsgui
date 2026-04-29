import React, { useState, useEffect } from 'react';
import ChallengeTable from './ChallengeTable';
import ActionButtons from './ActionButtons';
import LogsPanel from './LogsPanel';
import StrategyEditor, { type ChallengeRef } from './StrategyEditor';
import IniEditor from './IniEditor';
import LogsViewerModal from './LogsViewerModal';
import StrategiesPanel from './StrategiesPanel';
import ChallengeUrlDialog from './ChallengeUrlDialog';
import type { Challenge, Strategy } from '../types/api';
import { apiClient } from '../services/api-v2';
import { wsService } from '../services/websocket';
import './MainInterface.css';

interface MainInterfaceProps {
  profileName: string;
  onDisconnect: () => void;
}

const MainInterface: React.FC<MainInterfaceProps> = ({
  profileName,
  onDisconnect
}) => {
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [selectedChallenges, setSelectedChallenges] = useState<Set<string>>(new Set());
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStrategyEditorOpen, setIsStrategyEditorOpen] = useState(false);
  const [isIniEditorOpen, setIsIniEditorOpen] = useState(false);
  const [strategyEditorContent, setStrategyEditorContent] = useState('');
  const [isLogsViewerOpen, setIsLogsViewerOpen] = useState(false);
  const [isStrategiesPanelOpen, setIsStrategiesPanelOpen] = useState(false);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(false);
  const [autoRefreshInterval, setAutoRefreshInterval] = useState(5);
  const [isUrlDialogOpen, setIsUrlDialogOpen] = useState(false);
  const [urlDialogLoading, setUrlDialogLoading] = useState(false);
  const [urlDialogError, setUrlDialogError] = useState<string | undefined>();
  const [oneShotChallenge, setOneShotChallenge] = useState<ChallengeRef | null>(null);

  // Helper functions pour récupérer les détails des stratégies depuis strategies.ini
  // Commenté temporairement - pas utilisé actuellement
  // const getStrategyDetails = (strategyName: string): { votes: string; timing: string; description: string } => {
  //   // Parser le contenu de strategies.ini pour trouver les détails
  //   // Le strategyEditorContent contient le contenu du fichier strategies.ini
  //   const lines = strategyEditorContent.split('\n');
  //   let inSection = false;
  //   let votes = '80';
  //   let timing = 'end-4m0s';
  //   let description = strategyName;
    
  //   for (let i = 0; i < lines.length; i++) {
  //     const line = lines[i].trim();
      
  //     // Détecter le début de la section [strategyName]
  //     if (line === `[${strategyName}]`) {
  //       inSection = true;
  //       continue;
  //     }
      
  //     // Détecter la fin de la section (nouvelle section ou fin de fichier)
  //     if (inSection && line.startsWith('[') && line !== `[${strategyName}]`) {
  //       break;
  //     }
      
  //     // Parser les propriétés dans la section
  //     if (inSection && line.includes('=')) {
  //       const [key, value] = line.split('=', 2);
  //       const cleanKey = key.trim();
  //       const cleanValue = value.trim();
        
  //       switch (cleanKey) {
  //         case 'votes':
  //           votes = cleanValue;
  //           break;
  //         case 'timing':
  //           timing = cleanValue;
  //           break;
  //         case 'description':
  //           description = cleanValue;
  //           break;
  //       }
  //     }
  //   }
    
  //   return { votes, timing, description };
  // };

  // Helper functions disponibles pour usage futur
  // const getStrategyVotes = (strategyName: string): string => {
  //   return getStrategyDetails(strategyName).votes;
  // };

  // const getStrategyTiming = (strategyName: string): string => {
  //   return getStrategyDetails(strategyName).timing;
  // };

  useEffect(() => {
    loadStrategies();
    refreshChallenges();
    loadStrategiesConfig(); // Charger le contenu strategies.ini pour parsing

    // Écouter les messages WebSocket pour refresh auto
    const handleLogMessage = (data: any) => {
      // Refresh automatique après "Fill terminé" ou "Turbo terminé"
      if (data.message && (data.message.includes('Fill terminé') || data.message.includes('Turbo terminé'))) {
        setTimeout(() => {
          console.log('🔄 Auto-refresh après completion:', data.message);
          refreshChallenges();
        }, 1000);
      }
    };

    const handleChallengeUpdate = (_data: any) => {
      // Refresh immédiat sur challenge_update
      console.log('🔄 Auto-refresh sur challenge_update');
      refreshChallenges();
    };

    const handleChallengesRefreshed = (data: any) => {
      // Auto-refresh depuis le scheduler - mettre à jour directement les challenges
      if (data.challenges && Array.isArray(data.challenges)) {
        console.log(`🔄 Auto-Refresh: ${data.challenges.length} challenges mis à jour`);
        const newChallenges = data.challenges;
        setChallenges(newChallenges);
        // Conserver les sélections qui existent encore dans la nouvelle liste
        setSelectedChallenges(prev => {
          const newIds = new Set(newChallenges.map((c: any) => c.id));
          return new Set([...prev].filter(id => newIds.has(id)));
        });
      }
    };

    wsService.on('log', handleLogMessage);
    wsService.on('challenge_update', handleChallengeUpdate);
    wsService.on('challenges_refreshed', handleChallengesRefreshed);

    return () => {
      wsService.off('log', handleLogMessage);
      wsService.off('challenge_update', handleChallengeUpdate);
      wsService.off('challenges_refreshed', handleChallengesRefreshed);
    };
  }, [profileName]);

  // Auto-refresh toutes les minutes
  useEffect(() => {
    const interval = setInterval(() => {
      console.log('🔄 Auto-refresh périodique (1 minute)');
      refreshChallenges();
    }, 60000); // 60 secondes

    return () => clearInterval(interval);
  }, [profileName]);

  const loadStrategies = async () => {
    try {
      const strategiesData = await apiClient.getStrategies();
      setStrategies(strategiesData);
    } catch (error) {
      console.error('Erreur chargement stratégies:', error);
      // Stratégies par défaut si l'API échoue
      setStrategies([
        { name: 'fill_4h', description: 'Fill toutes les 4h', schedule: '0 */4 * * *' },
        { name: 'fill_30m', description: 'Fill toutes les 30m', schedule: '*/30 * * * *' },
        { name: 'turbo_1h', description: 'Turbo toutes les heures', schedule: '0 * * * *' }
      ]);
    }
  };

  const loadStrategiesConfig = async () => {
    try {
      const configData = await apiClient.getStrategiesConfig();
      setStrategyEditorContent(configData.content);
    } catch (error) {
      console.error('Erreur chargement strategies.ini:', error);
      // Contenu par défaut si l'API échoue
      setStrategyEditorContent('# Strategies configuration file\n# Unable to load from server');
    }
  };

  const refreshChallenges = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.refreshChallenges(profileName);
      const newChallenges = response.challenges || [];
      setChallenges(newChallenges);
      // Conserver les sélections qui existent encore dans la nouvelle liste
      setSelectedChallenges(prev => {
        const newIds = new Set(newChallenges.map((c: any) => c.id));
        return new Set([...prev].filter(id => newIds.has(id)));
      });
    } catch (error) {
      console.error('Erreur refresh challenges:', error);
      setChallenges([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChallengeSelection = (challengeId: string, selected: boolean) => {
    setSelectedChallenges(prev => {
      const newSet = new Set(prev);
      if (selected) {
        newSet.add(challengeId);
      } else {
        newSet.delete(challengeId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    setSelectedChallenges(new Set(challenges.map(c => c.id)));
  };

  const handleSelectNone = () => {
    setSelectedChallenges(new Set());
  };

  const handleFillAction = async (voteCount: number) => {
    if (selectedChallenges.size === 0) return;

    setIsLoading(true);
    try {
      const challengeIds = Array.from(selectedChallenges);
      await apiClient.fillChallenges(challengeIds, voteCount, profileName);
      await refreshChallenges(); // Refresh après l'action
    } catch (error) {
      console.error('Erreur fill challenges:', error);
      alert('Erreur lors du vote Fill');
    } finally {
      setIsLoading(false);
    }
  };

  const handleTurboAction = async () => {
    if (selectedChallenges.size === 0) return;
    
    if (selectedChallenges.size !== 1) {
      alert('Veuillez sélectionner exactement UN challenge pour activer le turbo');
      return;
    }

    setIsLoading(true);
    try {
      const challengeIds = Array.from(selectedChallenges);
      await apiClient.activateTurbo(challengeIds, profileName);
      await refreshChallenges(); // Refresh après l'action
    } catch (error) {
      console.error('Erreur turbo challenges:', error);
      alert(`Erreur lors de l'activation Turbo: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStrategyApplication = async (strategy: string) => {
    if (selectedChallenges.size === 0 || !strategy) return;

    setIsLoading(true);
    try {
      const challengeIds = Array.from(selectedChallenges);
      
      // Application de la stratégie
      const result = await apiClient.applyStrategy(challengeIds, strategy, profileName);
      
      if (result.success) {
        console.log('✅ Stratégie appliquée:', result.message);
      } else {
        console.warn('⚠️ Stratégie partiellement appliquée:', result.message);
      }
      
      await refreshChallenges(); // Refresh après l'action
    } catch (error) {
      console.error('Erreur application stratégie:', error);
      alert('Erreur lors de l\'application de la stratégie');
    } finally {
      setIsLoading(false);
    }
  };

  const handleShowActiveStrategies = async () => {
    try {
      wsService.emitLocalLog('🔍 Appel API /strategies/active...');
      
      const strategiesData = await apiClient.getActiveStrategies(profileName);
      const totalJobs = strategiesData.total_jobs || 0;
      const totalCount = strategiesData.total_count || 0;
      
      wsService.emitLocalLog(`✅ Récupéré ${totalCount} stratégies, ${totalJobs} jobs`, 'success');
      
      // Afficher dans les logs comme gs_backend_ui
      if (totalCount === 0) {
        wsService.emitLocalLog('📋 Aucune stratégie active', 'warning');
      } else {
        wsService.emitLocalLog('📋 === STRATÉGIES EN COURS ===', 'info');
        
        let totalActions = 0;
        strategiesData.strategies?.forEach((strategy: any) => {
          const challengeTitle = strategy.challenge_title || `Challenge ${strategy.challenge_id}`;
          const strategyName = strategy.strategy_name;
          
          // En-tête du challenge
          wsService.emitLocalLog(`🎯 ${challengeTitle}:`, 'info');
          
          // Afficher TOUTES les actions programmées pour ce challenge
          const actions = strategy.actions || [];
          if (actions.length === 0) {
            wsService.emitLocalLog(`   ⚠️ Aucune action programmée pour ${strategyName}`, 'warning');
          } else {
            actions.forEach((action: any) => {
              // Utiliser scheduled_time de l'API et le formater en heure locale
              let timing = 'Heure inconnue';
              if (action.scheduled_time) {
                try {
                  const dt = new Date(action.scheduled_time);
                  timing = dt.toLocaleTimeString('fr-FR', { 
                    hour: '2-digit', 
                    minute: '2-digit', 
                    second: '2-digit' 
                  });
                } catch (e) {
                  timing = action.execution_time || action.timing || 'Heure inconnue';
                }
              } else {
                timing = action.execution_time || action.timing || 'Heure inconnue';
              }
              
              // Affichage selon le type d'action
              let actionDescription = '';
              if (action.action === 'vote') {
                const votes = action.votes || '80';
                actionDescription = `Vote ${votes}`;
              } else if (action.action === 'boost') {
                const param = action.parameter || '0';
                actionDescription = `Boost (param: ${param})`;
              } else if (action.action === 'turbo') {
                const param = action.parameter || '1';
                actionDescription = `Turbo (param: ${param})`;
              } else if (action.action === 'submit') {
                const param = action.parameter || 'image';
                actionDescription = `Submit ${param}`;
              } else if (action.action === 'swap') {
                actionDescription = `Swap images`;
              } else {
                actionDescription = `${action.action} (${action.parameter || ''})`;
              }
              
              wsService.emitLocalLog(`   ⏰ ${timing} - ${actionDescription} pour ${challengeTitle}`, 'info');
              totalActions++;
            });
          }
        });
        
        wsService.emitLocalLog(`📊 Total: ${totalActions} job(s) programmé(s)`, 'success');
        
        // Afficher les stratégies persistantes comme dans l'ancienne version
        if (strategiesData.strategies && strategiesData.strategies.length > 0) {
          wsService.emitLocalLog('💾 Stratégies persistantes:', 'info');
          
          // Grouper par stratégie pour éviter les doublons
          const uniqueStrategies = new Map();
          strategiesData.strategies.forEach((strategy: any) => {
            const challengeTitle = strategy.challenge_title || `Challenge ${strategy.challenge_id}`;
            const strategyName = strategy.strategy_name;
            uniqueStrategies.set(challengeTitle, strategyName);
          });
          
          uniqueStrategies.forEach((strategyName, challengeTitle) => {
            wsService.emitLocalLog(`   📝 ${challengeTitle}: ${strategyName}`, 'info');
          });
        }
        
        // Proposer un cleanup automatique après affichage
        if (totalActions > 0) {
          wsService.emitLocalLog('🧹 Nettoyage automatique des stratégies obsolètes...', 'info');
          await handleCleanupStrategies();
        }
      }
      
    } catch (error) {
      console.error('❌ Erreur récupération stratégies:', error);
      wsService.emitLocalLog(`❌ Erreur récupération stratégies: ${error}`, 'error');
    }
  };

  const handleCleanupStrategies = async () => {
    try {
      wsService.emitLocalLog('🧹 Démarrage cleanup stratégies obsolètes...');
      
      await apiClient.cleanupStrategies(profileName); // Cleanup pour le profil actuel
      
      wsService.emitLocalLog('✅ Cleanup terminé - stratégies obsolètes supprimées', 'success');
      
    } catch (error) {
      console.error('❌ Erreur cleanup stratégies:', error);
      wsService.emitLocalLog(`❌ Erreur cleanup: ${error}`, 'error');
    }
  };

  // Bouton Stratégie → éditeur visuel
  const handleOpenStrategyEditor = () => {
    if (selectedChallenges.size === 0) {
      // Aucun challenge sélectionné → demander l'URL slug
      setUrlDialogError(undefined);
      setIsUrlDialogOpen(true);
    } else {
      setOneShotChallenge(null);
      setIsStrategyEditorOpen(true);
    }
  };

  const handleUrlDialogConfirm = async (challengeUrl: string) => {
    setUrlDialogLoading(true);
    setUrlDialogError(undefined);
    try {
      const data = await apiClient.getChallengeByUrl(challengeUrl, profileName);
      setOneShotChallenge({ id: data.id, title: data.title });
      setIsUrlDialogOpen(false);
      setIsStrategyEditorOpen(true);
    } catch (err: any) {
      setUrlDialogError(err?.response?.data?.detail || err?.message || 'Challenge introuvable');
    } finally {
      setUrlDialogLoading(false);
    }
  };

  // Bouton Edition → éditeur brut .ini
  const handleEditStrategies = async () => {
    try {
      const configData = await apiClient.getStrategiesConfig();
      setStrategyEditorContent(configData.content);
      setIsIniEditorOpen(true);
    } catch (error) {
      console.error('❌ Erreur ouverture éditeur .ini:', error);
    }
  };

  const handleSaveStrategies = async (content: string) => {
    try {
      wsService.emitLocalLog('💾 Sauvegarde strategies.ini...');
      
      // Sauvegarder le contenu modifié
      const result = await apiClient.updateStrategiesConfig(content);
      
      wsService.emitLocalLog('✅ ' + result.message, 'success');
      wsService.emitLocalLog('📁 Backup: ' + result.backup, 'info');
      
      // Recharger les stratégies disponibles
      await loadStrategies();
      
    } catch (error) {
      console.error('❌ Erreur sauvegarde strategies.ini:', error);
      wsService.emitLocalLog(`❌ Erreur sauvegarde: ${error}`, 'error');
      throw error; // Re-throw pour que le modal affiche l'erreur
    }
  };

  const handleShowLogs = () => {
    setIsLogsViewerOpen(true);
  };

  const handleDeepPurge = async () => {
    const confirmed = confirm(
      `⚠️ ATTENTION - PURGE PROFONDE ⚠️\n\n` +
      `Cette action va SUPPRIMER DÉFINITIVEMENT :\n` +
      `• TOUTES les stratégies en cours pour le profil "${profileName}"\n` +
      `• TOUS les jobs APScheduler associés\n` +
      `• TOUTES les données du fichier gsgui.ini\n\n` +
      `Cette action est IRRÉVERSIBLE !\n\n` +
      `Êtes-vous ABSOLUMENT sûr de vouloir continuer ?`
    );

    if (!confirmed) {
      return;
    }

    const doubleConfirm = confirm(
      `🚨 DERNIÈRE CONFIRMATION 🚨\n\n` +
      `Vous allez DÉTRUIRE toutes les stratégies du profil "${profileName}".\n\n` +
      `Tapez "SUPPRIMER" dans le prochain dialogue pour confirmer.`
    );

    if (!doubleConfirm) {
      return;
    }

    const finalConfirm = prompt(
      `Pour confirmer la purge profonde, tapez exactement : SUPPRIMER`
    );

    if (finalConfirm !== "SUPPRIMER") {
      alert("❌ Action annulée - Le texte de confirmation ne correspond pas.");
      return;
    }

    try {
      setIsLoading(true);
      
      // Appeler l'API de purge profonde
      const response = await fetch(`/api/v1/scheduler/deep-purge?profile_id=${profileName}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        alert(
          `✅ PURGE PROFONDE TERMINÉE\n\n` +
          `Jobs APScheduler supprimés: ${result.apscheduler_jobs_removed}\n` +
          `Stratégies INI supprimées: ${result.ini_strategies_removed}\n` +
          `Profils traités: ${result.profiles_processed.join(', ')}\n` +
          `${result.errors.length > 0 ? `\nErreurs: ${result.errors.length}` : ''}`
        );
        
        // Rafraîchir l'interface
        await refreshChallenges();
        setSelectedChallenges(new Set());
      } else {
        throw new Error(result.error || 'Erreur inconnue lors de la purge');
      }
    } catch (error) {
      console.error('Erreur lors de la purge profonde:', error);
      alert(`❌ Erreur lors de la purge profonde:\n${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleAutoRefresh = async () => {
    try {
      setIsLoading(true);

      const response = await fetch(
        `/api/v1/challenges/${profileName}/auto-refresh/toggle?enabled=${!autoRefreshEnabled}&interval_minutes=${autoRefreshInterval}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        setAutoRefreshEnabled(result.enabled);
        setAutoRefreshInterval(result.interval_minutes);

        console.log(
          `Auto-refresh ${result.enabled ? 'activé' : 'désactivé'} (${result.interval_minutes}m)`,
          result.next_run ? `Prochaine exécution: ${result.next_run}` : ''
        );
      } else {
        throw new Error('Échec du toggle auto-refresh');
      }
    } catch (error) {
      console.error('Erreur lors du toggle auto-refresh:', error);
      alert(`❌ Erreur lors du toggle auto-refresh:\n${error}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Charger le statut de l'auto-refresh au démarrage
  useEffect(() => {
    const loadAutoRefreshStatus = async () => {
      try {
        const response = await fetch(
          `/api/v1/challenges/${profileName}/auto-refresh/status`
        );

        if (response.ok) {
          const result = await response.json();
          if (result.success) {
            setAutoRefreshEnabled(result.enabled);
            setAutoRefreshInterval(result.interval_minutes);
          }
        }
      } catch (error) {
        console.error('Erreur lors du chargement du statut auto-refresh:', error);
      }
    };

    loadAutoRefreshStatus();
  }, [profileName]);

  return (
    <div className="main-interface">
      <header className="main-header">
        <div className="header-left">
          <h1>🎯 GSGUI Web Interface v2.0.0</h1>
          <div className="profile-info">
            <span className="profile-label">Profil actuel:</span>
            <span className="profile-name">{profileName}</span>
            <button onClick={onDisconnect} className="btn btn-disconnect">
              🚪 Déconnexion
            </button>
            <a
              href="http://localhost:5001"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-analyzer"
              style={{
                marginLeft: '10px',
                textDecoration: 'none',
                backgroundColor: '#000',
                color: '#fff',
                border: '1px solid #333'
              }}
            >
              📊 Web Analyzer
            </a>
          </div>
        </div>
      </header>

      <main className="main-content">
        <ActionButtons
          selectedCount={selectedChallenges.size}
          totalCount={challenges.length}
          strategies={strategies}
          isLoading={isLoading}
          onRefresh={refreshChallenges}
          onFill={handleFillAction}
          onTurbo={handleTurboAction}
          onApplyStrategy={() => handleOpenStrategyEditor()}
          onShowActiveStrategies={handleShowActiveStrategies}
          onEditStrategies={handleEditStrategies}
          onSelectAll={handleSelectAll}
          onSelectNone={handleSelectNone}
          onShowLogs={handleShowLogs}
          onShowStrategies={() => setIsStrategiesPanelOpen(!isStrategiesPanelOpen)}
          onDeepPurge={handleDeepPurge}
          onToggleAutoRefresh={handleToggleAutoRefresh}
          autoRefreshEnabled={autoRefreshEnabled}
          autoRefreshInterval={autoRefreshInterval}
        />

        <ChallengeTable
          challenges={challenges}
          selectedChallenges={selectedChallenges}
          onSelectionChange={handleChallengeSelection}
          onSelectAll={handleSelectAll}
          onSelectNone={handleSelectNone}
          onCancelStrategy={async (challengeId) => {
            try {
              await fetch(`/api/v1/profiles/${profileName.toLowerCase()}/strategies/${challengeId}/clean`, { method: 'DELETE' });
              refreshChallenges();
            } catch (e) {
              console.error('Erreur annulation stratégie:', e);
            }
          }}
        />

        <StrategiesPanel 
          profileName={profileName} 
          isVisible={isStrategiesPanelOpen}
        />

        <LogsPanel profileName={profileName} />
      </main>

      {/* Popup saisie URL challenge (one-shot sans sélection) */}
      <ChallengeUrlDialog
        isOpen={isUrlDialogOpen}
        isLoading={urlDialogLoading}
        error={urlDialogError}
        onConfirm={handleUrlDialogConfirm}
        onCancel={() => { setIsUrlDialogOpen(false); setUrlDialogError(undefined); }}
      />

      {/* Éditeur visuel de stratégie */}
      <StrategyEditor
        isOpen={isStrategyEditorOpen}
        onClose={() => { setIsStrategyEditorOpen(false); setOneShotChallenge(null); }}
        profileId={profileName}
        selectedChallenges={
          oneShotChallenge
            ? [oneShotChallenge]
            : challenges
                .filter(c => selectedChallenges.has(c.id))
                .map((c): ChallengeRef => ({ id: c.id, title: c.title, strategyName: c.selected_strategy }))
        }
        onApplied={refreshChallenges}
      />

      {/* Éditeur brut .ini */}
      <IniEditor
        isOpen={isIniEditorOpen}
        onClose={() => setIsIniEditorOpen(false)}
        onSave={handleSaveStrategies}
        initialContent={strategyEditorContent}
      />

      <LogsViewerModal
        isOpen={isLogsViewerOpen}
        onClose={() => setIsLogsViewerOpen(false)}
      />
    </div>
  );
};

export default MainInterface;