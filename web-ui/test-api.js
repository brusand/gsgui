// Simple test script to debug the API call issue
import axios from 'axios';

async function testProfilesAPI() {
  try {
    console.log('🧪 Test de l\'API des profils...');
    
    const response = await axios.get('http://127.0.0.1:8001/api/v1/profiles', {
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      timeout: 10000
    });
    
    console.log('✅ Statut HTTP:', response.status);
    console.log('📡 En-têtes de réponse:', response.headers);
    console.log('📦 Données reçues:', JSON.stringify(response.data, null, 2));
    console.log('🔍 Type des données:', typeof response.data);
    console.log('🔍 Propriété profiles présente:', 'profiles' in response.data);
    console.log('🔍 Type de response.data.profiles:', typeof response.data.profiles);
    console.log('🔍 Est-ce un tableau:', Array.isArray(response.data.profiles));
    console.log('🔍 Nombre d\'éléments:', response.data.profiles?.length || 0);
    
    if (response.data.profiles && Array.isArray(response.data.profiles)) {
      console.log('👥 Profils trouvés:');
      response.data.profiles.forEach((profile, index) => {
        console.log(`  ${index + 1}. ${profile.name} (Token: ${profile.has_token ? 'Oui' : 'Non'})`);
      });
    }
    
  } catch (error) {
    console.error('❌ Erreur lors du test API:', error.message);
    if (error.response) {
      console.error('📡 Statut HTTP:', error.response.status);
      console.error('📦 Données d\'erreur:', error.response.data);
    }
  }
}

testProfilesAPI();