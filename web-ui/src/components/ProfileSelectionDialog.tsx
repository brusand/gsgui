import React, { useState, useEffect } from 'react';
import type { Profile } from '../types/api';
import { apiClient } from '../services/api-v2';
import { detectGuruShotsToken, saveTokenForLater, createTokenBookmarklet } from '../utils/tokenDetection';
import './ProfileSelectionDialog.css';

interface ProfileSelectionDialogProps {
  onProfileSelected: (profileName: string) => void;
}

const ProfileSelectionDialog: React.FC<ProfileSelectionDialogProps> = ({
  onProfileSelected
}) => {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newProfileName, setNewProfileName] = useState('');
  const [detectedToken, setDetectedToken] = useState<string>('');
  const [tokenDetectionMethod, setTokenDetectionMethod] = useState<string>('');
  const [manualToken, setManualToken] = useState<string>('');
  const [showInstructions, setShowInstructions] = useState(false);

  useEffect(() => {
    loadProfiles();
    // Simuler la détection automatique du token depuis les cookies
    detectTokenFromCookies();
  }, []);

  const loadProfiles = async () => {
    try {
      setIsLoading(true);
      console.log('🔍 Début chargement des profils...');
      
      const profilesData = await apiClient.getProfiles();
      console.log('✅ Profils reçus:', profilesData);
      console.log('📊 Nombre de profils:', profilesData?.length || 0);
      
      if (Array.isArray(profilesData)) {
        setProfiles(profilesData);
        
        // Sélectionner le premier profil s'il existe
        if (profilesData.length > 0) {
          console.log('🎯 Sélection du premier profil:', profilesData[0].name);
          setSelectedProfile(profilesData[0].name);
        } else {
          console.warn('⚠️ Aucun profil trouvé dans la réponse');
        }
      } else {
        console.error('❌ Les données de profils ne sont pas un tableau:', typeof profilesData);
        setProfiles([]);
      }
    } catch (error) {
      console.error('❌ Erreur chargement profils:', error);
      // Afficher l'erreur dans l'interface pour debug
      if (error instanceof Error) {
        console.error('Détails de l\'erreur:', error.message, error.stack);
      }
      setProfiles([]);
    } finally {
      setIsLoading(false);
    }
  };

  const detectTokenFromCookies = async () => {
    try {
      const result = await detectGuruShotsToken();
      
      if (result.token) {
        setDetectedToken(result.token);
        setTokenDetectionMethod(result.method);
        console.log(`✅ ${result.message}: ${result.token.substring(0, 20)}...`);
      } else {
        console.log('❌ Token gs_t non trouvé automatiquement');
        setShowInstructions(true);
      }
    } catch (error) {
      console.log('⚠️ Erreur détection token:', error);
      setShowInstructions(true);
    }
  };

  const handleProfileSelect = () => {
    if (selectedProfile) {
      onProfileSelected(selectedProfile);
    }
  };

  const handleCreateProfile = async () => {
    if (!newProfileName.trim()) {
      alert('Veuillez saisir un nom de profil');
      return;
    }

    const tokenToUse = detectedToken || manualToken;
    if (!tokenToUse.trim()) {
      alert('Aucun token détecté ou saisi');
      return;
    }

    try {
      setIsLoading(true);
      await apiClient.createProfile(newProfileName.trim(), tokenToUse);
      
      // Sauvegarder le token pour la prochaine fois
      saveTokenForLater(tokenToUse);
      
      // Recharger la liste des profils
      await loadProfiles();
      
      // Sélectionner le nouveau profil
      setSelectedProfile(newProfileName.trim());
      
      // Fermer le formulaire
      setShowCreateForm(false);
      setNewProfileName('');
      setManualToken('');
      setDetectedToken('');
      
      alert(`Profil '${newProfileName}' créé avec succès!`);
    } catch (error) {
      console.error('Erreur création profil:', error);
      alert('Erreur lors de la création du profil');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRetryDetection = async () => {
    await detectTokenFromCookies();
  };

  const handleOpenGuruShots = () => {
    window.open('https://gurushots.com', '_blank');
  };

  const handleCopyBookmarklet = async () => {
    const bookmarklet = createTokenBookmarklet();
    const bookmarkTitle = 'GSGUI Token Extractor';
    
    try {
      // Méthode 1: API Chrome Bookmarks (extensions uniquement)
      if (window.chrome && window.chrome.bookmarks) {
        await window.chrome.bookmarks.create({
          title: bookmarkTitle,
          url: bookmarklet
        });
        alert('🔖 Bookmarklet installé automatiquement dans vos favoris Chrome!');
        return;
      }
      
      // Méthode 2: Tentative avec l'API Bookmarks native (expérimentale)
      if ('sidebar' in window && window.sidebar?.addPanel) {
        window.sidebar.addPanel(bookmarkTitle, bookmarklet, '');
        alert('🔖 Bookmarklet installé automatiquement dans vos favoris!');
        return;
      }
      
      // Méthode 3: Invitation à faire glisser (drag & drop)
      const dragElement = document.createElement('a');
      dragElement.href = bookmarklet;
      dragElement.innerHTML = `📑 ${bookmarkTitle}`;
      dragElement.style.cssText = `
        display: inline-block;
        padding: 8px 16px;
        background: #0066cc;
        color: white;
        text-decoration: none;
        border-radius: 4px;
        margin: 10px 0;
        cursor: grab;
      `;
      
      // Créer une popup avec le lien draggable
      const popup = window.open('', 'bookmarklet', 'width=500,height=300');
      if (popup) {
        popup.document.write(`
          <html>
            <head><title>Installation Bookmarklet</title></head>
            <body style="font-family: Arial; padding: 20px;">
              <h2>🔖 Installation du Bookmarklet GSGUI</h2>
              <p><strong>Glissez ce lien dans votre barre de favoris:</strong></p>
              <div style="text-align: center; padding: 20px; border: 2px dashed #ccc;">
                <a href="${bookmarklet}" style="${dragElement.style.cssText}">📑 ${bookmarkTitle}</a>
              </div>
              <hr>
              <h3>Instructions alternatives:</h3>
              <ol>
                <li>Clic droit sur le lien ci-dessus → "Ajouter aux favoris"</li>
                <li>Ou copiez l'URL ci-dessous et créez un favori manuellement:</li>
              </ol>
              <textarea style="width: 100%; height: 100px; font-family: monospace; font-size: 10px;">${bookmarklet}</textarea>
              <br><br>
              <button onclick="window.close()" style="padding: 8px 16px;">Fermer</button>
            </body>
          </html>
        `);
      }
      
      alert('🔖 Popup ouverte avec instructions d\'installation du bookmarklet!');
      
    } catch (error) {
      console.error('Erreur installation bookmarklet:', error);
      
      // Fallback: copie dans le presse-papiers
      try {
        await navigator.clipboard.writeText(bookmarklet);
        alert('📑 Bookmarklet copié dans le presse-papiers!\n\nPour l\'installer:\n1. Créez un nouveau favori\n2. Collez l\'URL copiée\n3. Nommez-le "GSGUI Token Extractor"');
      } catch (clipboardError) {
        prompt('Copiez ce bookmarklet et créez un favori avec cette URL:', bookmarklet);
      }
    }
  };

  if (showCreateForm) {
    return (
      <div className="profile-dialog">
        <div className="dialog-content">
          <h2>🆕 Nouveau Profil GSGUI</h2>
          
          <div className="form-group">
            <label>Nom du profil:</label>
            <input
              type="text"
              value={newProfileName}
              onChange={(e) => setNewProfileName(e.target.value)}
              placeholder="ex: bruno"
              autoFocus
            />
          </div>

          {detectedToken ? (
            <div className="token-detected">
              <h3>✅ Token GuruShots détecté automatiquement</h3>
              <div className="token-display">
                <code>{detectedToken.substring(0, 20)}...</code>
              </div>
              <p>Méthode: <strong>{tokenDetectionMethod}</strong></p>
              <p>Voulez-vous utiliser ce token pour le profil '{newProfileName}' ?</p>
              
              <button 
                onClick={handleRetryDetection}
                className="retry-btn"
              >
                🔄 Redétecter
              </button>
            </div>
          ) : (
            <div className="token-manual">
              <h3>🔑 Récupération manuelle du token</h3>
              
              <div className="detection-options">
                <button 
                  onClick={handleOpenGuruShots}
                  className="option-btn"
                >
                  🌐 Ouvrir GuruShots
                </button>
                
                <button 
                  onClick={handleRetryDetection}
                  className="option-btn"
                >
                  🔄 Redétecter
                </button>
                
                <button 
                  onClick={handleCopyBookmarklet}
                  className="option-btn"
                >
                  🔖 Installer Bookmarklet
                </button>
              </div>

              {showInstructions && (
                <div className="instructions">
                  <h4>Instructions détaillées:</h4>
                  <ol>
                    <li>Connectez-vous sur <strong>gurushots.com</strong></li>
                    <li>Appuyez sur <strong>F12</strong> → <strong>Application</strong> → <strong>Cookies</strong></li>
                    <li>Trouvez le cookie <strong>'gs_t'</strong> et copiez sa valeur</li>
                    <li>Revenez ici et collez le token ci-dessous</li>
                  </ol>
                </div>
              )}
              
              <div className="form-group">
                <label>Token gs_t:</label>
                <input
                  type="text"
                  value={manualToken}
                  onChange={(e) => setManualToken(e.target.value)}
                  placeholder="Collez votre token gs_t ici"
                />
              </div>
            </div>
          )}

          <div className="dialog-buttons">
            <button onClick={handleCreateProfile} disabled={isLoading}>
              ✅ Créer Profil
            </button>
            <button onClick={() => setShowCreateForm(false)}>
              ❌ Annuler
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-dialog">
      <div className="dialog-content">
        <h2>🔑 Sélection du Profil GSGUI</h2>
        
        <p>Sélectionnez votre profil GSGUI</p>
        
        <div className="form-group">
          <label>Profils disponibles: (Trouvé: {profiles.length})</label>
          <select 
            value={selectedProfile} 
            onChange={(e) => setSelectedProfile(e.target.value)}
            disabled={isLoading}
          >
            <option value="">-- Sélectionnez un profil --</option>
            {profiles.map(profile => (
              <option key={profile.name} value={profile.name}>
                {profile.name} {profile.has_token ? '✅' : '❌'}
              </option>
            ))}
          </select>
          {profiles.length === 0 && !isLoading && (
            <div style={{ color: 'red', marginTop: '8px' }}>
              ❌ Aucun profil trouvé. Vérifiez la console pour plus de détails.
            </div>
          )}
        </div>

        <button 
          className="new-profile-btn"
          onClick={() => setShowCreateForm(true)}
        >
          ➕ Nouveau Profil
        </button>

        <div className="dialog-buttons">
          <button 
            onClick={handleProfileSelect} 
            disabled={!selectedProfile || isLoading}
          >
            ✅ OK
          </button>
        </div>

        {isLoading && (
          <div className="loading">
            ⏳ Chargement...
          </div>
        )}
      </div>
    </div>
  );
};

export default ProfileSelectionDialog;