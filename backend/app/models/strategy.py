"""
Strategy models - Basé sur le système de stratégies de gsui.py
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

Base = declarative_base()


class StrategyStatus(str, Enum):
    """États possibles d'une stratégie"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StrategyAction(str, Enum):
    """Actions possibles dans une stratégie"""
    VOTE = "vote"
    WAIT = "wait"
    TURBO = "turbo"


class Strategy(Base):
    """
    Modèle de stratégie - Basé sur le système de stratégies dans gsui.py
    """
    __tablename__ = "strategies"
    
    # Identifiants
    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # Références
    challenge_id = Column(String, ForeignKey("challenges.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Configuration de la stratégie
    strategy_config = Column(JSON)  # Configuration complète de strategies.ini
    
    # État d'exécution
    status = Column(String(20), default=StrategyStatus.PENDING)
    scheduled_at = Column(DateTime, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Progression
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    
    # Résultats
    votes_executed = Column(Integer, default=0)
    votes_planned = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    
    # Logs et erreurs
    execution_log = Column(JSON, default=list)  # Log des actions exécutées
    last_error = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    challenge = relationship("Challenge", back_populates="strategies")
    user = relationship("User", back_populates="strategies")
    
    def __repr__(self):
        return f"<Strategy(id='{self.id}', name='{self.name}', status='{self.status}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour l'API"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "challenge_id": self.challenge_id,
            "user_id": self.user_id,
            "status": self.status,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "votes_executed": self.votes_executed,
            "votes_planned": self.votes_planned,
            "success_rate": self.success_rate,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class StrategyStep(Base):
    """
    Étapes individuelles d'une stratégie
    Basé sur la configuration de strategies.ini
    """
    __tablename__ = "strategy_steps"
    
    id = Column(String, primary_key=True)
    strategy_id = Column(String, ForeignKey("strategies.id"), nullable=False)
    
    # Configuration de l'étape
    step_number = Column(Integer, nullable=False)
    action = Column(String(20), nullable=False)  # vote, wait, turbo
    timing = Column(String(100))  # "end-2m0s", "now", etc.
    vote_count = Column(Integer, default=0)
    
    # État d'exécution
    status = Column(String(20), default="pending")
    scheduled_at = Column(DateTime)
    executed_at = Column(DateTime)
    
    # Résultat
    success = Column(Boolean)
    result_data = Column(JSON)
    error_message = Column(Text)
    
    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    strategy = relationship("Strategy")
    
    def __repr__(self):
        return f"<StrategyStep(id='{self.id}', step_number={self.step_number}, action='{self.action}')>"