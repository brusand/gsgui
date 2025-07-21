"""
Strategy Scheduler Service - Basé sur le système de scheduling de gsui.py
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
import uuid
import re

from app.services.gurushots_api import GuruShotsAPI
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class StrategyAction:
    """Action à exécuter dans une stratégie"""
    action_type: str  # "vote", "wait", "turbo"
    timing: str       # "end-2m0s", "now", "next-1m0s"
    vote_count: int   # Nombre de votes (si action_type == "vote")
    step_number: int  # Numéro d'étape dans la stratégie


@dataclass
class StrategyExecution:
    """Contexte d'exécution d'une stratégie"""
    strategy_id: str
    user_id: str
    user_token: str
    challenge_id: str
    challenge_url: str
    challenge_end_time: datetime
    actions: List[StrategyAction]
    current_step: int = 0


class StrategyScheduler:
    """
    Gestionnaire de scheduling des stratégies
    Basé sur le système APScheduler de gsui.py
    """
    
    def __init__(self):
        # Configuration du scheduler comme dans gsui.py
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=settings.SCHEDULER_TIMEZONE
        )
        
        # Stratégies actives
        self.active_strategies: Dict[str, StrategyExecution] = {}
        
        # Callbacks pour les événements
        self.on_strategy_start: Optional[Callable] = None
        self.on_strategy_step: Optional[Callable] = None
        self.on_strategy_complete: Optional[Callable] = None
        self.on_strategy_error: Optional[Callable] = None
        
        logger.info("✅ Strategy Scheduler initialized")
    
    def start(self):
        """Démarre le scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("🚀 Strategy Scheduler started")
    
    def shutdown(self):
        """Arrête le scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("⛔ Strategy Scheduler stopped")
    
    async def schedule_strategy(
        self,
        strategy_id: str,
        user_id: str,
        user_token: str,
        challenge_id: str,
        challenge_url: str,
        challenge_end_time: datetime,
        strategy_config: Dict[str, Any]
    ) -> bool:
        """
        Programme l'exécution d'une stratégie
        Basé sur la logique de strategies.ini
        """
        try:
            # Parser la configuration de stratégie
            actions = self._parse_strategy_config(strategy_config)
            
            if not actions:
                logger.error(f"No valid actions found in strategy {strategy_id}")
                return False
            
            # Créer le contexte d'exécution
            strategy_execution = StrategyExecution(
                strategy_id=strategy_id,
                user_id=user_id,
                user_token=user_token,
                challenge_id=challenge_id,
                challenge_url=challenge_url,
                challenge_end_time=challenge_end_time,
                actions=actions
            )
            
            # Stocker la stratégie
            self.active_strategies[strategy_id] = strategy_execution
            
            # Programmer la première étape
            first_action = actions[0]
            execution_time = self._calculate_execution_time(
                first_action.timing, 
                challenge_end_time
            )
            
            if execution_time:
                self.scheduler.add_job(
                    func=self._execute_strategy_step,
                    trigger=DateTrigger(run_date=execution_time),
                    args=[strategy_id, 0],
                    id=f"{strategy_id}_step_0",
                    replace_existing=True
                )
                
                logger.info(f"✅ Strategy {strategy_id} scheduled to start at {execution_time}")
                return True
            else:
                logger.error(f"Failed to calculate execution time for strategy {strategy_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error scheduling strategy {strategy_id}: {e}")
            return False
    
    def _parse_strategy_config(self, config: Dict[str, Any]) -> List[StrategyAction]:
        """
        Parse la configuration de stratégie depuis strategies.ini
        Format: {"0": "vote, end-2m0s, 80", "1": "vote, end-1m0s, 40", ...}
        """
        actions = []
        
        try:
            for key, value in config.items():
                if key == "description":
                    continue
                
                try:
                    step_number = int(key)
                    parts = [p.strip() for p in value.split(',')]
                    
                    if len(parts) >= 2:
                        action_type = parts[0].lower()
                        timing = parts[1]
                        vote_count = int(parts[2]) if len(parts) > 2 and parts[2].strip() else 0
                        
                        # Ignorer les actions avec vote_count = -1 (désactivées)
                        if vote_count == -1:
                            continue
                        
                        action = StrategyAction(
                            action_type=action_type,
                            timing=timing,
                            vote_count=vote_count,
                            step_number=step_number
                        )
                        
                        actions.append(action)
                        
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse strategy step {key}: {value} - {e}")
                    continue
            
            # Trier par numéro d'étape
            actions.sort(key=lambda x: x.step_number)
            logger.info(f"Parsed {len(actions)} strategy actions")
            return actions
            
        except Exception as e:
            logger.error(f"Error parsing strategy config: {e}")
            return []
    
    def _calculate_execution_time(self, timing: str, challenge_end_time: datetime) -> Optional[datetime]:
        """
        Calcule le moment d'exécution basé sur le timing
        Formats supportés: "end-2m0s", "now", "next-1m0s"
        """
        try:
            timing = timing.strip()
            
            if timing.lower() == "now":
                return datetime.now()
            
            # Pattern pour "end-2m0s" ou "end-2m"
            end_pattern = r"end-(\d+)([dhms])(\d+)?([dhms])?"
            match = re.match(end_pattern, timing.lower())
            
            if match:
                # Parser les composants temporels
                total_offset = timedelta()
                
                # Premier composant (obligatoire)
                value1 = int(match.group(1))
                unit1 = match.group(2)
                
                if unit1 == 'd':
                    total_offset += timedelta(days=value1)
                elif unit1 == 'h':
                    total_offset += timedelta(hours=value1)
                elif unit1 == 'm':
                    total_offset += timedelta(minutes=value1)
                elif unit1 == 's':
                    total_offset += timedelta(seconds=value1)
                
                # Deuxième composant (optionnel)
                if match.group(3) and match.group(4):
                    value2 = int(match.group(3))
                    unit2 = match.group(4)
                    
                    if unit2 == 'd':
                        total_offset += timedelta(days=value2)
                    elif unit2 == 'h':
                        total_offset += timedelta(hours=value2)
                    elif unit2 == 'm':
                        total_offset += timedelta(minutes=value2)
                    elif unit2 == 's':
                        total_offset += timedelta(seconds=value2)
                
                # Calculer le moment d'exécution
                execution_time = challenge_end_time - total_offset
                
                # Ne pas programmer dans le passé
                if execution_time <= datetime.now():
                    logger.warning(f"Execution time {execution_time} is in the past for timing {timing}")
                    return datetime.now() + timedelta(seconds=5)  # Exécuter dans 5 secondes
                
                return execution_time
            
            # Pattern pour "next-1m0s"
            next_pattern = r"next-(\d+)([dhms])(\d+)?([dhms])?"
            match = re.match(next_pattern, timing.lower())
            
            if match:
                # Parser comme pour "end-" mais ajouter à maintenant
                total_offset = timedelta()
                
                value1 = int(match.group(1))
                unit1 = match.group(2)
                
                if unit1 == 'd':
                    total_offset += timedelta(days=value1)
                elif unit1 == 'h':
                    total_offset += timedelta(hours=value1)
                elif unit1 == 'm':
                    total_offset += timedelta(minutes=value1)
                elif unit1 == 's':
                    total_offset += timedelta(seconds=value1)
                
                if match.group(3) and match.group(4):
                    value2 = int(match.group(3))
                    unit2 = match.group(4)
                    
                    if unit2 == 'd':
                        total_offset += timedelta(days=value2)
                    elif unit2 == 'h':
                        total_offset += timedelta(hours=value2)
                    elif unit2 == 'm':
                        total_offset += timedelta(minutes=value2)
                    elif unit2 == 's':
                        total_offset += timedelta(seconds=value2)
                
                return datetime.now() + total_offset
            
            logger.error(f"Unsupported timing format: {timing}")
            return None
            
        except Exception as e:
            logger.error(f"Error calculating execution time for timing '{timing}': {e}")
            return None
    
    async def _execute_strategy_step(self, strategy_id: str, step_number: int):
        """
        Exécute une étape de stratégie
        """
        try:
            strategy = self.active_strategies.get(strategy_id)
            if not strategy:
                logger.error(f"Strategy {strategy_id} not found")
                return
            
            if step_number >= len(strategy.actions):
                logger.error(f"Step {step_number} out of range for strategy {strategy_id}")
                return
            
            action = strategy.actions[step_number]
            logger.info(f"Executing strategy {strategy_id} step {step_number}: {action.action_type}")
            
            # Callback de début d'étape
            if self.on_strategy_step:
                await self.on_strategy_step(strategy_id, step_number, action)
            
            # Créer le client API
            api_client = GuruShotsAPI(strategy.user_token)
            
            success = False
            
            # Exécuter l'action
            if action.action_type == "vote":
                result = await api_client.execute_simple_vote(
                    strategy.challenge_url,
                    action.vote_count
                )
                success = result.success
                
                if success:
                    logger.info(f"✅ Vote executed: {action.vote_count} votes")
                else:
                    logger.error(f"❌ Vote failed: {result.message}")
            
            elif action.action_type == "wait":
                # Wait action - ne rien faire, juste logger
                logger.info(f"⏳ Wait action executed")
                success = True
            
            elif action.action_type == "turbo":
                # TODO: Implémenter l'action turbo
                logger.info(f"🚀 Turbo action - not implemented yet")
                success = True
            
            # Mettre à jour le contexte
            strategy.current_step = step_number + 1
            
            # Programmer la prochaine étape si elle existe
            if step_number + 1 < len(strategy.actions):
                next_action = strategy.actions[step_number + 1]
                execution_time = self._calculate_execution_time(
                    next_action.timing,
                    strategy.challenge_end_time
                )
                
                if execution_time:
                    self.scheduler.add_job(
                        func=self._execute_strategy_step,
                        trigger=DateTrigger(run_date=execution_time),
                        args=[strategy_id, step_number + 1],
                        id=f"{strategy_id}_step_{step_number + 1}",
                        replace_existing=True
                    )
                    
                    logger.info(f"Next step scheduled for {execution_time}")
            else:
                # Stratégie terminée
                logger.info(f"✅ Strategy {strategy_id} completed")
                
                if self.on_strategy_complete:
                    await self.on_strategy_complete(strategy_id, success)
                
                # Nettoyer
                del self.active_strategies[strategy_id]
            
        except Exception as e:
            logger.error(f"Error executing strategy step {strategy_id}:{step_number}: {e}")
            
            if self.on_strategy_error:
                await self.on_strategy_error(strategy_id, step_number, str(e))
    
    async def cancel_strategy(self, strategy_id: str) -> bool:
        """Annule une stratégie en cours"""
        try:
            # Supprimer tous les jobs programmés pour cette stratégie
            jobs = self.scheduler.get_jobs()
            for job in jobs:
                if job.id.startswith(f"{strategy_id}_"):
                    job.remove()
            
            # Supprimer de la liste active
            if strategy_id in self.active_strategies:
                del self.active_strategies[strategy_id]
            
            logger.info(f"✅ Strategy {strategy_id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling strategy {strategy_id}: {e}")
            return False
    
    def get_active_strategies(self) -> List[Dict[str, Any]]:
        """Retourne la liste des stratégies actives"""
        strategies = []
        
        for strategy_id, strategy in self.active_strategies.items():
            strategies.append({
                "strategy_id": strategy_id,
                "user_id": strategy.user_id,
                "challenge_id": strategy.challenge_id,
                "current_step": strategy.current_step,
                "total_steps": len(strategy.actions),
                "next_action": strategy.actions[strategy.current_step] if strategy.current_step < len(strategy.actions) else None
            })
        
        return strategies
    
    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Retourne la liste des jobs programmés"""
        jobs = []
        
        for job in self.scheduler.get_jobs():
            jobs.append({
                "job_id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return jobs


# Instance globale du scheduler
strategy_scheduler = StrategyScheduler()