// Utilitaires pour la détection du token GuruShots

export interface TokenDetectionResult {
  token: string | null;
  method: 'localStorage' | 'sessionStorage' | 'manual' | 'clipboard' | 'currentDomain';
  message: string;
}

/**
 * Tente de détecter le token gs_t depuis différentes sources
 */
export async function detectGuruShotsToken(): Promise<TokenDetectionResult> {
  // Méthode 1: Vérifier si on est sur le domaine gurushots.com
  if (window.location.hostname.includes('gurushots.com')) {
    const token = getCookieValue('gs_t');
    if (token) {
      return {
        token,
        method: 'currentDomain',
        message: 'Token trouvé dans les cookies du domaine actuel'
      };
    }
  }

  // Méthode 2: Vérifier localStorage
  const localToken = localStorage.getItem('gs_t');
  if (localToken) {
    return {
      token: localToken,
      method: 'localStorage',
      message: 'Token trouvé dans localStorage'
    };
  }

  // Méthode 3: Vérifier sessionStorage
  const sessionToken = sessionStorage.getItem('gs_t');
  if (sessionToken) {
    return {
      token: sessionToken,
      method: 'sessionStorage',
      message: 'Token trouvé dans sessionStorage'
    };
  }

  // Méthode 4: Essayer de lire depuis le clipboard (nécessite permission)
  try {
    if (navigator.clipboard && navigator.clipboard.readText) {
      const clipboardText = await navigator.clipboard.readText();
      if (isValidGuruShotsToken(clipboardText)) {
        return {
          token: clipboardText,
          method: 'clipboard',
          message: 'Token valide détecté dans le presse-papier'
        };
      }
    }
  } catch (error) {
    // Permission refusée ou API non supportée
  }

  return {
    token: null,
    method: 'manual',
    message: 'Aucun token détecté automatiquement'
  };
}

/**
 * Récupère la valeur d'un cookie par son nom
 */
function getCookieValue(name: string): string | null {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    const cookieValue = parts.pop()?.split(';').shift();
    return cookieValue || null;
  }
  return null;
}

/**
 * Vérifie si une chaîne ressemble à un token GuruShots valide
 */
function isValidGuruShotsToken(text: string): boolean {
  if (!text || text.length < 20) return false;
  
  // Les tokens GuruShots sont généralement des chaînes alphanumériques
  // d'environ 32-64 caractères
  const tokenPattern = /^[a-zA-Z0-9]{20,64}$/;
  return tokenPattern.test(text.trim());
}

/**
 * Sauvegarde le token pour la prochaine fois
 */
export function saveTokenForLater(token: string): void {
  try {
    localStorage.setItem('gs_t', token);
    console.log('✅ Token sauvegardé dans localStorage');
  } catch (error) {
    console.warn('⚠️ Impossible de sauvegarder le token:', error);
  }
}

/**
 * Ouvre une popup pour guider l'utilisateur vers GuruShots
 */
export function openGuruShotsInstructions(): string {
  const instructions = `
🔑 Comment récupérer votre token GuruShots:

1. Ouvrez un nouvel onglet et allez sur https://gurushots.com
2. Connectez-vous à votre compte GuruShots
3. Une fois connecté, appuyez sur F12 pour ouvrir les outils développeur
4. Allez dans l'onglet "Application" (ou "Storage")
5. Dans la sidebar, cliquez sur "Cookies" puis "https://gurushots.com"
6. Cherchez le cookie nommé "gs_t"
7. Copiez sa valeur (clic droit → Copier)
8. Revenez ici et collez le token

Alternative rapide:
- Restez connecté sur GuruShots dans un autre onglet
- Le token pourrait être détecté automatiquement si vous actualisez cette page
  `;
  
  return instructions.trim();
}

/**
 * Crée un bookmarklet pour simplifier la récupération du token
 */
export function createTokenBookmarklet(): string {
  const bookmarkletCode = `
javascript:(function(){
  const token = document.cookie.split(';').find(c => c.trim().startsWith('gs_t='));
  if (token) {
    const tokenValue = token.split('=')[1];
    navigator.clipboard.writeText(tokenValue).then(() => {
      alert('✅ Token GuruShots copié dans le presse-papier: ' + tokenValue.substring(0,20) + '...');
    }).catch(() => {
      prompt('Token GuruShots (copiez-le):', tokenValue);
    });
  } else {
    alert('❌ Token gs_t non trouvé. Assurez-vous d\\'être connecté sur GuruShots.');
  }
})();
  `.trim();

  return bookmarkletCode;
}