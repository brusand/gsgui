import React, { useState, useEffect } from 'react';
import type { Profile } from '../types/api';
import { apiClient } from '../services/api-v2';
import './ProfileSelector.css';

interface ProfileSelectorProps {
  currentProfile: string | null;
  onProfileChange: (profileName: string) => void;
}

const ProfileSelector: React.FC<ProfileSelectorProps> = ({
  currentProfile,
  onProfileChange
}) => {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newProfileName, setNewProfileName] = useState('');
  const [newProfileToken, setNewProfileToken] = useState('');
  const [showToken, setShowToken] = useState(false);

  useEffect(() => {
    loadProfiles();
  }, []);

  const loadProfiles = async () => {
    try {
      setIsLoading(true);
      const profilesData = await apiClient.getProfiles();
      setProfiles(profilesData);
    } catch (error) {
      console.error('Erreur chargement profils:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleProfileSwitch = async (profileName: string) => {
    if (profileName === currentProfile) return;

    try {
      setIsLoading(true);
      await apiClient.switchProfile(profileName);
      onProfileChange(profileName);
    } catch (error) {
      console.error('Erreur changement profil:', error);
      alert('Erreur lors du changement de profil');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProfileName.trim() || !newProfileToken.trim()) return;

    try {
      setIsLoading(true);
      await apiClient.createProfile(newProfileName.trim(), newProfileToken.trim());
      await loadProfiles();
      setShowCreateForm(false);
      setNewProfileName('');
      setNewProfileToken('');
      
      // Basculer automatiquement sur le nouveau profil
      await handleProfileSwitch(newProfileName.trim());
    } catch (error) {
      console.error('Erreur création profil:', error);
      alert('Erreur lors de la création du profil');
    } finally {
      setIsLoading(false);
    }
  };

  const getProfileIcon = (profile: Profile) => {
    if (!profile.has_token) return '❌';
    if (profile.name === currentProfile) return '🟢';
    return '✅';
  };

  return (
    <div className="profile-selector">
      <div className="profile-header">
        <h2>👤 Profil GuruShots</h2>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="btn btn-secondary"
          disabled={isLoading}
        >
          ➕ Nouveau
        </button>
      </div>

      <div className="current-profile">
        {currentProfile ? (
          <div className="profile-info">
            <span className="profile-icon">🟢</span>
            <span className="profile-name">Profil actuel: <strong>{currentProfile}</strong></span>
            <button
              onClick={() => onProfileChange('')}
              className="btn btn-logout"
              title="Déconnexion"
            >
              🚪 Déconnexion
            </button>
          </div>
        ) : (
          <div className="no-profile">
            <span>🔸 Aucun profil sélectionné</span>
          </div>
        )}
      </div>

      {showCreateForm && (
        <form onSubmit={handleCreateProfile} className="create-profile-form">
          <h3>Créer un nouveau profil</h3>
          <div className="form-group">
            <label htmlFor="profileName">Nom du profil:</label>
            <input
              type="text"
              id="profileName"
              value={newProfileName}
              onChange={(e) => setNewProfileName(e.target.value)}
              placeholder="ex: bruno"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="profileToken">Token GuruShots (gs_t):</label>
            <div className="token-input-group">
              <input
                type={showToken ? "text" : "password"}
                id="profileToken"
                value={newProfileToken}
                onChange={(e) => setNewProfileToken(e.target.value)}
                placeholder="Coller le token gs_t depuis les cookies du navigateur"
                required
              />
              <button
                type="button"
                className="btn btn-token-toggle"
                onClick={() => setShowToken(!showToken)}
                title={showToken ? "Masquer le token" : "Afficher le token"}
              >
                {showToken ? '👁️‍🗨️' : '👁️'}
              </button>
            </div>
            <small className="token-hint">
              💡 Récupérez le token gs_t depuis les cookies de votre navigateur sur gurushots.com
            </small>
          </div>
          <div className="form-buttons">
            <button type="submit" className="btn btn-primary" disabled={isLoading}>
              ✅ Créer
            </button>
            <button
              type="button"
              onClick={() => setShowCreateForm(false)}
              className="btn btn-secondary"
            >
              ❌ Annuler
            </button>
          </div>
        </form>
      )}

      {profiles.length > 0 && (
        <div className="profiles-list">
          <h3>Profils disponibles:</h3>
          <div className="profiles-grid">
            {profiles.map((profile) => (
              <div
                key={profile.name}
                className={`profile-card ${profile.name === currentProfile ? 'active' : ''}`}
                onClick={() => handleProfileSwitch(profile.name)}
              >
                <span className="profile-icon">{getProfileIcon(profile)}</span>
                <span className="profile-name">{profile.name}</span>
                <span className="profile-status">
                  {profile.has_token ? 'Token OK' : 'Pas de token'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {isLoading && (
        <div className="loading-overlay">
          <span>⏳ Chargement...</span>
        </div>
      )}
    </div>
  );
};

export default ProfileSelector;