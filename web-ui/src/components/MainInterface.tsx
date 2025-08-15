import React, { useState, useEffect } from 'react';
import ChallengeTable from './ChallengeTable';
import ActionButtons from './ActionButtons';
import LogsPanel from './LogsPanel';
import StrategyEditor from './StrategyEditor';
import LogsViewerModal from './LogsViewerModal';
import StrategiesPanel from './StrategiesPanel';
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
  const [strategyEditorContent, setStrategyEditorContent] = useState('');
  const [isLogsViewerOpen, setIsLogsViewerOpen] = useState(false);
  const [isStrategiesPanelOpen, setIsStrategiesPanelOpen] = useState(false);

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

    wsService.on('log', handleLogMessage);
    wsService.on('challenge_update', handleChallengeUpdate);

    return () => {
      wsService.off('log', handleLogMessage);
      wsService.off('challenge_update', handleChallengeUpdate);
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
      setChallenges(response.challenges || []);
      setSelectedChallenges(new Set()); // Reset selection
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

  const handleEditStrategies = async () => {
    try {
      wsService.emitLocalLog('📝 Ouverture éditeur de stratégies...');
      
      // Récupérer le contenu du fichier strategies.ini
      const configData = await apiClient.getStrategiesConfig();
      setStrategyEditorContent(configData.content);
      setIsStrategyEditorOpen(true);
      
      wsService.emitLocalLog('✅ Éditeur de stratégies ouvert', 'success');
      
    } catch (error) {
      console.error('❌ Erreur ouverture éditeur:', error);
      wsService.emitLocalLog(`❌ Erreur ouverture éditeur: ${error}`, 'error');
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
          onApplyStrategy={handleStrategyApplication}
          onShowActiveStrategies={handleShowActiveStrategies}
          onEditStrategies={handleEditStrategies}
          onSelectAll={handleSelectAll}
          onSelectNone={handleSelectNone}
          onShowLogs={handleShowLogs}
          onShowStrategies={() => setIsStrategiesPanelOpen(!isStrategiesPanelOpen)}
        />

        <ChallengeTable
          challenges={challenges}
          selectedChallenges={selectedChallenges}
          onSelectionChange={handleChallengeSelection}
          onSelectAll={handleSelectAll}
          onSelectNone={handleSelectNone}
        />

        <StrategiesPanel 
          profileName={profileName} 
          isVisible={isStrategiesPanelOpen}
        />

        <LogsPanel profileName={profileName} />
      </main>

      <StrategyEditor
        isOpen={isStrategyEditorOpen}
        onClose={() => setIsStrategyEditorOpen(false)}
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