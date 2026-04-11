"""
Auto-Refresh Scheduler Service
Rafraîchit automatiquement tous les challenges d'un profil via APScheduler
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from app.services.config_manager import config_manager
from app.services.gurushots_api import GuruShotsAPI

logger = logging.getLogger(__name__)


class AutoRefreshScheduler:
    """Gère l'auto-refresh global des challenges"""

    def __init__(self, strategy_scheduler):
        self.scheduler = strategy_scheduler.scheduler
        self.api_instances: Dict[str, GuruShotsAPI] = {}  # Cache des API instances
        logger.info("🔄 AutoRefreshScheduler initialized")

    async def enable_auto_refresh(
        self,
        profile_id: str,
        interval_minutes: int = 5
    ) -> bool:
        """Active l'auto-refresh pour un profil"""
        try:
            job_id = f"auto_refresh_{profile_id}"

            # Supprimer l'ancien job s'il existe
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.debug(f"Removed existing auto-refresh job for {profile_id}")

            # Ajouter le nouveau job avec interval trigger
            self.scheduler.add_job(
                func=self._refresh_all_challenges,
                trigger='interval',
                minutes=interval_minutes,
                args=[profile_id],
                id=job_id,
                name=f"Auto-Refresh {profile_id}",
                replace_existing=True
            )

            # Sauvegarder la config (ne passer que les clés modifiées pour éviter d'écraser scheduled_strategies)
            user_data = config_manager.get_user(profile_id)
            updates = {'auto_refresh_enabled': True}
            # Ne pas écraser auto_refresh_interval s'il existe déjà
            if not user_data or 'auto_refresh_interval' not in user_data:
                updates['auto_refresh_interval'] = interval_minutes
            config_manager.update_user(profile_id, updates)

            logger.debug(f"Auto-refresh enabled for {profile_id} (every {interval_minutes}m)")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to enable auto-refresh: {e}")
            return False

    async def disable_auto_refresh(self, profile_id: str) -> bool:
        """Désactive l'auto-refresh pour un profil"""
        try:
            job_id = f"auto_refresh_{profile_id}"

            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.debug(f"Auto-refresh disabled for {profile_id}")

            # Mettre à jour la config (ne passer que les clés modifiées)
            updates = {'auto_refresh_enabled': False}
            config_manager.update_user(profile_id, updates)

            return True

        except Exception as e:
            logger.error(f"❌ Failed to disable auto-refresh: {e}")
            return False

    def get_status(self, profile_id: str) -> Dict[str, Any]:
        """Retourne le statut de l'auto-refresh"""
        job_id = f"auto_refresh_{profile_id}"
        job = self.scheduler.get_job(job_id)

        user_data = config_manager.get_user(profile_id) or {}

        return {
            "enabled": job is not None,
            "interval_minutes": user_data.get('auto_refresh_interval', 5),
            "next_run": job.next_run_time.isoformat() if job and job.next_run_time else None
        }

    async def _refresh_all_challenges(self, profile_id: str):
        """
        Job APScheduler - Rafraîchit tous les challenges d'un profil
        1 seul call API GuruShots
        """
        try:
            logger.debug(f"Auto-refreshing challenges for {profile_id}")

            # Récupérer l'API instance
            api = await self._get_api_instance(profile_id)

            challenges = await api.get_challenges()

            # Identifier les boosts disponibles (AVAILABLE = gratuit, à activer immédiatement)
            import time
            available_boosts = []
            for challenge in challenges:
                try:
                    challenge_dict = challenge.challenge_data if hasattr(challenge, 'challenge_data') else challenge
                    challenge_id = challenge.id if hasattr(challenge, 'id') else challenge_dict.get('id')
                    challenge_title = challenge.title if hasattr(challenge, 'title') else challenge_dict.get('title', 'Unknown')

                    if 'member' in challenge_dict and 'boost' in challenge_dict['member']:
                        boost_data = challenge_dict['member']['boost']
                        if isinstance(boost_data, dict):
                            state = boost_data.get('state')
                            timeout = boost_data.get('timeout')

                            # Logger tous les états de boost pour le diagnostic
                            if state and state != 'LOCKED':
                                remaining_info = ''
                                if timeout is not None:
                                    remaining_seconds = timeout - int(time.time())
                                    remaining_info = f' | remaining: {int(remaining_seconds / 60)}m'
                                logger.info(f"🔍 [{profile_id}] Boost state for '{challenge_title}' (ID: {challenge_id}): {state}{remaining_info}")

                            if state == 'AVAILABLE' and timeout is not None:
                                now = int(time.time())
                                remaining_seconds = timeout - now
                                remaining_minutes = remaining_seconds / 60

                                if 0 < remaining_minutes <= 15:
                                    available_boosts.append({
                                        'id': challenge_id,
                                        'title': challenge_title,
                                        'remaining_minutes': int(remaining_minutes)
                                    })
                except Exception as e:
                    challenge_id = challenge.id if hasattr(challenge, 'id') else 'unknown'
                    logger.warning(f"⚠️ Error checking boost for challenge {challenge_id}: {e}")

            # Activer automatiquement les boosts disponibles (gratuits)
            if available_boosts:
                for boost in available_boosts:
                    logger.warning(f"⚡ [{profile_id}] BOOST GRATUIT: Challenge '{boost['title']}' (ID: {boost['id']}) - expire dans {boost['remaining_minutes']}m")
                    await self._send_log_to_ui(
                        profile_id,
                        "warning",
                        f"⚡ BOOST GRATUIT: '{boost['title']}' expire dans {boost['remaining_minutes']}m"
                    )

                    # Appeler boost_photo automatiquement avec le vrai photo_id
                    try:
                        # Récupérer le vrai photo_id de la première photo du membre
                        photo_id = None
                        challenge_dict = None

                        # Trouver le challenge correspondant dans la liste
                        for ch in challenges:
                            ch_dict = ch.challenge_data if hasattr(ch, 'challenge_data') else ch
                            ch_id = ch.id if hasattr(ch, 'id') else ch_dict.get('id')
                            if str(ch_id) == str(boost['id']):
                                challenge_dict = ch_dict
                                break

                        if challenge_dict and 'member' in challenge_dict and 'ranking' in challenge_dict['member'] and 'entries' in challenge_dict['member']['ranking']:
                            items = challenge_dict['member']['ranking']['entries']
                            # Logger les entries pour diagnostic
                            logger.info(f"🔍 [{profile_id}] Boost entries for challenge {boost['id']}: {len(items)} photos, turbo states: {[item.get('turbo', False) for item in items]}")
                            # Chercher la première photo non-turbo
                            for item in items:
                                if not item.get('turbo', False):
                                    photo_id = item.get('id')
                                    break
                            # Si toutes les photos sont turbo, log explicite
                            if not photo_id and items:
                                logger.warning(f"⚠️ [{profile_id}] Toutes les photos sont déjà turbo pour challenge {boost['id']}")
                        if not photo_id:
                            logger.warning(f"⚠️ Impossible de trouver photo_id pour challenge {boost['id']}, skip boost")
                            await self._send_log_to_ui(
                                profile_id,
                                "warning",
                                f"⚠️ Pas de photo trouvée pour boost '{boost['title']}'"
                            )
                            continue

                        logger.info(f"🚀 Activation automatique du boost pour challenge {boost['id']} avec photo_id={photo_id}")
                        await self._send_log_to_ui(
                            profile_id,
                            "info",
                            f"🚀 Activation du boost pour '{boost['title']}' (photo ID: {photo_id})..."
                        )

                        result = await api.boost_photo(
                            challenge_id=int(boost['id']),
                            image_id=str(photo_id)
                        )

                        # Vérifier si le boost a vraiment réussi
                        if isinstance(result, dict) and result.get('success') == False:
                            error_code = result.get('error_code', 'unknown')
                            logger.error(f"❌ Échec activation boost pour challenge {boost['id']}: error_code={error_code}")
                            await self._send_log_to_ui(
                                profile_id,
                                "error",
                                f"❌ Échec boost '{boost['title']}': GuruShots error {error_code}"
                            )
                        else:
                            logger.info(f"✅ Boost activé avec succès pour challenge {boost['id']}: {result}")
                            await self._send_log_to_ui(
                                profile_id,
                                "success",
                                f"✅ Boost activé avec succès pour '{boost['title']}'"
                            )

                    except Exception as boost_error:
                        logger.error(f"❌ Erreur lors de l'activation du boost pour challenge {boost['id']}: {boost_error}")
                        await self._send_log_to_ui(
                            profile_id,
                            "error",
                            f"❌ Erreur boost '{boost['title']}': {boost_error}"
                        )

            # Sauvegarder dans config
            for challenge in challenges:
                challenge_dict = challenge.challenge_data if hasattr(challenge, 'challenge_data') else challenge
                challenge_id = challenge.id if hasattr(challenge, 'id') else challenge_dict.get('id')
                config_manager.save_user_challenge(
                    profile_id,
                    str(challenge_id),  # Convertir en string pour ConfigObj
                    challenge_dict
                )

            # Notifier via WebSocket
            try:
                from app.websockets.connection_manager import connection_manager

                # Convertir les ChallengeData en dictionnaires pour le WebSocket
                challenges_dict = [
                    challenge.challenge_data if hasattr(challenge, 'challenge_data') else challenge
                    for challenge in challenges
                ]

                # Récupérer les stratégies schedulées pour ce profil
                user_data = config_manager.get_user(profile_id)
                scheduled_strategies = user_data.get('scheduled_strategies', {}) if user_data else {}

                # Merger les informations de stratégie avec les challenges
                for challenge_dict in challenges_dict:
                    challenge_id = str(challenge_dict.get('id'))
                    if challenge_id in scheduled_strategies:
                        strategy_info = scheduled_strategies[challenge_id]
                        challenge_dict['selected_strategy'] = strategy_info.get('strategy_name', '')
                        challenge_dict['strategy_status'] = strategy_info.get('strategy_status', '')
                        challenge_dict['strategy_started_at'] = strategy_info.get('started_at', '')

                await connection_manager.send_personal_message(
                    profile_id,
                    {
                        "type": "challenges_refreshed",
                        "profile_id": profile_id,
                        "challenges": challenges_dict,
                        "timestamp": datetime.now().isoformat()
                    }
                )

            except Exception as ws_error:
                logger.warning(f"⚠️ WebSocket notification failed: {ws_error}")
                await self._send_log_to_ui(
                    profile_id,
                    "warning",
                    f"⚠️ Notification WebSocket échouée: {ws_error}"
                )

            logger.debug(f"Auto-refreshed {len(challenges)} challenges for {profile_id}")

        except Exception as e:
            logger.error(f"❌ Auto-refresh failed for {profile_id}: {e}")
            await self._send_log_to_ui(
                profile_id,
                "error",
                f"❌ Erreur Auto-Refresh: {e}"
            )

    async def _get_api_instance(self, profile_id: str) -> GuruShotsAPI:
        """Récupère ou crée une instance API pour un profil"""
        if profile_id not in self.api_instances:
            user = config_manager.get_user(profile_id)
            if not user:
                raise ValueError(f"Profile {profile_id} not found")

            xtoken = user.get('xtoken')
            if not xtoken:
                raise ValueError(f"No token for profile {profile_id}")

            self.api_instances[profile_id] = GuruShotsAPI(xtoken)

        return self.api_instances[profile_id]

    async def restore_from_config(self):
        """Restaure les auto-refresh depuis la config au démarrage"""
        try:
            users = config_manager.list_users()

            # Initialiser auto_refresh_interval pour tous les profils s'ils ne l'ont pas
            for user_id in users:
                user_data = config_manager.get_user(user_id)
                if user_data and 'auto_refresh_interval' not in user_data:
                    updates = {'auto_refresh_interval': 5}
                    config_manager.update_user(user_id, updates)
                    logger.debug(f"Initialized auto_refresh_interval=5 for {user_id}")

            # Restaurer les auto-refresh actifs
            for user_id in users:
                user_data = config_manager.get_user(user_id)

                if user_data and user_data.get('auto_refresh_enabled'):
                    # Lire l'intervalle existant (maintenant garanti d'exister)
                    interval = int(user_data.get('auto_refresh_interval', 5))
                    await self.enable_auto_refresh(user_id, interval)
                    logger.debug(f"Restored auto-refresh for {user_id} with interval {interval}m")

        except Exception as e:
            logger.error(f"❌ Failed to restore auto-refresh: {e}")

    async def _send_log_to_ui(self, profile_id: str, level: str, message: str):
        """Envoie un message de log au frontend via WebSocket"""
        try:
            from app.websockets.connection_manager import connection_manager

            await connection_manager.send_personal_message(
                profile_id,
                {
                    "type": "log",
                    "level": level,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "source": "auto_refresh"
                }
            )
        except Exception as e:
            logger.warning(f"⚠️ Failed to send log to UI: {e}")


# Instance globale
auto_refresh_scheduler: Optional[AutoRefreshScheduler] = None


def init_auto_refresh_scheduler(strategy_scheduler):
    """Initialise l'auto-refresh scheduler"""
    global auto_refresh_scheduler
    auto_refresh_scheduler = AutoRefreshScheduler(strategy_scheduler)
    return auto_refresh_scheduler
