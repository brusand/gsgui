import { useState } from 'react';
import ProfileSelectionDialog from './components/ProfileSelectionDialog';
import MainInterface from './components/MainInterface';
import './App.css';

function App() {
  const [selectedProfile, setSelectedProfile] = useState<string | null>(null);
  const [showProfileDialog, setShowProfileDialog] = useState(true);

  const handleProfileSelected = (profileName: string) => {
    setSelectedProfile(profileName);
    setShowProfileDialog(false);
  };

  const handleDisconnect = () => {
    setSelectedProfile(null);
    setShowProfileDialog(true);
  };

  return (
    <div className="app">
      {showProfileDialog ? (
        <ProfileSelectionDialog
          onProfileSelected={handleProfileSelected}
        />
      ) : (
        <MainInterface
          profileName={selectedProfile!}
          onDisconnect={handleDisconnect}
        />
      )}
    </div>
  );
}

export default App;