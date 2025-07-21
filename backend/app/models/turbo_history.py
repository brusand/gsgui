"""
Turbo History models - Basé sur le système turbo_history de gsui.py
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, Dict, Any

Base = declarative_base()


class TurboHistory(Base):
    """
    Historique des comparaisons turbo
    Basé sur la section [turbo_history] de gsgui.ini
    """
    __tablename__ = "turbo_history"
    
    # Identifiant unique
    id = Column(String, primary_key=True)
    
    # Références
    challenge_id = Column(String, ForeignKey("challenges.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Informations du challenge
    challenge_title = Column(String(255), nullable=False)
    time_left = Column(String(50))  # Format "0D 17H 42M 40S"
    
    # Algorithme utilisé
    algorithm = Column(String(50), nullable=False)
    strategy_description = Column(Text)
    success = Column(Boolean, nullable=False)
    
    # Photo 1
    photo1_id = Column(String(255), nullable=False)
    photo1_ratio = Column(Float)
    photo1_votes = Column(Integer)
    photo1_rank = Column(Integer)
    photo1_found = Column(Boolean, default=False)
    
    # Photo 2
    photo2_id = Column(String(255), nullable=False)
    photo2_ratio = Column(Float)
    photo2_votes = Column(Integer)
    photo2_rank = Column(Integer)
    photo2_found = Column(Boolean, default=False)
    
    # Gagnant
    winner_id = Column(String(255), nullable=False)
    is_photo1_winner = Column(Boolean, nullable=False)
    
    # Métadonnées
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    challenge = relationship("Challenge", back_populates="turbo_history")
    user = relationship("User", back_populates="turbo_history")
    
    def __repr__(self):
        return f"<TurboHistory(id='{self.id}', challenge='{self.challenge_title}', algorithm='{self.algorithm}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour l'API"""
        return {
            "id": self.id,
            "challenge_id": self.challenge_id,
            "challenge_title": self.challenge_title,
            "time_left": self.time_left,
            "algorithm": self.algorithm,
            "strategy_description": self.strategy_description,
            "success": self.success,
            "photo1": {
                "id": self.photo1_id,
                "ratio": self.photo1_ratio,
                "votes": self.photo1_votes,
                "rank": self.photo1_rank,
                "found": self.photo1_found
            },
            "photo2": {
                "id": self.photo2_id,
                "ratio": self.photo2_ratio,
                "votes": self.photo2_votes,
                "rank": self.photo2_rank,
                "found": self.photo2_found
            },
            "winner": {
                "id": self.winner_id,
                "is_photo1": self.is_photo1_winner
            },
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class TurboAlgorithmStats(Base):
    """
    Statistiques des algorithmes turbo par utilisateur
    Pour l'auto-optimisation
    """
    __tablename__ = "turbo_algorithm_stats"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    algorithm = Column(String(50), nullable=False)
    
    # Statistiques
    total_comparisons = Column(Integer, default=0)
    successful_comparisons = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    
    # Dernière utilisation
    last_used = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    user = relationship("User")
    
    def __repr__(self):
        return f"<TurboAlgorithmStats(algorithm='{self.algorithm}', success_rate={self.success_rate:.2f})>"
    
    def update_stats(self, success: bool):
        """Met à jour les statistiques après une comparaison"""
        self.total_comparisons += 1
        if success:
            self.successful_comparisons += 1
        
        self.success_rate = (
            self.successful_comparisons / self.total_comparisons 
            if self.total_comparisons > 0 else 0.0
        )
        self.last_used = datetime.utcnow()
        self.updated_at = datetime.utcnow()