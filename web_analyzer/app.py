#!/usr/bin/env python3
"""
GURUSHOTS WEB ANALYZER
Application web pour l'analyse interactive des stratégies GuruShots
"""

from flask import Flask, render_template, jsonify, request, send_file
import sqlite3
import os
import json
import io
import base64
import plotly.graph_objects as go
import plotly.subplots as sp
from plotly.utils import PlotlyJSONEncoder
import numpy as np
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, List, Any, Tuple
import colorsys
import requests as http_requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor as APThreadPoolExecutor
from apscheduler.triggers.date import DateTrigger

# Fuseau horaire
PARIS_TZ = ZoneInfo("Europe/Paris")

# Import de notre classe existante (adaptée pour le web)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)

BRUNO_MEMBER_ID = '0ccd720cab0da1c771a7a2086453d7dc'
GURUSHOTS_API = 'https://api.gurushots.com/rest'

def load_bruno_token() -> str:
    """Charger le token X-token depuis backend/data/gsgui.ini"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend', 'data', 'gsgui.ini')
    try:
        with open(config_path, 'r') as f:
            in_bruno = False
            for line in f:
                line = line.strip()
                if line == '[[bruno]]':
                    in_bruno = True
                elif line.startswith('[[') and in_bruno:
                    break
                elif in_bruno and line.startswith('xtoken'):
                    return line.split('=', 1)[1].strip()
    except Exception:
        pass
    return ''

GS_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:39.0) Gecko/20100101 Firefox/39.0',
    'x-api-version': '8',
    'x-env': 'WEB',
    'X-requested-with': 'XMLHttpRequest',
    'X-token': load_bruno_token(),
}

def utc_to_paris(dt_str: str) -> str:
    """Convertir un timestamp UTC en Europe/Paris"""
    try:
        # Parser le timestamp (peut être ISO format ou avec 'Z')
        dt_str_clean = dt_str.replace('Z', '+00:00')
        dt_utc = datetime.fromisoformat(dt_str_clean)

        # Si pas de timezone, supposer UTC
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)

        # Convertir en Paris
        dt_paris = dt_utc.astimezone(PARIS_TZ)
        return dt_paris.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return dt_str

def now_paris() -> datetime:
    """Obtenir l'heure actuelle en Europe/Paris"""
    return datetime.now(PARIS_TZ)

def now_paris_str() -> str:
    """Obtenir l'heure actuelle en Europe/Paris (format string)"""
    return now_paris().strftime('%Y-%m-%d %H:%M:%S')

class PhotoColorManager:
    """Gestionnaire de couleurs pour les photos"""
    
    def __init__(self):
        self.photo_colors = {}
        self.color_index = 0
        
    def get_color_for_photo(self, photo_id: str) -> str:
        """Obtenir une couleur unique pour une photo (format hex pour Plotly)"""
        if photo_id not in self.photo_colors:
            # Générer une couleur unique avec HSV
            hue = (self.color_index * 137.508) % 360  # Nombre d'or pour distribution uniforme
            saturation = 0.7 + (self.color_index % 3) * 0.1  # Varier saturation
            value = 0.8 + (self.color_index % 2) * 0.2        # Varier luminosité
            
            rgb = colorsys.hsv_to_rgb(hue/360, saturation, value)
            # Convertir en hex pour Plotly
            hex_color = '#{:02x}{:02x}{:02x}'.format(
                int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)
            )
            self.photo_colors[photo_id] = hex_color
            self.color_index += 1
            
        return self.photo_colors[photo_id]

class WebGuruShotsAnalyzer:
    """Analyseur GuruShots pour le web"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.color_manager = PhotoColorManager()
        
    def get_connection(self):
        """Obtenir une connexion à la base de données"""
        return sqlite3.connect(self.db_path)
    
    def get_available_challenges(self) -> List[Dict]:
        """Récupérer tous les challenges disponibles"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
            SELECT DISTINCT 
                s.challenge_id as id, 
                COALESCE(c.title, 'Challenge ' || s.challenge_id) as title, 
                CASE 
                    WHEN MIN(s.seconds_to_end) <= 0 THEN 'ended'
                    ELSE 'active'
                END as status,
                COUNT(s.id) as snapshot_count,
                COUNT(DISTINCT ps.member_id) as member_count,
                MIN(s.timestamp) as first_snapshot,
                MAX(s.timestamp) as last_snapshot,
                MIN(s.seconds_to_end) as min_seconds_to_end,
                COALESCE(c.close_time, 0) as end_time
            FROM snapshots s
            LEFT JOIN participant_snapshots ps ON s.id = ps.snapshot_id
            LEFT JOIN challenges c ON s.challenge_id = c.c_id
            GROUP BY s.challenge_id
            HAVING snapshot_count > 10
            ORDER BY
                CASE WHEN c.close_time IS NOT NULL THEN c.close_time ELSE 0 END DESC,
                last_snapshot DESC
            """
            
            cursor.execute(query)
            challenges = []
            
            for row in cursor.fetchall():
                challenge_id, title, status, snapshots, members, first_snap, last_snap, min_seconds, end_time = row
                challenges.append({
                    'id': challenge_id,
                    'title': title,
                    'status': status,
                    'snapshots': snapshots,
                    'members': members,
                    'first_snapshot': utc_to_paris(first_snap) if first_snap else None,
                    'last_snapshot': utc_to_paris(last_snap) if last_snap else None
                })
            
            return challenges
    
    def get_challenge_members(self, challenge_id: str) -> List[Dict]:
        """Récupérer les top membres d'un challenge"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
            SELECT DISTINCT 
                m.id,
                m.name,
                COUNT(ps.id) as appearances,
                MIN(ps.total_votes) as min_votes,
                MAX(ps.total_votes) as max_votes,
                MIN(ps.total_rank) as best_rank,
                MAX(ps.total_rank) as worst_rank
            FROM members m
            JOIN participant_snapshots ps ON m.id = ps.member_id
            JOIN snapshots s ON ps.snapshot_id = s.id
            WHERE s.challenge_id = ?
            GROUP BY m.id, m.name
            HAVING appearances >= 1
            ORDER BY best_rank ASC, appearances DESC
            LIMIT 50
            """
            
            cursor.execute(query, (challenge_id,))
            members = []
            
            for row in cursor.fetchall():
                member_id, name, appearances, min_votes, max_votes, best_rank, worst_rank = row
                members.append({
                    'id': member_id,
                    'name': name or f'Member_{member_id[:8]}',
                    'appearances': appearances,
                    'vote_range': [min_votes, max_votes],
                    'rank_range': [best_rank, worst_rank],
                    'vote_gain': max_votes - min_votes if max_votes and min_votes else 0
                })
            
            return members
    
    def get_member_data(self, challenge_id: str, member_id: str) -> Dict:
        """Récupérer les données d'un membre pour un challenge"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Récupérer les données avec entries et seconds_to_end
            query = """
            SELECT 
                s.timestamp,
                s.seconds_to_end,
                ps.total_votes,
                ps.total_rank,
                ph.photo_id,
                ph.votes as photo_votes,
                ph.rank as photo_rank,
                ph.boost_timestamp,
                ph.guru_pick,
                ROW_NUMBER() OVER (PARTITION BY s.timestamp ORDER BY ph.votes DESC) - 1 as entry_position
            FROM snapshots s
            JOIN participant_snapshots ps ON s.id = ps.snapshot_id
            JOIN photo_snapshots ph ON ps.id = ph.participant_snapshot_id
            WHERE s.challenge_id = ? AND ps.member_id = ?
            ORDER BY s.timestamp, ph.votes DESC
            """
            
            cursor.execute(query, (challenge_id, member_id))
            raw_data = cursor.fetchall()
            
            # Grouper par timestamp
            collections = {}
            for timestamp, seconds_to_end, total_votes, total_rank, photo_id, photo_votes, photo_rank, boost_ts, guru_pick, entry_pos in raw_data:
                if timestamp not in collections:
                    collections[timestamp] = {
                        'timestamp': timestamp,
                        'seconds_to_end': seconds_to_end,
                        'total_votes': total_votes,
                        'total_rank': total_rank,
                        'entries': [None, None, None, None]  # Entry_0, Entry_1, Entry_2, Entry_3
                    }
                
                if entry_pos < 4:  # Seulement les 4 premières positions
                    collections[timestamp]['entries'][entry_pos] = {
                        'photo_id': photo_id,
                        'votes': photo_votes,
                        'rank': photo_rank,
                        'boosted': boost_ts != -1 and boost_ts is not None,
                        'guru_pick': guru_pick
                    }
            
            return list(collections.values())
    
    def format_time_from_seconds(self, seconds: int) -> str:
        """Formatter le temps selon le système du backend (1h00 -> 0h55 -> 0h50 -> ... -> 0h10m -> 0h9m0s -> etc.)"""
        if seconds >= 3600:  # Plus d'1 heure
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}h{minutes:02d}m"
            else:
                return f"{hours}h00m"
        elif seconds >= 60:  # Plus d'1 minute
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m{secs:02d}s"
        else:  # Moins d'1 minute
            return f"{seconds}s"
    
    def format_time_from_minutes(self, total_minutes: float) -> str:
        """Formatter les minutes en format j-h-m-s lisible pour l'axe X"""
        if total_minutes <= 0:
            return "Fin"
        
        total_seconds = int(total_minutes * 60)
        
        # Convertir en jours, heures, minutes, secondes
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        # Format adaptatif selon la durée
        if days > 0:
            if hours > 0:
                return f"{days}j{hours}h"
            else:
                return f"{days}j"
        elif hours > 0:
            if minutes > 0:
                return f"{hours}h{minutes:02d}m"
            else:
                return f"{hours}h"
        elif minutes > 0:
            if seconds > 0:
                return f"{minutes}m{seconds:02d}s"
            else:
                return f"{minutes}m"
        else:
            return f"{seconds}s"
    
    def create_readable_x_ticks(self, times: List[float]) -> Dict:
        """Créer des ticks lisibles pour l'axe X en format j-h-m-s"""
        if not times:
            return {'values': [], 'labels': []}
        
        min_time = min(times)
        max_time = max(times)
        time_range = max_time - min_time
        
        # Déterminer le nombre optimal de ticks (6-10 ticks)
        if time_range <= 60:  # Moins d'1 heure
            # Ticks tous les 10 minutes
            step = 10
        elif time_range <= 360:  # Moins de 6 heures
            # Ticks toutes les 30 minutes
            step = 30
        elif time_range <= 1440:  # Moins de 24 heures
            # Ticks toutes les 2 heures
            step = 120
        else:  # Plus de 24 heures
            # Ticks tous les 6 heures
            step = 360
        
        # Générer les valeurs de ticks
        tick_values = []
        tick_labels = []
        
        # Commencer par le maximum arrondi
        start_tick = int((max_time // step + 1) * step)
        
        current_tick = start_tick
        while current_tick >= min_time - step:
            if min_time <= current_tick <= max_time:
                tick_values.append(current_tick)
                tick_labels.append(self.format_time_from_minutes(current_tick))
            current_tick -= step
        
        # Ajouter toujours le point 0 (fin)
        if 0 not in tick_values and min_time <= 0:
            tick_values.append(0)
            tick_labels.append("Fin")
        
        # Trier par ordre décroissant (pour l'affichage inversé)
        sorted_pairs = sorted(zip(tick_values, tick_labels), reverse=True)
        tick_values, tick_labels = zip(*sorted_pairs) if sorted_pairs else ([], [])
        
        return {
            'values': list(tick_values),
            'labels': list(tick_labels)
        }
    
    def calculate_time_remaining(self, collections: List[Dict], challenge_end: datetime) -> List[Dict]:
        """Calculer le temps restant pour chaque collection avec formatage proper"""
        for collection in collections:
            timestamp = datetime.fromisoformat(collection['timestamp'].replace('Z', '+00:00'))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            # Convertir challenge_end en timezone-aware si nécessaire
            if isinstance(challenge_end, datetime) and challenge_end.tzinfo is None:
                challenge_end = challenge_end.replace(tzinfo=PARIS_TZ)
            time_remaining_seconds = int((challenge_end - timestamp).total_seconds())
            
            # Utiliser les secondes restantes réelles des snapshots si disponibles
            if 'seconds_to_end' in collection:
                time_remaining_seconds = collection['seconds_to_end']
            
            collection['time_remaining_seconds'] = time_remaining_seconds
            collection['time_remaining_total_minutes'] = time_remaining_seconds / 60
            collection['time_remaining_formatted'] = self.format_time_from_seconds(time_remaining_seconds)
            
        return collections
    
    def create_plot(self, challenge_id: str, member_id: str, visible_entries: List[str] = None, ranking_type: str = 'total', time_zoom_minutes: int = 1440) -> Dict:
        """Créer le graphique interactif avec Plotly et retourner JSON"""
        if visible_entries is None:
            visible_entries = ['Entry_0', 'Entry_1', 'Entry_2', 'Entry_3']
        
        # Fins corrigées pour les challenges spécifiques
        if challenge_id == "105594":  # By the Waterside
            challenge_end = datetime(2025, 8, 11, 16, 10, 0, tzinfo=PARIS_TZ)
        elif challenge_id == "105607":  # Rotated
            challenge_end = datetime(2025, 8, 12, 12, 52, 37, tzinfo=PARIS_TZ)
        else:
            # Estimation générique - utiliser la dernière donnée + petit buffer
            challenge_end = now_paris() + timedelta(days=1)
        
        # Récupérer les données
        collections = self.get_member_data(challenge_id, member_id)
        collections = self.calculate_time_remaining(collections, challenge_end)
        
        if not collections:
            return None
        
        # Trier par temps
        collections.sort(key=lambda x: x['time_remaining_total_minutes'], reverse=True)
        
        # Filtrer par zoom temporel si spécifié
        if time_zoom_minutes < 1440:  # Moins de 24h = appliquer le zoom
            filtered_collections = [c for c in collections if c['time_remaining_total_minutes'] <= time_zoom_minutes]
            if filtered_collections:
                collections = filtered_collections
            else:
                # Si pas de données dans la période zoomée, prendre les plus récentes
                collections = collections[:min(10, len(collections))]
        
        # Créer les sous-graphiques avec Plotly
        fig = sp.make_subplots(
            rows=3, cols=1,
            subplot_titles=[
                f'Évolution Votes et {"Ranking Général" if ranking_type == "total" else "Ranking par Photo"}',
                'Visualisation par Entries - Chaque couleur = une photo ID',
                '🎯 Rankings Dernières 10 Minutes'
            ],
            specs=[[{"secondary_y": True}], [{}], [{}]],
            vertical_spacing=0.08
        )
        
        # Titre principal
        zoom_text = f"Zoom {time_zoom_minutes}min" if time_zoom_minutes < 1440 else "Vue complète"
        ranking_text = "Ranking Général" if ranking_type == 'total' else "Ranking par Photo"
        fig.update_layout(
            title=f'🎯 Analyse GuruShots Interactive - {ranking_text} - {zoom_text}',
            title_x=0.5,
            height=1200,
            showlegend=True
        )
        
        # GRAPHIQUE 1: Overview avec ranking
        times = [c['time_remaining_total_minutes'] for c in collections]
        votes = [c['total_votes'] for c in collections]
        ranks = [c['total_rank'] for c in collections]
        
        # Formatage des temps pour hover - utiliser les temps formatés depuis la DB
        time_labels = []
        for collection in collections:
            if 'time_remaining_formatted' in collection:
                time_labels.append(collection['time_remaining_formatted'])
            else:
                # Fallback si pas de formatage
                t = collection['time_remaining_total_minutes']
                if t < 60:
                    time_labels.append(f"{t:.1f}min")
                else:
                    h = int(t // 60)
                    m = int(t % 60)
                    time_labels.append(f"{h}h{m:02d}")
        
        # Votes (axe principal)
        fig.add_trace(
            go.Scatter(
                x=times, y=votes,
                mode='lines+markers',
                name='Votes Totaux',
                line=dict(color='#2E86DE', width=3),
                marker=dict(size=8),
                hovertemplate='<b>Votes:</b> %{y}<br><b>Temps restant:</b> %{customdata}<extra></extra>',
                customdata=time_labels
            ),
            row=1, col=1
        )
        
        # Rankings (axe secondaire)
        fig.add_trace(
            go.Scatter(
                x=times, y=ranks,
                mode='lines+markers',
                name=f'{ranking_text}',
                line=dict(color='#E74C3C', width=3),
                marker=dict(size=8, symbol='square'),
                hovertemplate=f'<b>{ranking_text}:</b> %{{y}}<br><b>Temps restant:</b> %{{customdata}}<extra></extra>',
                customdata=time_labels,
                yaxis='y2'
            ),
            row=1, col=1, secondary_y=True
        )
        
        # GRAPHIQUE 2: Entries par photo avec événements
        self.create_plotly_entries_plot(fig, collections, visible_entries, ranking_type)
        
        # GRAPHIQUE 3: Analyse finale
        self.create_plotly_final_minutes_analysis(fig, collections, challenge_end)
        
        # Ajouter les annotations d'événements majeurs
        self.add_event_annotations(fig, collections, member_id)
        
        # Configuration des axes avec étiquettes personnalisées
        # Créer des ticks personnalisés pour l'axe X
        x_ticks = self.create_readable_x_ticks(times)
        
        fig.update_xaxes(
            title_text="⏰ Temps restant avant la fin",
            autorange="reversed",  # Inverser l'axe X
            tickvals=x_ticks['values'],
            ticktext=x_ticks['labels'],
            tickangle=45,  # Angle pour éviter la superposition
            row=1, col=1
        )
        fig.update_yaxes(title_text="Votes Totaux", title_font_color="#2E86DE", row=1, col=1)
        fig.update_yaxes(
            title_text=ranking_text, 
            title_font_color="#E74C3C",
            autorange="reversed",  # Plus petit rank = mieux
            row=1, col=1, secondary_y=True
        )
        
        fig.update_xaxes(
            title_text="⏰ Temps restant avant la fin",
            autorange="reversed",
            tickvals=x_ticks['values'],
            ticktext=x_ticks['labels'],
            tickangle=45,
            row=2, col=1
        )
        fig.update_yaxes(title_text="Votes par Photo", row=2, col=1)
        
        fig.update_xaxes(
            title_text="⏰ Temps restant avant la fin",
            autorange="reversed",
            tickvals=x_ticks['values'],
            ticktext=x_ticks['labels'],
            tickangle=45,
            row=3, col=1
        )
        fig.update_yaxes(
            title_text="Ranking Global (1 = Meilleur)",
            autorange="reversed",
            row=3, col=1
        )
        
        # Configuration générale pour zoom et interactivité
        fig.update_layout(
            hovermode='x unified',
            dragmode='pan',
            template='plotly_white'
        )
        
        # Retourner le JSON du graphique
        return json.loads(json.dumps(fig, cls=PlotlyJSONEncoder))
    
    def create_plotly_entries_plot(self, fig, collections: List[Dict], visible_entries: List[str], ranking_type: str = 'total'):
        """Créer le graphique des entries avec Plotly"""
        times = [c['time_remaining_total_minutes'] for c in collections]
        
        # Collecter toutes les photos pour les couleurs
        all_photos = set()
        for collection in collections:
            for entry in collection['entries']:
                if entry and entry['photo_id']:
                    all_photos.add(entry['photo_id'])
        
        # Pré-générer les couleurs
        for photo_id in all_photos:
            self.color_manager.get_color_for_photo(photo_id)
        
        # Créer les lignes pour chaque entry visible
        for entry_idx in range(4):
            entry_name = f"Entry_{entry_idx}"
            
            if entry_name not in visible_entries:
                continue
                
            # Extraire les données de cette entry
            entry_times = []
            entry_votes = []
            entry_photos = []
            
            for collection in collections:
                current_entry = collection['entries'][entry_idx]
                if current_entry and current_entry['photo_id']:
                    entry_times.append(collection['time_remaining_total_minutes'])
                    entry_votes.append(current_entry['votes'])
                    entry_photos.append(current_entry['photo_id'])
            
            if not entry_times:
                continue
            
            # Grouper par photo ID pour créer des segments colorés
            photo_segments = {}
            for i, photo_id in enumerate(entry_photos):
                if photo_id not in photo_segments:
                    photo_segments[photo_id] = {'x': [], 'y': [], 'times': []}
                photo_segments[photo_id]['x'].append(entry_times[i])
                photo_segments[photo_id]['y'].append(entry_votes[i])
                # Utiliser le formatage du temps
                time_min = entry_times[i]
                time_formatted = self.format_time_from_seconds(int(time_min * 60))
                photo_segments[photo_id]['times'].append(time_formatted)
            
            # Ajouter chaque segment avec sa couleur unique
            for photo_id, segment_data in photo_segments.items():
                color = self.color_manager.get_color_for_photo(photo_id)
                fig.add_trace(
                    go.Scatter(
                        x=segment_data['x'], 
                        y=segment_data['y'],
                        mode='lines+markers',
                        name=f'{entry_name} - {photo_id[:8]}...',
                        line=dict(color=color, width=3),
                        marker=dict(size=8, color=color),
                        hovertemplate=f'<b>{entry_name}</b><br><b>Photo:</b> {photo_id}<br><b>Votes:</b> %{{y}}<br><b>Temps:</b> %{{customdata}}<extra></extra>',
                        customdata=segment_data['times'],
                        showlegend=True
                    ),
                    row=2, col=1
                )
    
    def create_plotly_final_minutes_analysis(self, fig, collections: List[Dict], challenge_end: datetime):
        """Analyse des rankings dans les 10 dernières minutes avec Plotly"""
        
        # Filtrer les données des 10 dernières minutes
        final_minutes_data = [c for c in collections if c['time_remaining_total_minutes'] <= 10]
        
        if len(final_minutes_data) < 2:
            # Ajouter un texte d'information
            fig.add_annotation(
                text="Pas assez de données dans les 10 dernières minutes",
                xref="x3", yref="y3",
                x=5, y=50,
                showarrow=False,
                font=dict(size=16, color="red"),
                row=3, col=1
            )
            return
        
        # Calculer les rankings pour chaque photo dans le challenge global
        photo_rankings = self.calculate_photo_rankings_in_final_minutes(final_minutes_data)
        
        # Couleurs pour les entries
        entry_colors = ['#e74c3c', '#2ecc71', '#3498db', '#f39c12']  # Rouge, Vert, Bleu, Orange
        
        # Tracer l'évolution des rankings pour chaque entry
        for entry_idx in range(4):
            entry_name = f"Entry_{entry_idx}"
            entry_times = []
            entry_rankings = []
            entry_photos = []
            time_labels = []
            
            for collection in final_minutes_data:
                current_entry = collection['entries'][entry_idx]
                if current_entry and current_entry['photo_id']:
                    photo_id = current_entry['photo_id']
                    time_remaining = collection['time_remaining_total_minutes']
                    
                    # Trouver le ranking de cette photo à ce moment
                    if photo_id in photo_rankings and time_remaining in photo_rankings[photo_id]:
                        ranking = photo_rankings[photo_id][time_remaining]
                        entry_times.append(time_remaining)
                        entry_rankings.append(ranking)
                        entry_photos.append(photo_id)
                        time_labels.append(self.format_time_from_seconds(int(time_remaining * 60)))
            
            if entry_times:
                color = entry_colors[entry_idx]
                fig.add_trace(
                    go.Scatter(
                        x=entry_times, 
                        y=entry_rankings,
                        mode='lines+markers',
                        name=f'{entry_name} Ranking',
                        line=dict(color=color, width=3),
                        marker=dict(size=10, color=color),
                        hovertemplate=f'<b>{entry_name}</b><br><b>Ranking:</b> %{{y}}<br><b>Temps:</b> %{{customdata}}<br><b>Photo:</b> %{{text}}<extra></extra>',
                        customdata=time_labels,
                        text=entry_photos,
                        showlegend=True
                    ),
                    row=3, col=1
                )
        
        # Analyser et marquer les zones de danger
        danger_zones = self.detect_optimal_voting_timing(final_minutes_data)
        optimal_timing = self.calculate_optimal_voting_timing(danger_zones)
        
        # Marquer les zones de danger avec des rectangles
        for zone in danger_zones:
            fig.add_shape(
                type="rect",
                x0=zone['start_time'], y0=0,
                x1=zone['end_time'], y1=100,
                fillcolor="red", opacity=0.2,
                layer="below", line_width=0,
                row=3, col=1
            )
        
        # Ajouter conseil stratégique
        if optimal_timing:
            fig.add_annotation(
                text=f"⚡ TIMING OPTIMAL: Voter après {optimal_timing:.1f}min de la fin",
                xref="x3", yref="paper",
                x=5, y=0.02,
                showarrow=False,
                font=dict(size=12, color="blue"),
                bgcolor="lightblue",
                bordercolor="blue",
                borderwidth=1,
                row=3, col=1
            )
    
    def add_event_annotations(self, fig, collections: List[Dict], member_id: str):
        """Ajouter des annotations pour les événements majeurs (submits, swaps, boosts)"""
        events = self.detect_major_events(collections)
        
        for event in events:
            time_remaining = event['time_remaining']
            event_type = event['type']
            description = event['description']
            
            # Couleurs par type d'événement
            color_map = {
                'submit': '#FF6B6B',      # Rouge pour submits
                'swap': '#4ECDC4',        # Turquoise pour swaps  
                'boost': '#FFE66D',       # Jaune pour boosts
                'major_gain': '#95E1D3'   # Vert pour gains majeurs
            }
            
            color = color_map.get(event_type, '#95A5A6')
            
            # Ajouter ligne verticale sur graphique 1 (overview)
            fig.add_vline(
                x=time_remaining,
                line=dict(color=color, width=2, dash="dash"),
                opacity=0.7,
                row=1, col=1
            )
            
            # Ajouter ligne verticale sur graphique 2 (entries)  
            fig.add_vline(
                x=time_remaining,
                line=dict(color=color, width=2, dash="dash"),
                opacity=0.7,
                row=2, col=1
            )
            
            # Annotation sur graphique 1
            fig.add_annotation(
                x=time_remaining,
                y=event.get('votes', 0),
                text=f"📍 {description}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor=color,
                bgcolor="white",
                bordercolor=color,
                borderwidth=1,
                font=dict(size=10, color="black"),
                row=1, col=1
            )
    
    def detect_major_events(self, collections: List[Dict]) -> List[Dict]:
        """Détecter les événements majeurs dans les collections"""
        events = []
        
        if not collections:
            return events
        
        # Trier par temps décroissant
        sorted_collections = sorted(collections, key=lambda x: x['time_remaining_total_minutes'], reverse=True)
        
        # Détecter les submits de nouvelles photos
        photo_first_seen = {}
        for i, collection in enumerate(sorted_collections):
            for entry in collection['entries']:
                if entry and entry['photo_id']:
                    photo_id = entry['photo_id']
                    if photo_id not in photo_first_seen:
                        photo_first_seen[photo_id] = {
                            'time': collection['time_remaining_total_minutes'],
                            'time_formatted': collection.get('time_remaining_formatted', ''),
                            'votes': collection['total_votes'],
                            'collection_index': i
                        }
        
        # Ajouter les submits comme événements
        for photo_id, first_occurrence in photo_first_seen.items():
            events.append({
                'type': 'submit',
                'time_remaining': first_occurrence['time'],
                'description': f"📸 Submit {first_occurrence['time_formatted']}",
                'votes': first_occurrence['votes'],
                'photo_id': photo_id
            })
        
        # Détecter les gains de votes majeurs (>200 en une collecte)
        for i in range(len(sorted_collections) - 1):
            current = sorted_collections[i]
            next_col = sorted_collections[i + 1]
            
            vote_gain = next_col['total_votes'] - current['total_votes']
            
            if vote_gain >= 200:  # Gain majeur
                events.append({
                    'type': 'major_gain',
                    'time_remaining': next_col['time_remaining_total_minutes'],
                    'description': f"🚀 +{vote_gain}v {next_col.get('time_remaining_formatted', '')}",
                    'votes': next_col['total_votes']
                })
        
        # Détecter les boosts (boost_timestamp != -1)
        for collection in sorted_collections:
            for entry in collection['entries']:
                if entry and entry.get('boost_timestamp', -1) != -1:
                    events.append({
                        'type': 'boost',
                        'time_remaining': collection['time_remaining_total_minutes'],
                        'description': f"⚡ Boost {collection.get('time_remaining_formatted', '')}",
                        'votes': collection['total_votes'],
                        'photo_id': entry['photo_id']
                    })
                    break  # Un seul boost par collection
        
        # Supprimer les doublons et trier
        unique_events = []
        seen_times = set()
        for event in events:
            time_key = f"{event['type']}_{event['time_remaining']:.1f}"
            if time_key not in seen_times:
                seen_times.add(time_key)
                unique_events.append(event)
        
        return sorted(unique_events, key=lambda x: x['time_remaining'], reverse=True)
    
    def calculate_photo_rankings_in_final_minutes(self, final_minutes_data: List[Dict]) -> Dict:
        """Calculer les rankings des photos du membre - Utilisation des rankings déjà disponibles"""
        photo_rankings = {}
        
        # Utiliser les rankings déjà stockés dans photo_snapshots.rank
        for collection in final_minutes_data:
            time_remaining = collection['time_remaining_total_minutes']
            
            for entry in collection['entries']:
                if entry and entry['photo_id'] and entry.get('rank'):
                    photo_id = entry['photo_id']
                    rank = entry['rank']  # Utiliser le ranking déjà calculé
                    
                    if photo_id not in photo_rankings:
                        photo_rankings[photo_id] = {}
                    photo_rankings[photo_id][time_remaining] = rank
        
        return photo_rankings
    
    def detect_optimal_voting_timing(self, final_minutes_data: List[Dict]) -> List[Dict]:
        """ALGORITHME RÉVOLUTIONNAIRE: Détecter les zones où le ranking chute rapidement"""
        danger_zones = []
        
        # Analyser chaque photo pour détecter les chutes de ranking
        photo_rankings = self.calculate_photo_rankings_in_final_minutes(final_minutes_data)
        
        for photo_id, rankings_by_time in photo_rankings.items():
            if len(rankings_by_time) < 3:
                continue
            
            # Trier par temps décroissant
            times_rankings = sorted(rankings_by_time.items(), reverse=True)
            
            # Détecter les chutes rapides de ranking
            for i in range(len(times_rankings) - 2):
                time1, rank1 = times_rankings[i]
                time2, rank2 = times_rankings[i + 1]
                time3, rank3 = times_rankings[i + 2]
                
                # Critères de "danger zone" - SEUILS AJUSTÉS
                rank_drop = rank3 - rank1  # Augmentation du rang = chute de position
                time_span = time1 - time3  # Durée de la chute
                
                # Détection plus sensible pour capturer les patterns réels
                if rank_drop >= 5 and time_span <= 8:  # Chute de 5+ rangs en 8min max
                    danger_zones.append({
                        'photo_id': photo_id,
                        'start_time': time1,
                        'end_time': time3,
                        'rank_drop': rank_drop,
                        'duration': time_span
                    })
        
        return danger_zones
    
    def calculate_optimal_voting_timing(self, danger_zones: List[Dict]) -> float:
        """Calculer le timing optimal de vote basé sur les patterns détectés"""
        if not danger_zones:
            return None
        
        # Analyser la distribution des zones de danger
        danger_start_times = [zone['start_time'] for zone in danger_zones]
        
        if danger_start_times:
            # Le timing optimal est juste après la zone de danger la plus fréquente
            # Prendre la médiane des temps de début de danger + petit buffer
            danger_start_times.sort()
            median_danger_start = danger_start_times[len(danger_start_times) // 2]
            
            # Timing optimal = juste après le début de la zone de danger médiane
            optimal_timing = max(0.5, median_danger_start - 0.5)  # Au moins 30s de la fin
            return optimal_timing
        
        return None
    
    def generate_strategic_advice(self, danger_zones: List[Dict], optimal_timing: float) -> str:
        """Générer des conseils stratégiques basés sur l'analyse"""
        if not danger_zones:
            return "✅ Pas de zone de danger détectée\n💡 Vous pouvez voter à tout moment"
        
        advice = f"⚠️ {len(danger_zones)} zone(s) de danger détectée(s)\n"
        
        if optimal_timing:
            advice += f"🎯 TIMING OPTIMAL: Voter après {optimal_timing:.1f}min de la fin\n"
        
        # Analyser la sévérité des chutes
        max_drop = max(zone['rank_drop'] for zone in danger_zones)
        avg_duration = sum(zone['duration'] for zone in danger_zones) / len(danger_zones)
        
        if max_drop >= 5:
            advice += "🚨 ATTENTION: Chutes de ranking très sévères\n"
        elif max_drop >= 3:
            advice += "⚠️ Chutes de ranking modérées\n"
        
        advice += f"⏱️ Durée moyenne des chutes: {avg_duration:.1f}min"
        
        return advice
    

# Instance globale de l'analyzeur
analyzer = None

@app.route('/api/refresh-cache')
def refresh_cache():
    """Forcer le rechargement du cache de l'analyzer"""
    global analyzer
    analyzer = None  # Vider le cache
    return jsonify({"success": True, "message": "Cache refreshed"})

@app.route('/api/delete-challenge/<challenge_id>', methods=['DELETE'])
def delete_challenge(challenge_id):
    """Supprimer toutes les données d'un challenge de la base"""
    global analyzer
    
    try:
        analyzer_instance = get_analyzer()
        
        with analyzer_instance.get_connection() as conn:
            cursor = conn.cursor()
            
            # Compter les données avant suppression
            cursor.execute('SELECT COUNT(*) FROM snapshots WHERE challenge_id = ?', (challenge_id,))
            snapshots_count = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(DISTINCT ps.member_id) 
                FROM participant_snapshots ps 
                JOIN snapshots s ON ps.snapshot_id = s.id 
                WHERE s.challenge_id = ?
            ''', (challenge_id,))
            members_count = cursor.fetchone()[0]
            
            if snapshots_count == 0:
                return jsonify({
                    'success': False,
                    'error': f'Challenge {challenge_id} non trouvé dans la base'
                })
            
            # Supprimer dans l'ordre (contraintes de clés étrangères)
            
            # 1. Supprimer photo_snapshots liés aux snapshots de ce challenge
            cursor.execute('''
                DELETE FROM photo_snapshots 
                WHERE snapshot_id IN (
                    SELECT id FROM snapshots WHERE challenge_id = ?
                )
            ''', (challenge_id,))
            photo_snapshots_deleted = cursor.rowcount
            
            # 2. Supprimer participant_snapshots liés aux snapshots de ce challenge  
            cursor.execute('''
                DELETE FROM participant_snapshots 
                WHERE snapshot_id IN (
                    SELECT id FROM snapshots WHERE challenge_id = ?
                )
            ''', (challenge_id,))
            participant_snapshots_deleted = cursor.rowcount
            
            # 3. Supprimer events liés à ce challenge
            cursor.execute('DELETE FROM events WHERE challenge_id = ?', (challenge_id,))
            events_deleted = cursor.rowcount
            
            # 4. Supprimer snapshots du challenge
            cursor.execute('DELETE FROM snapshots WHERE challenge_id = ?', (challenge_id,))
            snapshots_deleted = cursor.rowcount
            
            # 5. Supprimer le challenge lui-même
            cursor.execute('DELETE FROM challenges WHERE id = ?', (challenge_id,))
            challenge_deleted = cursor.rowcount
            
            conn.commit()
            
        # Vider le cache pour forcer rechargement
        analyzer = None
        
        return jsonify({
            'success': True,
            'message': f'Challenge {challenge_id} supprimé avec succès',
            'deleted': {
                'snapshots': snapshots_deleted,
                'participant_snapshots': participant_snapshots_deleted,  
                'photo_snapshots': photo_snapshots_deleted,
                'events': events_deleted,
                'challenge': challenge_deleted,
                'members_affected': members_count
            }
        })
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': f'Erreur lors de la suppression: {str(e)}'
        })

def get_analyzer():
    global analyzer
    if analyzer is None:
        # Utiliser la base de données du collector adaptatif
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_paths = [
            os.path.join(base, 'data', 'gurushots_adaptive.db'),
            os.path.join(base, 'gurushots_adaptive.db'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gurushots_adaptive.db'),
        ]

        for db_path in db_paths:
            if os.path.exists(db_path):
                analyzer = WebGuruShotsAnalyzer(db_path)
                break

        if analyzer is None:
            raise Exception("Base de données GuruShots non trouvée")

    return analyzer

# ─────────────────────────────────────────────────────────────
#  Scheduler de collecte adaptative
# ─────────────────────────────────────────────────────────────

class MonitoringScheduler:
    """
    Collecte adaptative APScheduler — un job DateTrigger par challenge,
    se reprogramme lui-même après chaque collecte avec le bon intervalle.

    Rythme (GUIDE ADVANCED.md) :
      > 1h     → 15 min
      1h→5min  →  5 min
      5min→1min → 1 min
      < 1min   → 15 s
    """

    INTERVALS = [
        (60,           15),
        (300,          60),
        (3600,        300),
        (float('inf'), 900),
    ]

    def __init__(self):
        self._scheduler = BackgroundScheduler(
            jobstores={'default': MemoryJobStore()},
            executors={'default': APThreadPoolExecutor(max_workers=10)},
            job_defaults={'coalesce': True, 'max_instances': 1, 'misfire_grace_time': 10},
            timezone='UTC'
        )
        self._db_path = None
        self._monitored_ids = set()  # challenges actifs (indépendant des jobs APScheduler)

    # ── helpers ────────────────────────────────────────────────

    def get_interval(self, seconds_to_end):
        if seconds_to_end is None:
            return 900
        for threshold, interval in self.INTERVALS:
            if seconds_to_end < threshold:
                return interval
        return 900

    def _get_db_path(self):
        if self._db_path and os.path.exists(self._db_path):
            return self._db_path
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for p in [
            os.path.join(base, 'data', 'gurushots_adaptive.db'),
            os.path.join(base, 'gurushots_adaptive.db'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gurushots_adaptive.db'),
        ]:
            if os.path.exists(p):
                self._db_path = p
                return p
        return None

    def _job_id(self, challenge_id):
        return f'challenge_{challenge_id}'

    # ── job APScheduler ────────────────────────────────────────

    def _collect_job(self, c_id, challenge_url):
        """Collecte un snapshot et reprogramme le prochain job."""
        db_path = self._get_db_path()
        if not db_path:
            return

        conn = None
        try:
            resp = http_requests.post(
                f'{GURUSHOTS_API}/get_challenge',
                data={'challenge_url': challenge_url},
                headers=GS_HEADERS,
                timeout=10
            )
            resp.raise_for_status()
            api_data = resp.json()

            if not api_data.get('success'):
                print(f'[APScheduler] API échec {c_id}: {api_data}')
                return

            challenge = api_data['challenge']
            new_status = 'active' if challenge.get('status') == 'active' else 'ended'
            now_iso = datetime.now(timezone.utc).isoformat()

            conn = sqlite3.connect(db_path)
            ensure_schema(conn)
            seconds_to_end = save_global_snapshot(conn, c_id, challenge, now_iso)
            conn.execute('UPDATE challenges SET status=?, updated_at=? WHERE c_id=?',
                         (new_status, now_iso, c_id))
            conn.commit()

            # Collecter les followings
            try:
                resp2 = http_requests.post(
                    f'{GURUSHOTS_API}/get_top_photographer',
                    data={'c_id': c_id, 'filter': 'following', 'init': 'true',
                          'limit_above': 150, 'limit_below': 150},
                    headers=GS_HEADERS, timeout=15
                )
                top_data = resp2.json()
                if top_data.get('success') and top_data.get('items'):
                    save_following_snapshot(conn, c_id, now_iso, top_data['items'])
            except Exception as e2:
                print(f'[APScheduler] get_top_photographer échec {c_id}: {e2}')

            conn.close()

            interval = self.get_interval(seconds_to_end)
            print(f'[APScheduler] {challenge.get("title","?")} | '
                  f'{seconds_to_end}s restant | '
                  f'{challenge.get("votes",0):,} votes | '
                  f'{challenge.get("players",0)} joueurs | '
                  f'prochain dans {interval}s')

            if new_status == 'active' and self._scheduler.running:
                next_run = datetime.now(timezone.utc) + timedelta(seconds=interval)
                self._scheduler.add_job(
                    func=self._collect_job,
                    trigger=DateTrigger(run_date=next_run, timezone='UTC'),
                    args=[c_id, challenge_url],
                    id=self._job_id(c_id),
                    name=f'Monitor {challenge.get("title", c_id)}',
                    replace_existing=True
                )
            else:
                self._monitored_ids.discard(str(c_id))
                print(f'[APScheduler] {challenge.get("title","?")} terminé — collecte stoppée')

        except Exception as e:
            print(f'[APScheduler] Erreur {c_id}: {e}')
            if conn:
                try: conn.close()
                except: pass
            # Reprogrammer quand même pour ne pas casser la collecte sur erreur réseau/API
            if str(c_id) in self._monitored_ids and self._scheduler.running:
                retry_in = 60  # réessayer dans 1 min
                next_run = datetime.now(timezone.utc) + timedelta(seconds=retry_in)
                try:
                    self._scheduler.add_job(
                        func=self._collect_job,
                        trigger=DateTrigger(run_date=next_run, timezone='UTC'),
                        args=[c_id, challenge_url],
                        id=self._job_id(c_id),
                        replace_existing=True
                    )
                    print(f'[APScheduler] Retry {c_id} dans {retry_in}s')
                except Exception as e2:
                    print(f'[APScheduler] Impossible de reprogrammer {c_id}: {e2}')

    # ── contrôle par challenge ─────────────────────────────────

    def start_challenge(self, challenge_id, challenge_url, title=''):
        """Démarrer immédiatement la collecte d'un challenge."""
        self._monitored_ids.add(str(challenge_id))
        self._scheduler.add_job(
            func=self._collect_job,
            trigger=DateTrigger(run_date=datetime.now(timezone.utc), timezone='UTC'),
            args=[challenge_id, challenge_url],
            id=self._job_id(challenge_id),
            name=f'Monitor {title or challenge_id}',
            replace_existing=True
        )
        print(f'[APScheduler] Démarré: {title or challenge_id}')

    def stop_challenge(self, challenge_id):
        """Stopper la collecte d'un challenge."""
        self._monitored_ids.discard(str(challenge_id))
        try:
            self._scheduler.remove_job(self._job_id(challenge_id))
            print(f'[APScheduler] Stoppé: {challenge_id}')
            return True
        except Exception:
            return False

    # ── contrôle global ───────────────────────────────────────

    def start_all(self):
        """Démarrer tous les challenges actifs présents en DB."""
        db_path = self._get_db_path()
        if not db_path:
            return 0
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c_id, url, title FROM challenges
                WHERE status = 'active' AND url IS NOT NULL AND url != ''
            """)
            rows = cursor.fetchall()
            conn.close()
        except sqlite3.OperationalError as e:
            print(f'[APScheduler] start_all: schéma obsolète ({e}) — cliquez sur Purge puis re-ajoutez les challenges')
            return 0
        for cid, url, title in rows:
            self.start_challenge(cid, url, title or cid)
        print(f'[APScheduler] {len(rows)} challenges démarrés au lancement')
        return len(rows)

    def stop_all(self):
        """Stopper tous les jobs de monitoring."""
        self._monitored_ids.clear()
        jobs = [j for j in self._scheduler.get_jobs()
                if j.id.startswith('challenge_')]
        for j in jobs:
            try: self._scheduler.remove_job(j.id)
            except: pass
        print(f'[APScheduler] {len(jobs)} challenges stoppés')
        return len(jobs)

    def get_status(self):
        """Statut de tous les jobs de collecte."""
        jobs = [j for j in self._scheduler.get_jobs()
                if j.id.startswith('challenge_')]
        return {
            'running': self._scheduler.running,
            'monitored_ids': list(self._monitored_ids),
            'total_challenges': len(self._monitored_ids),
            'jobs': [
                {
                    'id': j.id,
                    'challenge_id': j.id.replace('challenge_', ''),
                    'name': j.name,
                    'next_run': j.next_run_time.isoformat() if j.next_run_time else None,
                }
                for j in jobs
            ]
        }

    # ── cycle de vie ──────────────────────────────────────────

    def start(self):
        self._scheduler.start()
        print('[APScheduler] Scheduler démarré')
        self.start_all()

    def stop(self):
        self._scheduler.shutdown(wait=False)
        print('[APScheduler] Scheduler arrêté')

    @property
    def running(self):
        return self._scheduler.running


scheduler = MonitoringScheduler()


# Routes Flask
@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')

@app.route('/api/challenges')
def api_challenges():
    """API pour récupérer les challenges (snapshots détaillés + challenges global)"""
    try:
        analyzer_instance = get_analyzer()

        # Source 1 : challenges avec données détaillées (snapshots table)
        detailed = analyzer_instance.get_available_challenges()
        detailed_ids = {str(c['id']) for c in detailed}

        # Source 2 : challenges ajoutés via + (challenge_global_snapshots uniquement)
        with analyzer_instance.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.c_id, c.title, c.status,
                       COUNT(g.id) as snap_count,
                       MAX(g.timestamp) as last_snapshot
                FROM challenges c
                LEFT JOIN challenge_global_snapshots g ON g.c_id = c.c_id
                GROUP BY c.c_id
            """)
            for row in cursor.fetchall():
                cid, title, status, snap_count, last_snap = row
                if str(cid) not in detailed_ids:
                    detailed.append({
                        'id': cid,
                        'title': title or f'Challenge {cid}',
                        'status': status,
                        'snapshots': snap_count,
                        'members': 0,
                        'first_snapshot': None,
                        'last_snapshot': utc_to_paris(last_snap) if last_snap else None,
                        'data_source': 'global'
                    })

        return jsonify({'success': True, 'challenges': detailed})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/discover')
def api_discover():
    """API pour découvrir tous les challenges avec métadonnées enrichies"""
    try:
        analyzer_instance = get_analyzer()
        with analyzer_instance.get_connection() as conn:
            cursor = conn.cursor()

            query = """
            SELECT
                s.challenge_id AS id,
                COALESCE(c.title, 'Challenge ' || s.challenge_id) AS title,
                c.status AS monitored_status,
                CASE
                    WHEN MIN(s.seconds_to_end) <= 0 THEN 'ended'
                    ELSE 'active'
                END AS status,
                COUNT(s.id) AS snapshots,
                COUNT(DISTINCT ps.member_id) AS members,
                MAX(s.timestamp) AS last_snapshot,
                MIN(s.seconds_to_end) AS min_seconds_to_end,
                MAX(CASE WHEN ps.member_id = ? THEN 1 ELSE 0 END) AS is_mine,
                MIN(CASE WHEN ps.member_id = ? THEN ps.total_rank ELSE NULL END) AS best_rank
            FROM snapshots s
            LEFT JOIN participant_snapshots ps ON s.id = ps.snapshot_id
            LEFT JOIN challenges c ON s.challenge_id = c.id
            GROUP BY s.challenge_id
            HAVING snapshots > 10
            ORDER BY last_snapshot DESC
            """

            cursor.execute(query, (BRUNO_MEMBER_ID, BRUNO_MEMBER_ID))
            rows = cursor.fetchall()

            challenges = []
            for row in rows:
                cid, title, monitored_status, status, snapshots, members, last_snap, min_sec, is_mine, best_rank = row
                challenges.append({
                    'id': cid,
                    'title': title,
                    'status': status,
                    'monitored': monitored_status == 'active',
                    'is_mine': bool(is_mine),
                    'snapshots': snapshots,
                    'members': members,
                    'last_snapshot': utc_to_paris(last_snap) if last_snap else None,
                    'min_seconds_to_end': min_sec,
                    'best_rank': best_rank
                })

        return jsonify({'success': True, 'challenges': challenges})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/monitoring')
def api_monitoring():
    """API pour les challenges activement monitorés avec stats en temps réel"""
    try:
        analyzer_instance = get_analyzer()
        with analyzer_instance.get_connection() as conn:
            cursor = conn.cursor()

            # Récupérer les challenges avec status='active' dans la table challenges
            cursor.execute("""
                SELECT c.c_id, c.title
                FROM challenges c
                WHERE c.status = 'active'
            """)
            monitored = cursor.fetchall()

            now_str = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
            challenges = []

            for (cid, title) in monitored:
                # Stats depuis la table snapshots (collecte détaillée)
                cursor.execute("""
                    SELECT
                        COUNT(s.id) AS snapshots,
                        COUNT(DISTINCT ps.member_id) AS members,
                        MAX(s.timestamp) AS last_snapshot,
                        MIN(s.seconds_to_end) AS min_seconds_to_end
                    FROM snapshots s
                    LEFT JOIN participant_snapshots ps ON s.id = ps.snapshot_id
                    WHERE s.challenge_id = ?
                """, (cid,))
                stats_row = cursor.fetchone()
                snapshots = stats_row[0] if stats_row else 0
                members = stats_row[1] if stats_row else 0
                last_snap = stats_row[2] if stats_row else None
                min_sec = stats_row[3] if stats_row else None

                # Source de données et stats globales
                data_source = 'snapshots' if snapshots > 0 else 'global'
                total_votes_global = None
                players_global = None

                if snapshots == 0:
                    # Fallback : données agrégées sauvées via l'API GuruShots
                    cursor.execute("""
                        SELECT total_votes, players, seconds_to_end, timestamp
                        FROM challenge_global_snapshots
                        WHERE c_id = ?
                        ORDER BY id DESC LIMIT 1
                    """, (cid,))
                    gsnap = cursor.fetchone()
                    if gsnap:
                        total_votes_global, players_global, min_sec, last_snap = gsnap
                        members = players_global or 0
                    else:
                        data_source = 'none'

                # Calculer seconds_since_last
                try:
                    last_dt = datetime.fromisoformat(last_snap.replace('Z', '+00:00'))
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                    seconds_since_last = int((datetime.now(timezone.utc) - last_dt).total_seconds())
                except Exception:
                    seconds_since_last = None

                # Formatter le temps restant
                def fmt_time(sec):
                    if sec is None or sec <= 0:
                        return 'Terminé'
                    h = sec // 3600
                    m = (sec % 3600) // 60
                    if h > 0:
                        return f"{h}h{m:02d}m"
                    return f"{m}m"

                # Données Bruno dans le snapshot le plus récent
                cursor.execute("""
                    SELECT ps.total_rank, ps.total_votes
                    FROM participant_snapshots ps
                    JOIN snapshots s ON ps.snapshot_id = s.id
                    WHERE s.challenge_id = ? AND ps.member_id = ?
                    ORDER BY s.timestamp DESC
                    LIMIT 1
                """, (cid, BRUNO_MEMBER_ID))
                bruno_row = cursor.fetchone()
                is_mine = bruno_row is not None
                my_rank = bruno_row[0] if bruno_row else None
                my_votes = bruno_row[1] if bruno_row else None

                # Top 3 participants dans le snapshot le plus récent
                cursor.execute("""
                    SELECT ps.total_rank, COALESCE(m.name, 'Member_' || SUBSTR(ps.member_id,1,8)) AS name, ps.total_votes
                    FROM participant_snapshots ps
                    JOIN snapshots s ON ps.snapshot_id = s.id
                    LEFT JOIN members m ON ps.member_id = m.id
                    WHERE s.challenge_id = ?
                      AND s.id = (SELECT id FROM snapshots WHERE challenge_id = ? ORDER BY timestamp DESC LIMIT 1)
                    ORDER BY ps.total_rank ASC
                    LIMIT 3
                """, (cid, cid))
                top3_rows = cursor.fetchall()
                top3 = [{'rank': r[0], 'name': r[1], 'votes': r[2]} for r in top3_rows]

                challenges.append({
                    'id': cid,
                    'title': title,
                    'snapshots': snapshots,
                    'members': members,
                    'last_snapshot': utc_to_paris(last_snap) if last_snap else None,
                    'seconds_since_last': seconds_since_last,
                    'min_seconds_to_end': min_sec,
                    'time_remaining_formatted': fmt_time(min_sec),
                    'is_mine': is_mine,
                    'my_rank': my_rank,
                    'my_votes': my_votes,
                    'top3': top3,
                    'data_source': data_source,
                    'total_votes': total_votes_global,
                    'players': players_global
                })

            # Trier par temps restant croissant (les plus urgents en premier)
            challenges.sort(key=lambda x: x['min_seconds_to_end'] if x['min_seconds_to_end'] is not None else 999999999)

        # Enrichir avec l'état du scheduler (collecte active + prochain run)
        now_utc = datetime.now(timezone.utc)
        status = scheduler.get_status()
        monitored_ids = set(status.get('monitored_ids', []))
        jobs_by_cid = {}
        for j in status.get('jobs', []):
            cid = j['challenge_id']
            next_in = None
            if j.get('next_run'):
                try:
                    nr = j['next_run'].replace('Z', '').split('+')[0]
                    next_in = max(0, int((datetime.fromisoformat(nr) - now_utc).total_seconds()))
                except Exception:
                    pass
            jobs_by_cid[cid] = next_in

        for c in challenges:
            cid = str(c['id'])
            c['is_collecting'] = cid in monitored_ids
            c['next_collection_in'] = jobs_by_cid.get(cid)  # None si job en cours d'exécution

        return jsonify({'success': True, 'challenges': challenges})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def ensure_schema(conn):
    """Créer toutes les tables gérées par ce module si elles n'existent pas"""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS challenges (
            c_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT,
            status TEXT,
            start_time INTEGER,
            close_time INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS challenge_global_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            c_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            total_votes INTEGER,
            players INTEGER,
            seconds_to_end INTEGER,
            status TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS followings (
            member_id TEXT PRIMARY KEY,
            name TEXT,
            country_code TEXT,
            member_status_name TEXT,
            updated_at TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS following_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            c_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            member_id TEXT NOT NULL,
            total_votes INTEGER,
            total_rank INTEGER,
            level_name TEXT,
            percent REAL,
            guru_picks INTEGER
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS following_photo_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            following_snapshot_id INTEGER NOT NULL,
            photo_id TEXT,
            member_id TEXT,
            votes INTEGER,
            rank INTEGER,
            boost INTEGER
        )
    ''')
    conn.commit()


def save_global_snapshot(conn, c_id, challenge_data, now_iso):
    """Sauvegarder un snapshot agrégé depuis la réponse de l'API GuruShots"""
    time_left = challenge_data.get('time_left', {})
    seconds_to_end = (
        time_left.get('days', 0) * 86400 +
        time_left.get('hours', 0) * 3600 +
        time_left.get('minutes', 0) * 60 +
        time_left.get('seconds', 0)
    )
    conn.execute('''
        INSERT INTO challenge_global_snapshots (c_id, timestamp, total_votes, players, seconds_to_end, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        c_id,
        now_iso,
        challenge_data.get('votes', 0),
        challenge_data.get('players', 0),
        seconds_to_end,
        challenge_data.get('status', 'active')
    ))
    conn.commit()
    return seconds_to_end


def save_following_snapshot(conn, c_id, now_iso, items):
    """Sauvegarder les snapshots des followings depuis get_top_photographer"""
    for item in items:
        member = item.get('member', {})
        total = item.get('total', {})
        member_id = member.get('id')
        if not member_id:
            continue

        # Upsert dans followings
        conn.execute('''
            INSERT INTO followings (member_id, name, country_code, member_status_name, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(member_id) DO UPDATE SET
                name=excluded.name,
                country_code=excluded.country_code,
                member_status_name=excluded.member_status_name,
                updated_at=excluded.updated_at
        ''', (
            member_id,
            member.get('name'),
            member.get('country_code'),
            member.get('member_status_name'),
            now_iso
        ))

        # INSERT dans following_snapshots
        cursor = conn.execute('''
            INSERT INTO following_snapshots
                (c_id, timestamp, member_id, total_votes, total_rank, level_name, percent, guru_picks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            c_id,
            now_iso,
            member_id,
            total.get('votes'),
            total.get('rank'),
            total.get('level_name'),
            total.get('percent'),
            total.get('guru_picks')
        ))
        following_snapshot_id = cursor.lastrowid

        # INSERT dans following_photo_snapshots pour chaque entry
        for entry in item.get('entries', []):
            conn.execute('''
                INSERT INTO following_photo_snapshots
                    (following_snapshot_id, photo_id, member_id, votes, rank, boost)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                following_snapshot_id,
                entry.get('id'),
                member_id,
                entry.get('votes'),
                entry.get('rank'),
                entry.get('boost')
            ))

    conn.commit()


@app.route('/api/add-challenge', methods=['POST'])
def api_add_challenge():
    """Ajouter un challenge via son URL GuruShots"""
    try:
        data = request.json or {}
        challenge_url = (data.get('challenge_url') or '').strip()
        if not challenge_url:
            return jsonify({'success': False, 'error': 'challenge_url requis'})

        # Appel à l'API GuruShots
        try:
            resp = http_requests.post(
                f'{GURUSHOTS_API}/get_challenge',
                data={'challenge_url': challenge_url},
                timeout=10,
                headers=GS_HEADERS
            )
            resp.raise_for_status()
            api_data = resp.json()
        except http_requests.RequestException as e:
            return jsonify({'success': False, 'error': f'Erreur API GuruShots: {str(e)}'})

        if not api_data.get('success'):
            return jsonify({'success': False, 'error': f'API GuruShots: {api_data}'})

        challenge = api_data['challenge']
        c_id = int(challenge['id'])
        title = challenge.get('title', challenge_url)
        url = challenge.get('url', challenge_url)
        close_time = challenge.get('close_time')
        start_time = challenge.get('start_time')
        status = challenge.get('status', 'active')

        now = datetime.now(timezone.utc).isoformat()

        analyzer_instance = get_analyzer()
        with analyzer_instance.get_connection() as conn:
            ensure_schema(conn)

            conn.execute('''
                INSERT INTO challenges (c_id, title, url, status, start_time, close_time, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(c_id) DO UPDATE SET
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    title=excluded.title
            ''', (c_id, title, url,
                  'active' if status == 'active' else 'ended',
                  start_time, close_time, now, now))

            seconds_to_end = save_global_snapshot(conn, c_id, challenge, now)

        # Démarrer la collecte adaptative si le challenge est actif
        if status == 'active' and scheduler.running:
            scheduler.start_challenge(c_id, url, title)

        return jsonify({
            'success': True,
            'challenge': {
                'id': c_id,
                'title': title,
                'players': challenge.get('players', 0),
                'votes': challenge.get('votes', 0),
                'seconds_to_end': seconds_to_end,
                'time_left': challenge.get('time_left', {}),
                'status': status,
                'url': url
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/refresh-challenge/<challenge_id>', methods=['POST'])
def api_refresh_challenge(challenge_id):
    """Rafraîchir un challenge depuis l'API GuruShots et sauvegarder un nouveau snapshot"""
    try:
        c_id = int(challenge_id)
        analyzer_instance = get_analyzer()
        with analyzer_instance.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT url, title FROM challenges WHERE c_id = ?', (c_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'success': False, 'error': 'Challenge introuvable'})
            challenge_url, title = row

        if not challenge_url:
            return jsonify({'success': False, 'error': 'URL du challenge inconnue'})

        try:
            resp = http_requests.post(
                f'{GURUSHOTS_API}/get_challenge',
                data={'challenge_url': challenge_url},
                timeout=10,
                headers=GS_HEADERS
            )
            resp.raise_for_status()
            api_data = resp.json()
        except http_requests.RequestException as e:
            return jsonify({'success': False, 'error': f'Erreur API GuruShots: {str(e)}'})

        if not api_data.get('success'):
            return jsonify({'success': False, 'error': 'Erreur API GuruShots'})

        challenge = api_data['challenge']
        now = datetime.now(timezone.utc).isoformat()
        new_status = 'active' if challenge.get('status') == 'active' else 'ended'

        with analyzer_instance.get_connection() as conn:
            conn.execute(
                'UPDATE challenges SET status = ?, updated_at = ? WHERE c_id = ?',
                (new_status, now, c_id)
            )
            seconds_to_end = save_global_snapshot(conn, c_id, challenge, now)

            # Collecter les followings
            try:
                resp2 = http_requests.post(
                    f'{GURUSHOTS_API}/get_top_photographer',
                    data={'c_id': c_id, 'filter': 'following', 'init': 'true',
                          'limit_above': 150, 'limit_below': 150},
                    headers=GS_HEADERS, timeout=15
                )
                top_data = resp2.json()
                if top_data.get('success') and top_data.get('items'):
                    save_following_snapshot(conn, c_id, now, top_data['items'])
            except Exception as e2:
                print(f'[refresh] get_top_photographer échec {c_id}: {e2}')

        return jsonify({
            'success': True,
            'challenge': {
                'id': c_id,
                'title': challenge.get('title', title),
                'players': challenge.get('players', 0),
                'votes': challenge.get('votes', 0),
                'seconds_to_end': seconds_to_end,
                'time_left': challenge.get('time_left', {}),
                'status': challenge.get('status', 'active')
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/members/<challenge_id>')
def api_members(challenge_id):
    """API pour récupérer les membres d'un challenge"""
    try:
        members = get_analyzer().get_challenge_members(challenge_id)
        return jsonify({
            'success': True,
            'members': members
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """API pour générer le graphique d'analyse"""
    try:
        data = request.json
        challenge_id = data.get('challenge_id')
        member_id = data.get('member_id')
        visible_entries = data.get('visible_entries', ['Entry_0', 'Entry_1', 'Entry_2', 'Entry_3'])
        ranking_type = data.get('ranking_type', 'total')
        time_zoom_minutes = data.get('time_zoom_minutes', 1440)
        
        if not challenge_id or not member_id:
            return jsonify({
                'success': False,
                'error': 'challenge_id et member_id requis'
            })
        
        plot_data = get_analyzer().create_plot(challenge_id, member_id, visible_entries, ranking_type, time_zoom_minutes)
        
        if plot_data:
            return jsonify({
                'success': True,
                'plotly_json': plot_data
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Aucune donnée trouvée pour ce membre'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/ultra-precision/<challenge_id>')
def api_ultra_precision(challenge_id):
    """API pour récupérer l'analyse ultra-précise d'un challenge"""
    try:
        analyzer = get_analyzer()
        
        # Récupérer les événements critiques
        with analyzer.get_connection() as conn:
            cursor = conn.cursor()
            
            # Événements des 10 dernières minutes avec timing ultra-précis
            query = """
            SELECT 
                s.timestamp,
                s.seconds_to_end,
                ps.member_id,
                COALESCE(m.name, 'Member_' || SUBSTR(ps.member_id, 1, 8)) as name,
                ps.total_votes,
                ps.total_rank,
                LAG(ps.total_votes) OVER (PARTITION BY ps.member_id ORDER BY s.seconds_to_end DESC) as prev_votes,
                LAG(ps.total_rank) OVER (PARTITION BY ps.member_id ORDER BY s.seconds_to_end DESC) as prev_rank
            FROM snapshots s
            JOIN participant_snapshots ps ON s.id = ps.snapshot_id
            LEFT JOIN members m ON ps.member_id = m.id
            WHERE s.challenge_id = ?
              AND s.seconds_to_end <= 600
            ORDER BY s.seconds_to_end DESC, ps.total_rank ASC
            """
            
            cursor.execute(query, (challenge_id,))
            raw_data = cursor.fetchall()
            
            # Analyser les événements critiques
            events = []
            for row in raw_data:
                timestamp, seconds_to_end, member_id, name, votes, rank, prev_votes, prev_rank = row
                
                if prev_votes is not None and prev_rank is not None:
                    vote_change = votes - prev_votes
                    rank_change = prev_rank - rank
                    
                    if abs(vote_change) >= 50 or abs(rank_change) >= 3:
                        # Déterminer la phase temporelle
                        if seconds_to_end <= 60:
                            phase = "🔥 ULTRA_PRECISION (15s)"
                        elif seconds_to_end <= 900:
                            phase = "⚠️ JUAN_RODRIGUEZ_PHASE (1min)"
                        elif seconds_to_end <= 3600:
                            phase = "📊 HEIGHTENED_SURVEILLANCE (5min)"
                        else:
                            phase = "📈 STANDARD_MONITORING (15min)"
                        
                        events.append({
                            'member': name,
                            'member_id': member_id,
                            'timestamp': utc_to_paris(timestamp) if timestamp else None,
                            'seconds_to_end': seconds_to_end,
                            'time_formatted': analyzer.format_time_from_seconds(seconds_to_end),
                            'vote_change': vote_change,
                            'rank_change': rank_change,
                            'new_rank': rank,
                            'new_votes': votes,
                            'phase': phase,
                            'event_type': 'major_gain' if vote_change > 0 else 'major_loss'
                        })
            
            # Trier par importance (changement de votes)
            events.sort(key=lambda x: abs(x['vote_change']), reverse=True)
            
            return jsonify({
                'success': True,
                'challenge_id': challenge_id,
                'critical_events': events[:20],  # Top 20 événements
                'total_events': len(events),
                'analysis_type': 'ultra_precision_15s'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/scheduler/status')
def api_scheduler_status():
    """Statut du scheduler APScheduler"""
    return jsonify({'success': True, **scheduler.get_status()})


@app.route('/api/scheduler/start-all', methods=['POST'])
def api_scheduler_start_all():
    """Démarrer la collecte de tous les challenges actifs"""
    count = scheduler.start_all()
    return jsonify({'success': True, 'started': count})


@app.route('/api/scheduler/stop-all', methods=['POST'])
def api_scheduler_stop_all():
    """Stopper la collecte de tous les challenges"""
    count = scheduler.stop_all()
    return jsonify({'success': True, 'stopped': count})


@app.route('/api/scheduler/start/<challenge_id>', methods=['POST'])
def api_scheduler_start(challenge_id):
    """Démarrer la collecte d'un challenge"""
    try:
        analyzer_instance = get_analyzer()
        with analyzer_instance.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT url, title FROM challenges WHERE id = ?', (challenge_id,))
            row = cursor.fetchone()
        if not row or not row[0]:
            return jsonify({'success': False, 'error': 'Challenge introuvable ou URL manquante'})
        url, title = row
        scheduler.start_challenge(challenge_id, url, title or challenge_id)
        return jsonify({'success': True, 'challenge_id': challenge_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/scheduler/stop/<challenge_id>', methods=['POST'])
def api_scheduler_stop(challenge_id):
    """Stopper la collecte d'un challenge"""
    stopped = scheduler.stop_challenge(challenge_id)
    return jsonify({'success': True, 'stopped': stopped, 'challenge_id': challenge_id})


@app.route('/api/ended-challenges')
def api_ended_challenges():
    """Challenges terminés avec leurs stats finales depuis challenge_global_snapshots"""
    try:
        analyzer_instance = get_analyzer()
        with analyzer_instance.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.c_id, c.title, c.url, c.close_time, c.updated_at,
                       g.total_votes, g.players, g.timestamp as last_snapshot
                FROM challenges c
                LEFT JOIN challenge_global_snapshots g ON g.id = (
                    SELECT id FROM challenge_global_snapshots
                    WHERE c_id = c.c_id ORDER BY id DESC LIMIT 1
                )
                WHERE c.status = 'ended'
                ORDER BY c.updated_at DESC
            """)
            rows = cursor.fetchall()

        ended = []
        for row in rows:
            cid, title, url, end_time, updated_at, total_votes, players, last_snap = row
            ended.append({
                'id': cid,
                'title': title or f'Challenge {cid}',
                'url': url,
                'end_time': utc_to_paris(end_time) if end_time else None,
                'updated_at': utc_to_paris(updated_at) if updated_at else None,
                'total_votes': total_votes,
                'players': players,
                'last_snapshot': utc_to_paris(last_snap) if last_snap else None,
            })

        return jsonify({'success': True, 'challenges': ended})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/followings/<challenge_id>/member/<member_id>/photos')
def api_member_photo_history(challenge_id, member_id):
    """Historique des votes par photo pour un following sur un challenge"""
    try:
        c_id = int(challenge_id)
        analyzer_instance = get_analyzer()
        with analyzer_instance.get_connection() as conn:
            cursor = conn.cursor()

            # close_time du challenge pour calculer seconds_to_end
            cursor.execute('SELECT close_time FROM challenges WHERE c_id = ?', (c_id,))
            row = cursor.fetchone()
            close_time = row[0] if row else None

            # Tous les snapshots du membre sur ce challenge, ordonnés chronologiquement
            cursor.execute('''
                SELECT id, timestamp, total_votes, total_rank
                FROM following_snapshots
                WHERE c_id = ? AND member_id = ?
                ORDER BY timestamp ASC
            ''', (c_id, member_id))
            snapshots = cursor.fetchall()

            if not snapshots:
                return jsonify({'success': True, 'photos': {}, 'timestamps': []})

            # Pour chaque snapshot, récupérer les photos
            # Structure : {photo_id: [{ts, seconds_to_end, votes, rank, boosted}]}
            photos = {}
            all_timestamps = []

            for fs_id, ts, total_votes, total_rank in snapshots:
                # Calculer seconds_to_end depuis close_time - timestamp
                sec_to_end = None
                if close_time:
                    try:
                        from datetime import timezone
                        ts_dt = datetime.fromisoformat(ts.replace('Z', ''))
                        sec_to_end = max(0, int(close_time - ts_dt.replace(tzinfo=timezone.utc).timestamp()))
                    except Exception:
                        pass
                all_timestamps.append({'timestamp': utc_to_paris(ts) if ts else None, 'seconds_to_end': sec_to_end})
                cursor.execute('''
                    SELECT photo_id, votes, rank, boost
                    FROM following_photo_snapshots
                    WHERE following_snapshot_id = ?
                    ORDER BY rank ASC
                ''', (fs_id,))
                for photo_id, votes, rank, boost in cursor.fetchall():
                    if photo_id not in photos:
                        photos[photo_id] = []
                    photos[photo_id].append({
                        'timestamp': utc_to_paris(ts) if ts else None,
                        'seconds_to_end': sec_to_end,
                        'votes': votes,
                        'rank': rank,
                        'boosted': boost != -1 and boost is not None
                    })

            # Nom du membre
            cursor.execute('SELECT name FROM followings WHERE member_id = ?', (member_id,))
            row = cursor.fetchone()
            name = row[0] if row else member_id

        return jsonify({
            'success': True,
            'member_id': member_id,
            'name': name,
            'c_id': c_id,
            'photos': photos,
            'timestamps': all_timestamps
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/followings/<challenge_id>')
def api_followings(challenge_id):
    """Dernier snapshot followings d'un challenge + historique des rangs"""
    try:
        c_id = int(challenge_id)
        analyzer_instance = get_analyzer()
        with analyzer_instance.get_connection() as conn:
            cursor = conn.cursor()

            # Dernier timestamp de collecte following pour ce challenge
            cursor.execute('''
                SELECT MAX(timestamp) FROM following_snapshots WHERE c_id = ?
            ''', (c_id,))
            row = cursor.fetchone()
            last_ts = row[0] if row else None

            if not last_ts:
                return jsonify({'success': True, 'members': [], 'history': []})

            # Données du dernier snapshot par membre
            cursor.execute('''
                SELECT fs.id, fs.member_id, f.name, fs.total_votes, fs.total_rank,
                       fs.level_name, fs.percent, fs.guru_picks
                FROM following_snapshots fs
                JOIN followings f ON fs.member_id = f.member_id
                WHERE fs.c_id = ? AND fs.timestamp = ?
                ORDER BY fs.total_rank ASC
            ''', (c_id, last_ts))
            snap_rows = cursor.fetchall()

            members = []
            for fs_id, member_id, name, votes, rank, level, pct, guru_picks in snap_rows:
                # Photos du membre dans ce snapshot
                cursor.execute('''
                    SELECT photo_id, votes, rank, boost
                    FROM following_photo_snapshots
                    WHERE following_snapshot_id = ?
                    ORDER BY rank ASC
                ''', (fs_id,))
                photos = [
                    {'photo_id': p[0], 'votes': p[1], 'rank': p[2],
                     'boosted': p[3] != -1 and p[3] is not None}
                    for p in cursor.fetchall()
                ]
                members.append({
                    'member_id': member_id,
                    'name': name,
                    'total_votes': votes,
                    'total_rank': rank,
                    'level_name': level,
                    'percent': round(pct, 1) if pct else None,
                    'guru_picks': guru_picks,
                    'photos': photos
                })

            # Historique des rangs (toutes les collectes, pour le graphique)
            cursor.execute('''
                SELECT fs.timestamp, fs.member_id, f.name, fs.total_rank, fs.total_votes
                FROM following_snapshots fs
                JOIN followings f ON fs.member_id = f.member_id
                WHERE fs.c_id = ?
                ORDER BY fs.timestamp ASC
            ''', (c_id,))
            history_rows = cursor.fetchall()

            # Grouper par timestamp
            from collections import defaultdict
            by_ts = defaultdict(list)
            for ts, mid, name, rank, votes in history_rows:
                by_ts[ts].append({'member_id': mid, 'name': name, 'rank': rank, 'votes': votes})
            history = [{'timestamp': utc_to_paris(ts) if ts else None, 'members': entries} for ts, entries in sorted(by_ts.items())]

        return jsonify({
            'success': True,
            'c_id': c_id,
            'last_snapshot': utc_to_paris(last_ts) if last_ts else None,
            'members': members,
            'history': history
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/monitoring/history/<challenge_id>')
def api_monitoring_history(challenge_id):
    """Historique des snapshots agrégés pour les graphiques"""
    try:
        analyzer_instance = get_analyzer()
        with analyzer_instance.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT timestamp, total_votes, players, seconds_to_end
                FROM challenge_global_snapshots
                WHERE c_id = ?
                ORDER BY id ASC
                LIMIT 200
            ''', (challenge_id,))
            rows = cursor.fetchall()

        snapshots = [
            {
                'timestamp': utc_to_paris(r[0]) if r[0] else None,
                'total_votes': r[1],
                'players': r[2],
                'seconds_to_end': r[3]
            }
            for r in rows
        ]
        return jsonify({'success': True, 'challenge_id': challenge_id, 'snapshots': snapshots})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/purge-tables', methods=['POST'])
def api_purge_tables():
    """Dropper et recréer les 5 tables gérées par ce module"""
    try:
        analyzer_instance = get_analyzer()
        tables = [
            'following_photo_snapshots',
            'following_snapshots',
            'followings',
            'challenge_global_snapshots',
            'challenges',
        ]
        with analyzer_instance.get_connection() as conn:
            for table in tables:
                conn.execute(f'DROP TABLE IF EXISTS {table}')
            conn.commit()
            ensure_schema(conn)
        return jsonify({'success': True, 'dropped': tables})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/delete-challenge/<challenge_id>', methods=['POST'])
def api_delete_challenge(challenge_id):
    """Supprimer toutes les données d'un challenge pour libérer de l'espace"""
    try:
        c_id = int(challenge_id)
    except ValueError:
        return jsonify({'success': False, 'error': 'c_id invalide'})
    try:
        # Stopper la collecte si active
        scheduler.stop_challenge(c_id)

        analyzer_instance = get_analyzer()
        with analyzer_instance.get_connection() as conn:
            # Tables nouvelles (c_id)
            conn.execute('DELETE FROM following_photo_snapshots WHERE following_snapshot_id IN (SELECT id FROM following_snapshots WHERE c_id=?)', (c_id,))
            conn.execute('DELETE FROM following_snapshots WHERE c_id=?', (c_id,))
            conn.execute('DELETE FROM challenge_global_snapshots WHERE c_id=?', (c_id,))
            # Tables anciennes (challenge_id = même valeur numérique)
            conn.execute('DELETE FROM photo_snapshots WHERE participant_snapshot_id IN (SELECT id FROM participant_snapshots WHERE snapshot_id IN (SELECT id FROM snapshots WHERE challenge_id=?))', (c_id,))
            conn.execute('DELETE FROM participant_snapshots WHERE snapshot_id IN (SELECT id FROM snapshots WHERE challenge_id=?)', (c_id,))
            conn.execute('DELETE FROM snapshots WHERE challenge_id=?', (c_id,))
            conn.execute('DELETE FROM challenges WHERE c_id=?', (c_id,))
            conn.commit()

        return jsonify({'success': True, 'c_id': c_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    # Démarrer le scheduler uniquement dans le process principal (pas le reloader werkzeug)
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        scheduler.start()
    print("🌐 Démarrage du serveur web GuruShots Analyzer")
    print("📊 Interface web disponible sur: http://localhost:5001")
    app.run(debug=True, host='0.0.0.0', port=5001)