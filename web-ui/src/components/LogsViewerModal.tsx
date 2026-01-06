import React, { useEffect, useRef, useState } from 'react';
import './LogsViewerModal.css';

interface LogsViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const LogsViewerModal: React.FC<LogsViewerModalProps> = ({ isOpen, onClose }) => {
  const [logs, setLogs] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [profileFilter, setProfileFilter] = useState('');
  const [filteredLogs, setFilteredLogs] = useState('');
  const logsEndRef = useRef<HTMLDivElement>(null);
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const loadLogs = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Récupérer les logs du fichier backend.log
      const response = await fetch('/api/v1/logs/backend');
      
      if (!response.ok) {
        throw new Error(`Erreur ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.text();
      setLogs(data);
      setFilteredLogs(data); // Initialiser les logs filtrés
      
      // Auto-scroll vers le bas
      setTimeout(() => {
        if (logsEndRef.current) {
          logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
      }, 100);
      
    } catch (error) {
      console.error('Erreur chargement logs:', error);
      setError(`Impossible de charger les logs: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadLogs();
      
      if (autoRefresh) {
        refreshIntervalRef.current = setInterval(loadLogs, 5000); // Refresh toutes les 5 secondes
      }
    }
    
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
        refreshIntervalRef.current = null;
      }
    };
  }, [isOpen, autoRefresh]);

  // Effet pour filtrer les logs quand le terme de recherche ou le filtre profil change
  useEffect(() => {
    const lines = logs.split('\n');
    let filtered = lines;
    
    // Filtrer par terme de recherche
    if (searchTerm.trim()) {
      filtered = filtered.filter(line => 
        line.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    
    // Filtrer par profil ID (format [profile_id])
    if (profileFilter.trim()) {
      filtered = filtered.filter(line => 
        line.includes(`[${profileFilter}]`)
      );
    }
    
    setFilteredLogs(filtered.join('\n'));
  }, [logs, searchTerm, profileFilter]);

  const handleRefresh = () => {
    loadLogs();
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const clearSearch = () => {
    setSearchTerm('');
    setProfileFilter('');
  };

  const handleProfileFilterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setProfileFilter(e.target.value);
  };

  const handleDownload = () => {
    const blob = new Blob([logs], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `backend_logs_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.log`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const formatLogContent = (content: string) => {
    if (!content) return [];
    
    return content.split('\n').map((line, index) => {
      const formattedLine = formatLogLine(line);
      return (
        <div key={index} className={`log-line ${getLogLineClass(line)}`}>
          {formattedLine || '\u00A0'} {/* Non-breaking space for empty lines */}
        </div>
      );
    });
  };

  const formatLogLine = (line: string) => {
    if (!line.trim()) return '';
    
    // Rechercher un timestamp au début de la ligne (format: YYYY-MM-DD HH:MM:SS)
    const timestampRegex = /^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s*(.*)/;
    const match = line.match(timestampRegex);
    
    if (match) {
      const [, timestamp, message] = match;
      return (
        <>
          <span className="log-timestamp">[{timestamp}]</span>
          <span className="log-message"> {message}</span>
        </>
      );
    }
    
    // Si pas de timestamp reconnu, afficher la ligne telle quelle
    return line;
  };

  const getLogLineClass = (line: string) => {
    const lowercaseLine = line.toLowerCase();
    if (lowercaseLine.includes('error') || lowercaseLine.includes('❌')) return 'log-error';
    if (lowercaseLine.includes('warning') || lowercaseLine.includes('warn') || lowercaseLine.includes('⚠️')) return 'log-warning';
    if (lowercaseLine.includes('success') || lowercaseLine.includes('✅')) return 'log-success';
    if (lowercaseLine.includes('[vite]') || lowercaseLine.includes('dev server')) return 'log-vite';
    return 'log-info';
  };

  if (!isOpen) return null;

  return (
    <div className="logs-modal-overlay" onClick={onClose}>
      <div className="logs-modal" onClick={(e) => e.stopPropagation()}>
        <div className="logs-modal-header">
          <div className="logs-modal-title">
            <h2>📋 Logs Backend</h2>
            <span className="logs-file-path">/logs/backend.log</span>
          </div>
          
          <div className="logs-modal-controls">
            <div className="search-section">
              <input
                type="text"
                placeholder="Rechercher dans les logs..."
                value={searchTerm}
                onChange={handleSearchChange}
                className="search-input"
              />
              <input
                type="text"
                placeholder="Filtrer par profil (ex: bruno, caloune)..."
                value={profileFilter}
                onChange={handleProfileFilterChange}
                className="search-input profile-filter"
              />
              {(searchTerm || profileFilter) && (
                <button onClick={clearSearch} className="btn btn-clear-search">
                  ✕
                </button>
              )}
            </div>
            
            <div className="control-buttons">
              <label className="auto-refresh-toggle">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                />
                Auto-refresh (5s)
              </label>
              
              <button 
                onClick={handleRefresh} 
                className="btn btn-refresh"
                disabled={isLoading}
              >
                {isLoading ? '🔄' : '↻'} Refresh
              </button>
              
              <button 
                onClick={handleDownload} 
                className="btn btn-download"
                disabled={!logs}
              >
                💾 Download
              </button>
              
              <button onClick={onClose} className="btn btn-close">
                ✕
              </button>
            </div>
          </div>
        </div>
        
        <div className="logs-modal-content">
          {error ? (
            <div className="logs-error">
              <p>❌ {error}</p>
              <button onClick={handleRefresh} className="btn btn-retry">
                🔄 Réessayer
              </button>
            </div>
          ) : (
            <div className="logs-container">
              <div className="logs-text">
                {isLoading && logs === '' ? (
                  <div className="logs-loading">
                    <p>🔄 Chargement des logs...</p>
                  </div>
                ) : logs ? (
                  <>
                    {searchTerm && (
                      <div className="search-info">
                        <p>🔍 Recherche: "{searchTerm}" - {filteredLogs.split('\n').filter(l => l.trim()).length} résultats</p>
                      </div>
                    )}
                    {formatLogContent(filteredLogs)}
                    <div ref={logsEndRef} className="logs-end-marker" />
                  </>
                ) : (
                  <div className="logs-empty">
                    <p>📝 Aucun log disponible</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        
        <div className="logs-modal-footer">
          <div className="logs-stats">
            {logs && (
              <>
                <span>Lignes: {logs.split('\n').length}</span>
                <span>Taille: {new Blob([logs]).size} bytes</span>
                <span>Dernière mise à jour: {new Date().toLocaleTimeString()}</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LogsViewerModal;