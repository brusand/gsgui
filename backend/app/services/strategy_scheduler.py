"""
Strategy Scheduler Service - APScheduler integration for strategy execution
Migration from gsui.py scheduled strategies system
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from app.services.config_manager import config_manager
from app.services.gurushots_api import GuruShotsAPI
# from app.websockets.connection_manager import connection_manager  # Désactivé pour backend monolithique

logger = logging.getLogger(__name__)


class StrategyScheduler:
    """
    Gestionnaire de programmation des stratégies
    Équivalent de la logique APScheduler dans gsui.py
    """
    
    def __init__(self):
        # Configuration APScheduler optimisée pour la précision
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()  # AsyncIOExecutor ne prend pas max_workers
        }
        job_defaults = {
            'coalesce': True,      # Fusionner les jobs en retard
            'max_instances': 1,    # Une seule instance par job pour éviter doublons
            'misfire_grace_time': 5  # Tolérance de 5s pour les jobs en retard
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'  # UTC pour éviter problèmes timezone
        )
        
        # Configuration précision
        self.scheduler.configure(
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 5
            }
        )
        
        self._running = False
        logger.info("📅 StrategyScheduler initialized")
    
    async def start(self):
        """Démarre le scheduler avec optimisations de précision"""
        if not self._running:
            self.scheduler.start()
            self._running = True
            
            # Log de la précision
            import time
            start_time = time.time()
            logger.info(f"🚀 StrategyScheduler started at {datetime.now().isoformat()}")
            logger.info(f"⏱️ Scheduler precision: misfire_grace_time=5s, coalesce=True")
            
            # Ajouter un job de test de précision toutes les minutes
            self.scheduler.add_job(
                func=self._precision_test_job,
                trigger='interval',
                minutes=1,
                id='precision_test',
                name='Precision Test Job',
                replace_existing=True
            )
            
            # Ajouter un job de nettoyage des jobs expirés toutes les 30 minutes
            self.scheduler.add_job(
                func=self._cleanup_expired_jobs,
                trigger='interval',
                minutes=30,
                id='cleanup_expired_jobs',
                name='Cleanup Expired Jobs',
                replace_existing=True
            )
            
            # Restaurer les stratégies programmées au démarrage
            await self._restore_scheduled_strategies()
    
    def _precision_test_job(self):
        """Job de test de précision - log l'heure exacte d'exécution"""
        actual_time = datetime.now()
        expected_time = actual_time.replace(second=0, microsecond=0)
        delay = (actual_time - expected_time).total_seconds()
        
        if delay > 2:  # Plus de 2s de retard
            logger.warning(f"⚠️ APScheduler delay detected: {delay:.2f}s at {actual_time.strftime('%H:%M:%S.%f')}")
        else:
            logger.debug(f"✅ APScheduler precision OK: {delay:.2f}s delay at {actual_time.strftime('%H:%M:%S.%f')}")
    
    def _cleanup_expired_jobs(self):
        """Nettoie les jobs expirés d'APScheduler"""
        try:
            from datetime import timezone
            now = datetime.now(timezone.utc)  # UTC pour correspondre à APScheduler
            
            def safe_datetime_compare(job_time, reference_time):
                """Safely compare datetimes, handling timezone issues"""
                if job_time is None:
                    return False
                try:
                    # Ensure both datetimes have timezone info
                    if job_time.tzinfo is None:
                        job_time = job_time.replace(tzinfo=timezone.utc)
                    if reference_time.tzinfo is None:
                        reference_time = reference_time.replace(tzinfo=timezone.utc)
                    return job_time < reference_time
                except Exception:
                    return False
            
            jobs = self.scheduler.get_jobs()
            cleaned_count = 0
            
            for job in jobs:
                # Ne pas supprimer les jobs système (precision test, cleanup)
                if job.id in ['precision_test', 'cleanup_expired_jobs']:
                    continue
                
                # Ne pas supprimer les jobs unlock_boost récurrents (ils se reprogramment)
                if 'unlock_boost' in job.id:
                    logger.debug(f"🔒 Preserving unlock_boost job: {job.id}")
                    continue
                
                # Supprimer les jobs programmés dans le passé (mais pas exécutés à cause d'un redémarrage)
                if safe_datetime_compare(job.next_run_time, now - timedelta(hours=1)):
                    try:
                        self.scheduler.remove_job(job.id)
                        cleaned_count += 1
                        logger.debug(f"🧹 Cleaned expired job: {job.id} (was scheduled for {job.next_run_time})")
                    except Exception as e:
                        logger.error(f"Error cleaning job {job.id}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"🧹 Cleaned {cleaned_count} expired jobs from APScheduler")
            else:
                logger.debug("🧹 No expired jobs to clean")
                
        except Exception as e:
            logger.error(f"Error during job cleanup: {e}")
    
    async def stop(self):
        """Arrête le scheduler"""
        if self._running:
            self.scheduler.shutdown()
            self._running = False
            logger.info("🛑 StrategyScheduler stopped")
    
    async def _restore_scheduled_strategies(self):
        """
        Restaure les stratégies programmées depuis la configuration
        Équivalent de load_and_restore_scheduled_strategies() dans gsui.py
        """
        try:
            logger.info("🔄 Restoring scheduled strategies from config...")
            
            # Récupérer tous les utilisateurs
            user_ids = config_manager.list_users()
            
            restored_count = 0
            for user_id in user_ids:
                try:
                    # Récupérer les stratégies programmées de cet utilisateur
                    scheduled_strategies = config_manager.get_user_section(user_id, 'scheduled_strategies') or {}
                    
                    for strategy_id, strategy_data in scheduled_strategies.items():
                        try:
                            # Vérifier si la stratégie est encore pertinente
                            scheduled_at = datetime.fromisoformat(strategy_data.get('scheduled_at', ''))
                            status = strategy_data.get('status', 'pending')
                            
                            # Ne restaurer que les stratégies en attente et futures
                            # Normaliser les datetimes pour éviter les problèmes de timezone
                            now = datetime.now()
                            if scheduled_at.tzinfo is not None:
                                from datetime import timezone
                                now = now.replace(tzinfo=timezone.utc)
                            elif now.tzinfo is not None:
                                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
                                
                            if status == 'pending' and scheduled_at > now:
                                await self._schedule_strategy_job(
                                    profile_id=user_id,
                                    strategy_id=strategy_id,
                                    strategy_data=strategy_data
                                )
                                restored_count += 1
                                logger.debug(f"✅ Restored strategy {strategy_id} for {user_id}")
                            
                            elif scheduled_at <= now and status == 'pending':
                                # Marquer comme expirée
                                strategy_data['status'] = 'expired'
                                strategy_data['updated_at'] = datetime.now().isoformat()
                                scheduled_strategies[strategy_id] = strategy_data
                                config_manager.update_user_section(user_id, 'scheduled_strategies', scheduled_strategies)
                                logger.info(f"⏰ Marked expired strategy {strategy_id} for {user_id}")
                        
                        except Exception as e:
                            logger.error(f"Error restoring strategy {strategy_id} for {user_id}: {e}")
                            continue
                
                except Exception as e:
                    logger.error(f"Error processing strategies for user {user_id}: {e}")
                    continue
            
            logger.info(f"✅ Restored {restored_count} scheduled strategies")
            
        except Exception as e:
            logger.error(f"Error restoring scheduled strategies: {e}")
    
    async def schedule_strategy(self, profile_id: str, strategy_id: str, strategy_data: Dict[str, Any]):
        """
        Programme l'exécution d'une stratégie
        """
        try:
            logger.info(f"📅 Scheduling strategy {strategy_id} for profile {profile_id}")
            
            await self._schedule_strategy_job(profile_id, strategy_id, strategy_data)
            
        except Exception as e:
            logger.error(f"Error scheduling strategy {strategy_id}: {e}")
            raise
    
    async def _schedule_strategy_job(self, profile_id: str, strategy_id: str, strategy_data: Dict[str, Any]):
        """Crée la tâche APScheduler pour une stratégie"""
        try:
            scheduled_at = datetime.fromisoformat(strategy_data.get('scheduled_at', ''))
            challenge_id = strategy_data.get('challenge_id', '')
            strategy_name = strategy_data.get('strategy_name', '')
            
            # Créer le job APScheduler
            job_id = f"{profile_id}_{strategy_id}"
            
            self.scheduler.add_job(
                func=self._execute_strategy,
                trigger=DateTrigger(run_date=scheduled_at),
                args=[profile_id, strategy_id, challenge_id, strategy_name],
                id=job_id,
                name=f"Strategy {strategy_name} for {challenge_id}",
                replace_existing=True,
                # Optimisations précision
                coalesce=True,
                max_instances=1,
                misfire_grace_time=5
            )
            
            logger.info(f"✅ Scheduled job {job_id} for {scheduled_at}")
            
        except Exception as e:
            logger.error(f"Error creating scheduler job: {e}")
            raise
    
    async def reschedule_strategy(self, profile_id: str, strategy_id: str, new_schedule_time: datetime):
        """Re-programme une stratégie existante"""
        try:
            job_id = f"{profile_id}_{strategy_id}"
            
            # Modifier le job existant
            self.scheduler.modify_job(
                job_id=job_id,
                trigger=DateTrigger(run_date=new_schedule_time)
            )
            
            logger.info(f"✅ Rescheduled job {job_id} to {new_schedule_time}")
            
        except Exception as e:
            logger.error(f"Error rescheduling strategy {strategy_id}: {e}")
            raise
    
    async def cancel_strategy(self, profile_id: str, strategy_id: str):
        """Annule une stratégie programmée"""
        try:
            job_id = f"{profile_id}_{strategy_id}"
            
            # Supprimer le job
            self.scheduler.remove_job(job_id)
            
            logger.info(f"✅ Cancelled job {job_id}")
            
        except Exception as e:
            logger.warning(f"Error cancelling strategy {strategy_id}: {e}")
            # Ne pas lever d'exception si le job n'existe pas
    
    async def _execute_strategy(self, profile_id: str, strategy_id: str, challenge_id: str, strategy_name: str):
        """
        Exécute une stratégie programmée
        Équivalent de schedule_multiple_votes() dans gsui.py
        """
        logger.info(f"🚀 Executing strategy {strategy_name} for challenge {challenge_id} (profile: {profile_id})")
        
        execution_start = datetime.now()
        success = False
        votes_cast = 0
        error_message = None
        result_data = {}
        
        try:
            # Mettre à jour le statut à 'running'
            await self._update_strategy_status(profile_id, strategy_id, 'running')
            
            # Récupérer les informations utilisateur
            user = config_manager.get_user(profile_id)
            if not user:
                raise Exception(f"Profile {profile_id} not found")
            
            xtoken = user.get('xtoken')
            if not xtoken:
                raise Exception(f"No xtoken found for profile {profile_id}")
            
            # Créer le client API GuruShots
            api_client = GuruShotsAPI(xtoken)
            
            # Exécuter la stratégie selon son type
            if strategy_name == '4m':
                result = await self._execute_4m_strategy(api_client, challenge_id)
            elif strategy_name == 'fill':
                result = await self._execute_fill_strategy(api_client, challenge_id)
            elif strategy_name == 'boost':
                result = await self._execute_boost_strategy(api_client, challenge_id)
            elif strategy_name == 'swap':
                result = await self._execute_swap_strategy(api_client, challenge_id)
            else:
                raise Exception(f"Unknown strategy type: {strategy_name}")
            
            success = result.get('success', False)
            votes_cast = result.get('votes_cast', 0)
            result_data = result.get('result_data', {})
            
            # Mettre à jour le statut final
            final_status = 'completed' if success else 'failed'
            await self._update_strategy_status(profile_id, strategy_id, final_status)
            
            logger.info(f"✅ Strategy execution completed: {votes_cast} votes cast, success: {success}")
            
        except Exception as e:
            error_message = str(e)
            success = False
            await self._update_strategy_status(profile_id, strategy_id, 'failed')
            logger.error(f"❌ Strategy execution failed: {error_message}")
        
        finally:
            execution_end = datetime.now()
            
            # Créer le résultat d'exécution
            execution_result = {
                'strategy_id': strategy_id,
                'challenge_id': challenge_id,
                'strategy_name': strategy_name,
                'execution_started_at': execution_start.isoformat(),
                'execution_completed_at': execution_end.isoformat(),
                'success': success,
                'votes_cast': votes_cast,
                'error_message': error_message,
                'result_data': result_data
            }
            
            # Notifier via WebSocket
            await connection_manager.notify_strategy_executed(profile_id, execution_result)
    
    async def _update_strategy_status(self, profile_id: str, strategy_id: str, new_status: str):
        """Met à jour le statut d'une stratégie dans la configuration"""
        try:
            scheduled_strategies = config_manager.get_user_section(profile_id, 'scheduled_strategies') or {}
            
            if strategy_id in scheduled_strategies:
                old_status = scheduled_strategies[strategy_id].get('status', 'pending')
                scheduled_strategies[strategy_id]['status'] = new_status
                scheduled_strategies[strategy_id]['updated_at'] = datetime.now().isoformat()
                
                config_manager.update_user_section(profile_id, 'scheduled_strategies', scheduled_strategies)
                
                # Notifier le changement de statut
                await connection_manager.notify_strategy_status_changed(
                    profile_id, strategy_id, old_status, new_status
                )
            
        except Exception as e:
            logger.error(f"Error updating strategy status: {e}")
    
    async def _execute_4m_strategy(self, api_client: GuruShotsAPI, challenge_id: str) -> Dict[str, Any]:
        """
        Exécute la stratégie '4m' - vote toutes les 4 minutes
        """
        logger.info(f"⏰ Executing 4m strategy for challenge {challenge_id}")
        
        total_votes = 0
        challenge_url = f"https://gurushots.com/challenge/{challenge_id}"
        
        try:
            # Récupérer les informations du challenge pour connaître le temps restant
            vote_panel = await api_client.get_vote_panel(challenge_url, limit=50)
            
            if not vote_panel.success:
                return {'success': False, 'votes_cast': 0, 'error': 'Could not get vote panel'}
            
            # Calculer combien de cycles de 4 minutes on peut faire
            # Pour simplifier, on fait juste un vote pour cette implémentation
            vote_result = await api_client.execute_simple_vote(challenge_url, vote_count=10)
            
            if vote_result.success:
                total_votes = 10  # Nombre de votes cast
                
            return {
                'success': vote_result.success,
                'votes_cast': total_votes,
                'result_data': vote_result.result_data
            }
            
        except Exception as e:
            logger.error(f"Error in 4m strategy: {e}")
            return {'success': False, 'votes_cast': total_votes, 'error': str(e)}
    
    async def _execute_fill_strategy(self, api_client: GuruShotsAPI, challenge_id: str) -> Dict[str, Any]:
        """
        Exécute la stratégie 'fill' - utilise tous les votes restants
        """
        logger.info(f"🔄 Executing fill strategy for challenge {challenge_id}")
        
        challenge_url = f"https://gurushots.com/challenge/{challenge_id}"
        
        try:
            # Utiliser tous les votes disponibles (max 80 par défaut dans gsui.py)
            vote_result = await api_client.execute_simple_vote(challenge_url, vote_count=80)
            
            votes_cast = 80 if vote_result.success else 0
            
            return {
                'success': vote_result.success,
                'votes_cast': votes_cast,
                'result_data': vote_result.result_data
            }
            
        except Exception as e:
            logger.error(f"Error in fill strategy: {e}")
            return {'success': False, 'votes_cast': 0, 'error': str(e)}
    
    async def _execute_boost_strategy(self, api_client: GuruShotsAPI, challenge_id: str) -> Dict[str, Any]:
        """
        Exécute la stratégie 'boost' - boost optimisé
        """
        logger.info(f"⚡ Executing boost strategy for challenge {challenge_id}")
        
        # Pour l'instant, implémentation simple
        challenge_url = f"https://gurushots.com/challenge/{challenge_id}"
        
        try:
            vote_result = await api_client.execute_simple_vote(challenge_url, vote_count=20)
            
            votes_cast = 20 if vote_result.success else 0
            
            return {
                'success': vote_result.success,
                'votes_cast': votes_cast,
                'result_data': vote_result.result_data
            }
            
        except Exception as e:
            logger.error(f"Error in boost strategy: {e}")
            return {'success': False, 'votes_cast': 0, 'error': str(e)}
    
    async def _execute_swap_strategy(self, api_client: GuruShotsAPI, challenge_id: str) -> Dict[str, Any]:
        """
        Exécute la stratégie 'swap' - échange de photos stratégique
        """
        logger.info(f"🔄 Executing swap strategy for challenge {challenge_id}")
        
        # Pour l'instant, implémentation basique
        challenge_url = f"https://gurushots.com/challenge/{challenge_id}"
        
        try:
            vote_result = await api_client.execute_simple_vote(challenge_url, vote_count=15)
            
            votes_cast = 15 if vote_result.success else 0
            
            return {
                'success': vote_result.success,
                'votes_cast': votes_cast,
                'result_data': vote_result.result_data
            }
            
        except Exception as e:
            logger.error(f"Error in swap strategy: {e}")
            return {'success': False, 'votes_cast': 0, 'error': str(e)}
    
    def cleanup_expired_jobs(self) -> Dict[str, Any]:
        """
        Nettoie manuellement les jobs expirés - méthode publique pour l'API
        """
        try:
            from datetime import timezone
            now = datetime.now(timezone.utc)  # UTC pour correspondre à APScheduler
            
            def safe_datetime_compare(job_time, reference_time):
                """Safely compare datetimes, handling timezone issues"""
                if job_time is None:
                    return False
                try:
                    # Ensure both datetimes have timezone info
                    if job_time.tzinfo is None:
                        job_time = job_time.replace(tzinfo=timezone.utc)
                    if reference_time.tzinfo is None:
                        reference_time = reference_time.replace(tzinfo=timezone.utc)
                    return job_time < reference_time
                except Exception:
                    return False
            
            jobs = self.scheduler.get_jobs()
            cleaned_jobs = []
            
            for job in jobs:
                # Ne pas supprimer les jobs système
                if job.id in ['precision_test', 'cleanup_expired_jobs']:
                    continue
                
                # Ne pas supprimer les jobs unlock_boost récurrents (ils se reprogramment)
                if 'unlock_boost' in job.id:
                    logger.debug(f"🔒 Preserving unlock_boost job: {job.id}")
                    continue
                
                # Supprimer les jobs expirés (plus d'1h dans le passé)
                if safe_datetime_compare(job.next_run_time, now - timedelta(hours=1)):
                    try:
                        self.scheduler.remove_job(job.id)
                        cleaned_jobs.append({
                            'job_id': job.id,
                            'name': job.name,
                            'next_run_time': job.next_run_time.isoformat(),
                            'expired_hours': (now - job.next_run_time).total_seconds() / 3600
                        })
                        logger.info(f"🧹 Manually cleaned expired job: {job.id}")
                    except Exception as e:
                        logger.error(f"Error manually cleaning job {job.id}: {e}")
            
            return {
                'success': True,
                'cleaned_count': len(cleaned_jobs),
                'cleaned_jobs': cleaned_jobs,
                'remaining_jobs': len(self.scheduler.get_jobs()),
                'cleanup_timestamp': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error during manual job cleanup: {e}")
            return {
                'success': False,
                'error': str(e),
                'cleaned_count': 0
            }
    
    def get_jobs(self):
        """Expose get_jobs method from scheduler for backward compatibility"""
        return self.scheduler.get_jobs()
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """
        Retourne le statut du scheduler avec compteurs de jobs
        """
        try:
            from datetime import timezone
            jobs = self.scheduler.get_jobs()
            now = datetime.now(timezone.utc)  # UTC pour correspondre à APScheduler
            
            def safe_datetime_compare(job_time, reference_time):
                """Safely compare datetimes, handling timezone issues"""
                if job_time is None:
                    return False
                try:
                    # Ensure both datetimes have timezone info
                    if job_time.tzinfo is None:
                        job_time = job_time.replace(tzinfo=timezone.utc)
                    if reference_time.tzinfo is None:
                        reference_time = reference_time.replace(tzinfo=timezone.utc)
                    return job_time < reference_time
                except Exception:
                    return False
            
            active_jobs = []
            expired_jobs = []
            system_jobs = []
            
            for job in jobs:
                job_info = {
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                }
                
                if job.id in ['precision_test', 'cleanup_expired_jobs']:
                    system_jobs.append(job_info)
                elif 'unlock_boost' in job.id:
                    # Toujours considérer les unlock_boost comme actifs
                    active_jobs.append(job_info)
                elif safe_datetime_compare(job.next_run_time, now - timedelta(hours=1)):
                    expired_jobs.append(job_info)
                else:
                    active_jobs.append(job_info)
            
            return {
                'scheduler_running': self._running,
                'total_jobs': len(jobs),
                'active_jobs': len(active_jobs),
                'expired_jobs': len(expired_jobs),
                'system_jobs': len(system_jobs),
                'jobs': {
                    'active': active_jobs,
                    'expired': expired_jobs,
                    'system': system_jobs
                },
                'status_timestamp': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {
                'scheduler_running': self._running,
                'error': str(e)
            }

    def get_strategies_status(self) -> Dict[str, Any]:
        """
        Retourne le statut organisé par stratégies (nouvelle structure hiérarchique)
        """
        try:
            from datetime import timezone
            import re
            jobs = self.scheduler.get_jobs()
            now = datetime.now(timezone.utc)
            
            strategies = {}
            system_jobs = []
            
            def safe_datetime_compare(job_time, reference_time):
                """Safely compare datetimes, handling timezone issues"""
                if job_time is None:
                    return False
                try:
                    if job_time.tzinfo is None:
                        job_time = job_time.replace(tzinfo=timezone.utc)
                    if reference_time.tzinfo is None:
                        reference_time = reference_time.replace(tzinfo=timezone.utc)
                    return job_time < reference_time
                except Exception:
                    return False
            
            for job in jobs:
                # Jobs système séparés
                if job.id in ['precision_test', 'cleanup_expired_jobs']:
                    system_jobs.append({
                        'id': job.id,
                        'name': job.name,
                        'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                        'trigger': str(job.trigger)
                    })
                    continue
                
                # Extraction des informations de stratégie depuis job.id
                # Format typique: "extended_unlocked_boost_106517_20250815_114358_action_0_unlocked_boost"
                challenge_id = None
                strategy_name = None
                action_name = None
                
                # Pattern pour extraire challenge_id et strategy_name
                patterns = [
                    r'extended_([^_]+)_(\d+)_\d+_action_\d+_(.+)',  # extended strategy
                    r'([^_]+)_(\d+)_\d+',  # simple strategy
                    r'.*_(\d{6})_.*'  # fallback pour challenge ID
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, job.id)
                    if match:
                        if len(match.groups()) >= 3:
                            strategy_name = match.group(1)
                            challenge_id = match.group(2)
                            action_name = match.group(3)
                        elif len(match.groups()) >= 2:
                            strategy_name = match.group(1)
                            challenge_id = match.group(2)
                            action_name = strategy_name
                        else:
                            challenge_id = match.group(1)
                        break
                
                if not challenge_id:
                    # Si on ne peut pas extraire, mettre dans "unknown"
                    challenge_id = "unknown"
                    strategy_name = "unknown"
                    action_name = job.name or job.id
                
                # Statut du job
                is_expired = safe_datetime_compare(job.next_run_time, now - timedelta(hours=1))
                job_status = "expired" if is_expired else "scheduled"
                
                # Initialiser la stratégie si nécessaire
                strategy_key = f"challenge_{challenge_id}"
                if strategy_key not in strategies:
                    strategies[strategy_key] = {
                        "challenge_id": challenge_id,
                        "strategy_name": strategy_name or "unknown",
                        "strategy_status": "active",  # active, completed, failed
                        "jobs": [],
                        "total_jobs": 0,
                        "scheduled_jobs": 0,
                        "expired_jobs": 0,
                        "last_activity": None
                    }
                
                # Ajouter le job à la stratégie
                job_info = {
                    "job_id": job.id,
                    "action": action_name or "unknown",
                    "status": job_status,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                    "trigger": str(job.trigger),
                    "job_name": job.name
                }
                
                strategies[strategy_key]["jobs"].append(job_info)
                strategies[strategy_key]["total_jobs"] += 1
                
                if job_status == "scheduled":
                    strategies[strategy_key]["scheduled_jobs"] += 1
                elif job_status == "expired":
                    strategies[strategy_key]["expired_jobs"] += 1
                
                # Mettre à jour last_activity
                if job.next_run_time:
                    if not strategies[strategy_key]["last_activity"] or job.next_run_time > datetime.fromisoformat(strategies[strategy_key]["last_activity"].replace('Z', '+00:00')):
                        strategies[strategy_key]["last_activity"] = job.next_run_time.isoformat()
            
            # Déterminer le statut des stratégies
            for strategy_key, strategy in strategies.items():
                if strategy["expired_jobs"] > 0 and strategy["scheduled_jobs"] == 0:
                    strategy["strategy_status"] = "expired"
                elif strategy["scheduled_jobs"] > 0:
                    strategy["strategy_status"] = "active"
                else:
                    strategy["strategy_status"] = "completed"
                
                # Calculer le progress
                if strategy["total_jobs"] > 0:
                    strategy["progress"] = f"{strategy['total_jobs'] - strategy['scheduled_jobs']}/{strategy['total_jobs']}"
                else:
                    strategy["progress"] = "0/0"
            
            return {
                'scheduler_running': self._running,
                'total_strategies': len(strategies),
                'total_jobs': len(jobs) - len(system_jobs),
                'strategies': strategies,
                'system_jobs': system_jobs,
                'status_timestamp': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting strategies status: {e}")
            return {
                'scheduler_running': self._running,
                'error': str(e)
            }


# Instance globale du scheduler
strategy_scheduler = StrategyScheduler()