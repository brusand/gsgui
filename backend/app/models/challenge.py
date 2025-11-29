"""
Challenge models - Extrait et adapté de GurushotChallenge dans gsui.py
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, Dict, Any

Base = declarative_base()


class Challenge(Base):
    """
    Modèle de challenge GuruShots
    Basé sur la classe GurushotChallenge de gsui.py
    """
    __tablename__ = "challenges"
    
    # Identifiants
    id = Column(String, primary_key=True)  # ID GuruShots
    title = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    
    # Timing
    end_time = Column(DateTime, nullable=False)
    close_time = Column(DateTime, nullable=False)
    time_left_days = Column(Integer, default=0)
    time_left_hours = Column(Integer, default=0) 
    time_left_minutes = Column(Integer, default=0)
    time_left_seconds = Column(Integer, default=0)
    
    # Statistiques utilisateur
    votes = Column(Integer, default=0)
    rank = Column(Integer, default=0)
    level = Column(String(50))
    exposure = Column(Integer, default=0)
    gps = Column(Integer, default=0)
    
    # État et stratégie
    selected_strategy = Column(String(100))
    status = Column(String(50), default="")  # "", "active", "completed", "failed"
    turbo_status = Column(String(50), default="")  # "", "success", "failed"
    boost_status = Column(String(50), default="")  # "", "locked", "boosting", "boosted", "missed", "3H", "15M",..."
    # Processus en cours
    current_process_id = Column(String(255))
    process_start_time = Column(DateTime)
    
    # Données GuruShots complètes (JSON)
    challenge_data = Column(JSON)  # Stockage des données complètes de l'API
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Relations
    user = relationship("User", back_populates="challenges")
    strategies = relationship("Strategy", back_populates="challenge")
    turbo_history = relationship("TurboHistory", back_populates="challenge")
    
    def __repr__(self):
        return f"<Challenge(id='{self.id}', title='{self.title}', status='{self.status}')>"
    
    @property
    def time_left_formatted(self) -> str:
        """Format le temps restant comme dans gsui.py"""
        return f"{self.time_left_days}D {self.time_left_hours}H {self.time_left_minutes}M {self.time_left_seconds}S"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour l'API"""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "time_left": self.time_left_formatted,
            "votes": self.votes,
            "rank": self.rank,
            "level": self.level,
            "exposure": self.exposure,
            "gps": self.gps,
            "selected_strategy": self.selected_strategy,
            "status": self.status,
            "turbo_status": self.turbo_status,
            "boost_status": self.boost_status,
            "current_process_id": self.current_process_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class User(Base):
    """
    Modèle utilisateur - Basé sur la configuration des profils de gsui.py
    """
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255))
    
    # Authentification GuruShots
    xtoken = Column(String(500), nullable=False)  # Token GuruShots
    user_name = Column(String(100))  # Nom utilisateur GuruShots
    
    # Configuration Turbo
    turbo_algorithm = Column(String(50), default="hybrid")
    auto_optimize_turbo = Column(Boolean, default=True)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Relations
    challenges = relationship("Challenge", back_populates="user")
    strategies = relationship("Strategy", back_populates="user")
    turbo_history = relationship("TurboHistory", back_populates="user")
    
    def __repr__(self):
        return f"<User(id='{self.id}', username='{self.username}')>"