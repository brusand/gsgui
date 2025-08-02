"""
GuruShots API Service - Extrait et refactorisé de AsyncFetcher dans gsui.py
"""

import aiohttp
import asyncio
import ssl
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass

from app.core.config import settings

logger = logging.getLogger(__name__)

# Configuration SSL (comme dans gsui.py)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


@dataclass
class ChallengeData:
    """Structure de données pour un challenge"""
    id: str
    title: str
    end_time: datetime
    time_left: Dict[str, int]  # {"days": 0, "hours": 2, "minutes": 30, "seconds": 15}
    url: str
    votes: int
    rank: int
    level: str
    exposure: int
    gps: int
    challenge_data: Dict[str, Any]  # Données complètes de l'API


@dataclass  
class VotePanel:
    """Structure de données pour un panel de vote"""
    images: List[Dict[str, Any]]
    challenge_data: Dict[str, Any]
    success: bool
    message: str = ""


@dataclass
class VoteResult:
    """Résultat d'un vote"""
    success: bool
    message: str
    result_data: Optional[Dict[str, Any]] = None


class GuruShotsAPI:
    """
    Service API pour GuruShots
    Refactorisation de la classe AsyncFetcher de gsui.py
    """
    
    def __init__(self, user_token: str):
        self.user_token = user_token
        self.headers = self._create_headers(user_token)
        self.base_url = settings.GURUSHOTS_API_BASE
        
    def _create_headers(self, user_token: str) -> Dict[str, str]:
        """Crée les headers HTTP comme dans gsui.py"""
        return {
            'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:39.0) Gecko/20100101 Firefox/39.0',
            'x-api-version': '8',
            'x-env': 'WEB',
            'X-requested-with': 'XMLHttpRequest',
            'X-token': user_token
        }
    
    async def get_challenges(self) -> List[ChallengeData]:
        """
        Récupère la liste des challenges actifs
        Équivalent de fetch_challenges() dans gsui.py
        """
        try:
            logger.info(f"🔍 Fetching challenges avec token: {self.user_token[:20]}...")
            
            async with aiohttp.ClientSession(
                headers=self.headers,
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                async with session.post(f'{self.base_url}/get_my_active_challenges') as response:
                    logger.info(f"📡 Response status: {response.status}")
                    
                    if response.status != 200:
                        logger.error(f"❌ API Error: Status {response.status}")
                        return []
                    
                    data = await response.json()
                    logger.info(f"📊 JSON data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    
                    challenges = []
                    for challenge_data in data.get('challenges', []):
                        try:
                            challenge = self._parse_challenge_data(challenge_data)
                            challenges.append(challenge)
                        except Exception as e:
                            logger.error(f"Error parsing challenge {challenge_data.get('id', 'unknown')}: {e}")
                            continue
                    
                    logger.info(f"✅ Successfully fetched {len(challenges)} challenges")
                    return challenges
                    
        except Exception as e:
            logger.error(f"❌ Error fetching challenges: {e}")
            return []
    
    def _parse_challenge_data(self, challenge_data: Dict[str, Any]) -> ChallengeData:
        """Parse les données d'un challenge depuis l'API"""
        timeleft = challenge_data['time_left']
        
        return ChallengeData(
            id=challenge_data['id'],
            title=challenge_data['title'],
            end_time=datetime.fromtimestamp(challenge_data["close_time"]),
            time_left=timeleft,
            url=challenge_data['url'],
            votes=int(challenge_data['member']['ranking']['total']['votes']),
            rank=int(challenge_data['member']['ranking']['total']['rank']),
            level=challenge_data['member']['ranking']['total']['level_name'],
            exposure=int(challenge_data['member']['ranking']['total']['exposure']),
            gps=int(0),  # Comme dans gsui.py
            challenge_data=challenge_data
        )
    
    async def get_vote_panel(self, challenge_url: str, limit: int = 100) -> VotePanel:
        """
        Récupère le panel de vote pour un challenge
        Équivalent de fetch_get_votes_panel() dans gsui.py
        """
        try:
            if not challenge_url:
                return VotePanel(
                    images=[],
                    challenge_data={"close_time": 0},
                    success=False,
                    message="Challenge URL is missing or invalid"
                )
            
            logger.info(f"Récupération des données de vote pour {challenge_url}")
            
            async with aiohttp.ClientSession(
                headers=self.headers,
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                async with session.post(
                    f'{self.base_url}/get_vote_data',
                    data={'limit': limit, 'url': challenge_url}
                ) as response:
                    
                    if response.status == 200:
                        try:
                            result = await response.json()
                            
                            # Vérifier que la réponse contient des images
                            if not result.get('images') or len(result.get('images', [])) == 0:
                                logger.warning(f"Pas d'images disponibles pour {challenge_url}")
                                return VotePanel(
                                    images=[],
                                    challenge_data={"close_time": 0},
                                    success=False,
                                    message="No images available"
                                )
                            
                            logger.info(f"✅ Récupération réussie: {len(result.get('images', []))} images")
                            return VotePanel(
                                images=result.get('images', []),
                                challenge_data=result.get('challenge', {}),
                                success=True
                            )
                            
                        except Exception as json_error:
                            error_text = await response.text()
                            logger.error(f"Erreur de parsing JSON: {json_error}, Réponse: {error_text[:100]}...")
                            return VotePanel(
                                images=[],
                                challenge_data={"close_time": 0},
                                success=False,
                                message=f"JSON parsing error: {json_error}"
                            )
                    else:
                        error_text = await response.text()
                        logger.error(f"Erreur HTTP {response.status}: {error_text[:100]}...")
                        return VotePanel(
                            images=[],
                            challenge_data={"close_time": 0},
                            success=False,
                            message=f"HTTP {response.status}: {error_text}"
                        )
                        
        except Exception as e:
            logger.error(f"Exception générale lors de la récupération des votes: {e}")
            return VotePanel(
                images=[],
                challenge_data={"close_time": 0},
                success=False,
                message=str(e)
            )
    
    async def submit_votes(self, challenge_id: str, vote_tokens: List[str]) -> VoteResult:
        """
        Soumet des votes pour un challenge
        Équivalent de fetch_post_votes_panel() dans gsui.py
        """
        try:
            # Vérifier que nous avons des tokens à envoyer
            if not vote_tokens or len(vote_tokens) == 0:
                return VoteResult(
                    success=False,
                    message="No valid image tokens to vote on"
                )
            
            # Vérifier que tous les tokens sont valides (non vides)
            valid_votes = [v for v in vote_tokens if v and v.strip()]
            if len(valid_votes) == 0:
                return VoteResult(
                    success=False,
                    message="All image tokens were empty or invalid"
                )
            
            # Créer le payload avec seulement les tokens valides
            payload = {'tokens[' + str(id) + ']': value for id, value in enumerate(valid_votes)}
            payload.update({'viewed_tokens[' + str(id) + ']': value for id, value in enumerate(valid_votes)})
            
            if not challenge_id:
                return VoteResult(
                    success=False,
                    message="Invalid challenge ID"
                )
            
            payload['c_id'] = challenge_id
            # Token de challenge fixe comme dans gsui.py - à améliorer en production
            payload['c_token'] = "03AOLTBLR8mMuwAHd5TwbZo5KuuMZYDUVbM-gwQZgojsOHPf-NdlccOUjk6DXw6QE3thLUf6ASwqgQigw1-zTLI6-prjlTIS9ByBXVvePZkYXGwf6MDNIielvqiEWTemoMPWkKVSPme0EOALsd0MrbwDFHxbS02LGpt2u9GwieEKurIUmP7IKNxPEVBGwSR9UTDhWLfUimQK-yDKBVzIZYmbiEHM6gw85-9jDbtGtaAKcEGio83U6b4lmaGWVr8jhWYDKW49PDPrlc0hqYoV1nAOMySaIstamSZP56Zzp3ejo_1A0EqMOL1vGaG5aKt8a-tFY26Q9TRROHx8lVNcJoSBuBHFGUzl2n12JLjqAvJd6BcOweUMlhJapSrwSgHpRl5UQJ58G2AkWdMMvkwbplXZCqQ8cdv_HAzduBOwzutsfuubfCk0Fgqfb1wFK1FrfSGyRVhgrmci12xKmiIrIP1ZIOycaCXI7V0-sY5TW94mmjknYGwUiCdNI"
            
            async with aiohttp.ClientSession(
                headers=self.headers,
                connector=aiohttp.TCPConnector(ssl=False)
            ) as session:
                async with session.post(f'{self.base_url}/submit_votes', data=payload) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        return VoteResult(
                            success=True,
                            message="Votes submitted successfully",
                            result_data=result
                        )
                    else:
                        error_text = await response.text()
                        return VoteResult(
                            success=False,
                            message=f"HTTP {response.status}: {error_text}"
                        )
                        
        except Exception as e:
            return VoteResult(
                success=False,
                message=str(e)
            )
    
    async def execute_simple_vote(self, challenge_url: str, vote_count: int) -> VoteResult:
        """
        Exécute un vote simple sur un challenge
        Combine get_vote_panel + submit_votes
        """
        try:
            # Récupérer le panel de vote
            vote_panel = await self.get_vote_panel(challenge_url)
            
            if not vote_panel.success:
                return VoteResult(
                    success=False,
                    message=f"Failed to get vote panel: {vote_panel.message}"
                )
            
            if len(vote_panel.images) == 0:
                return VoteResult(
                    success=False,
                    message="No images available for voting"
                )
            
            # Extraire les tokens des premières images
            vote_tokens = []
            for i, image in enumerate(vote_panel.images[:vote_count]):
                if 'token' in image:
                    vote_tokens.append(image['token'])
            
            if not vote_tokens:
                return VoteResult(
                    success=False,
                    message="No valid vote tokens found in images"
                )
            
            # Soumettre les votes
            challenge_id = vote_panel.challenge_data.get('id', '')
            return await self.submit_votes(challenge_id, vote_tokens)
            
        except Exception as e:
            return VoteResult(
                success=False,
                message=f"Error executing simple vote: {str(e)}"
            )