import React from 'react';
import type { Challenge } from '../types/api';
import './ChallengeTable.css';

interface ChallengeTableProps {
  challenges: Challenge[];
  selectedChallenges: Set<string>;
  onSelectionChange: (challengeId: string, selected: boolean) => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
}

const ChallengeTable: React.FC<ChallengeTableProps> = ({
  challenges,
  selectedChallenges,
  onSelectionChange,
  onSelectAll,
  onSelectNone
}) => {
  // Fonction pour obtenir l'indicateur turbo selon l'état (identique à gs_backend_ui.py)
  const getTurboIndicator = (turboStatus: string) => {
    const turboIndicators: { [key: string]: string } = {
      "none": "",
      "running": "🟡 Running",
      "completed": "✅ OK",
      "failed": "❌ Failed",
      "timer": "⏰ Timer",
      "unknown": "❓ Unknown",
      "locked": "🔒 Locked",
      "free": "🆓 Free",
      "won": "🏆 Won",
      "used": "✅ Used"
    };
    return turboIndicators[turboStatus] || "";
  };

  // Fonction pour obtenir l'indicateur boost selon l'état
  const getBoostIndicator = (boostStatus?: string) => {
    if (!boostStatus) return "";

    // Le backend envoie maintenant le format: "available (21m)" ou "locked" ou "used"
    // On détecte le state de base et on garde le temps restant
    const lowerStatus = boostStatus.toLowerCase();

    // Extraire le state de base et le temps restant
    const baseState = lowerStatus.split(' ')[0]; // "available", "locked", etc.
    const timeRemaining = lowerStatus.includes('(') ? lowerStatus.substring(lowerStatus.indexOf('(')) : '';

    const boostIndicators: { [key: string]: string } = {
      "available": `🚀 Available${timeRemaining}`,
      "active": `⚡ Active${timeRemaining}`,
      "used": "✓ Used",
      "locked": "🔒 Locked",
      "missed": "⏭️ Missed",
      "none": "",
      "unknown": "",
      "unlocked": `🔓 Unlocked${timeRemaining}`
    };

    return boostIndicators[baseState] || boostStatus;
  };

  // Fonction pour obtenir la couleur de fond selon l'état turbo (identique à gs_backend_ui.py)
  const getTurboBackgroundColor = (turboStatus: string) => {
    switch (turboStatus) {
      case "running": return "rgba(255, 235, 59, 0.2)"; // Jaune transparent
      case "completed": return "rgba(76, 175, 80, 0.2)"; // Vert transparent
      case "failed": return "rgba(244, 67, 54, 0.2)"; // Rouge transparent
      case "timer": return "rgba(255, 152, 0, 0.2)"; // Orange transparent
      case "unknown": return "rgba(158, 158, 158, 0.2)"; // Gris transparent
      case "locked": return "rgba(96, 125, 139, 0.2)"; // Bleu-gris transparent
      case "free": return "rgba(139, 195, 74, 0.2)"; // Vert clair transparent
      case "won": return "rgba(255, 193, 7, 0.2)"; // Doré transparent
      case "used": return "rgba(76, 175, 80, 0.2)"; // Vert transparent (comme completed)
      default: return "transparent";
    }
  };

  // Fonction pour obtenir la couleur de fond selon l'état boost
  const getBoostBackgroundColor = (boostStatus?: string) => {
    if (!boostStatus) return "transparent";

    switch (boostStatus) {
      case "available": return "rgba(33, 150, 243, 0.2)"; // Bleu transparent
      case "active": return "rgba(255, 193, 7, 0.2)"; // Jaune doré transparent
      case "used": return "rgba(76, 175, 80, 0.2)"; // Vert transparent
      case "locked": return "rgba(158, 158, 158, 0.2)"; // Gris transparent
      case "unlocked": return "rgba(139, 195, 74, 0.2)"; // Vert clair transparent
      default: return "transparent";
    }
  };

  // Les challenges sont déjà triés côté backend par temps restant croissant
  const sortedChallenges = challenges;

  const handleTitleClick = (challengeId: string) => {
    const isSelected = selectedChallenges.has(challengeId);
    onSelectionChange(challengeId, !isSelected);
  };

  return (
    <div className="challenge-table-container">
      <div className="table-header">
        <h2>🎯 Challenges GuruShots</h2>
        <div className="selection-buttons">
          <button onClick={onSelectAll} className="btn btn-secondary">
            ✅ All
          </button>
          <button onClick={onSelectNone} className="btn btn-secondary">
            ❌ None
          </button>
        </div>
      </div>
      
      <div className="table-wrapper">
        <table className="challenge-table">
          <thead>
            <tr>
              <th className="title-col">Title</th>
              <th className="end-time-col">End Time</th>
              <th className="remaining-col">Remaining</th>
              <th className="votes-col">Votes</th>
              <th className="rank-col">Rank</th>
              <th className="level-col">Level</th>
              <th className="exposure-col">Exposure</th>
              <th className="gps-col">GPS</th>
              <th className="strategy-col">Stratégie</th>
              <th className="turbo-col">Turbo</th>
              <th className="boost-col">Boost</th>
            </tr>
          </thead>
          <tbody>
            {sortedChallenges.map((challenge) => (
              <tr
                key={challenge.id}
                className={`challenge-row ${selectedChallenges.has(challenge.id) ? 'selected' : ''}`}
              >
                <td className="title-cell">
                  <input
                    type="checkbox"
                    checked={selectedChallenges.has(challenge.id)}
                    onChange={() => handleTitleClick(challenge.id)}
                    className="challenge-checkbox"
                  />
                  <span className="challenge-title" title={challenge.title}>
                    {challenge.title}
                  </span>
                </td>
                <td className="end-time-cell">
                  {challenge.end_time}
                </td>
                <td className="remaining-cell">
                  {challenge.time_left_display}
                </td>
                <td className="votes-cell">
                  {challenge.votes}
                </td>
                <td className="rank-cell">
                  {challenge.rank}
                </td>
                <td className="level-cell">
                  {challenge.level}
                </td>
                <td className="exposure-cell">
                  {challenge.exposure}
                </td>
                <td className="gps-cell">
                  {challenge.gps}
                </td>
                <td className="strategy-cell">
                  {challenge.selected_strategy || ""}
                </td>
                <td
                  className="turbo-cell"
                  style={{ backgroundColor: getTurboBackgroundColor(challenge.turbo_status) }}
                >
                  {getTurboIndicator(challenge.turbo_status)}
                </td>
                <td
                  className="boost-cell"
                  style={{ backgroundColor: getBoostBackgroundColor(challenge.boost_status) }}
                >
                  {getBoostIndicator(challenge.boost_status)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {challenges.length === 0 && (
        <div className="empty-state">
          <p>🔄 Aucun challenge chargé. Cliquez sur "Refresh" pour récupérer les challenges.</p>
        </div>
      )}
    </div>
  );
};

export default ChallengeTable;