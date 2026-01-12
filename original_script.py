from jellyfin_apiclient_python import JellyfinClient
import os
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from dotenv import load_dotenv

# Global cache for TMDB details to avoid redundant API calls
_tmdb_cache: Dict[str, Dict[str, Any]] = {}

# Configuration for filtering future releases
FILTER_FUTURE_RELEASES = True  # Set to False to include future releases in notifications

# Configuration for filtering recently released content
FILTER_RECENT_RELEASES = True  # Set to False to include recently released content in notifications
RECENT_RELEASE_MONTHS_CUTOFF = 3  # Don't alert for content released less than X months ago

# 50 7 * * * /usr/bin/python3 /home/jimmydore/plex-analyzer/jellyfin_monitor.py

# ============================================================================
# CONFIGURATION VARIABLES - MODIFY THESE FOR EASIER CUSTOMIZATION
# ============================================================================

# Content Protection Allow Lists
# Items in these lists will be protected from deletion or specific checks
CONTENT_ALLOWLIST = [
    "Silo",
    "The substance",
    "Memento",
    "The Father",
    "Zootopie",
    "Le chat potté 2",
    "Migration",
    "Astérix & Obélix : Mission Cléopâtre",
    "Le dernier samouraï",
    "Les incorruptibles",
    "La La Land",
    "Lord of war",
    "Kung fu panda",
    "Interstellar",
    "Le robot sauvage",
    "Prisoners",
    "Gone girl",
    "Comment c'est loin",
    "House of the Dragon",
    "Arcane",
    "enfer du pacifique",
    "Shōgun",
    "Chernobyl",
    "Spider-Man : Across the Spider-Verse",
    "Joker",
    "Gladiator",
    "Oppenheimer",
    "Dune",
    "Tenet",
    "The penguin",
    "Mad Max",
    "Les trois mousquetaires",
    "Le Seigneur des Anneaux",
    "La Liste de Schindler",
    "Les Choristes",
    "Shaun of the Dead",
    "Lucy",
    "Hunger Games",
    "Tu ne tueras point",
    "The fall guy",
    "John Wick",
    "Le Prestige",
    "Hot Fuzz",
    "Night Call",
    "Paul",
    "Intouchables",
    "L'Exoconférence",
    "Vice-versa",
    "Élémentaire",
    "Vermines", 
    "Kaamelott",
    "8 Mile",
    "Whiplash",
    "Les animaux fantastiques",
    "L'amour ouf",
    "Un p'tit truc en plus",
    "Le Hobbit",
    "Frères d'armes",
    "Le Loup de Wall Street",
    "Bref",
    "The Dark Knight Rises",
    "The Batman",
    "Harry Potter",
    "The Dark Knight : Le Chevalier noir",
    "Madame Doubtfire",
    "Enemy",
    "Le Problème à 3 corps",
    "Batman Begins",
    "J. Edgar",
    "Master and Commander : De l'autre côté du monde",
    "Hook ou la Revanche du capitaine Crochet",
    "Les Affranchis",
    "Anatomie d'une chute",
    "Jumanji",
    "Good Morning, Vietnam",
    "J'ai rencontré le Diable",
    "Spotlight",
    "The Irishman",
    "Ricky Gervais",
    "Arthur et les Minimoys",
    "Frère des ours",
    "Le Comte de Monte-Cristo",
    "Dallas Buyers Club",
    "Arthur 3 : La guerre des deux mondes",
    "Arthur et la vengeance de Maltazard",
    "Vol au-dessus d'un nid de coucou",
    "Dans les yeux d'Enzo",
    "Ricky Gervais",
    "Le Cercle des neiges",
    "BAC Nord",
    "Douze Hommes en colère",
    "Monsieur Aznavour",
    "Peaky Blinders",
    "Dragons",
    "Avatar : La Voie de l'eau",
    "La Haine",
    "Will Hunting",
    "Avatar",
    "Flow, le chat qui n'avait plus peur de l'eau",
    "Une vie",
    "Babylon",
    "La flamme",
    "Le flambeau",
    "Parasite",
    "Fatal",
    "The office"
]

# French-only content (doesn't need English audio)
FRENCH_ONLY_ALLOWLIST = [
    "Baptiste Lecaplain",
    "Corniche Kennedy",
    "Les Visiteurs",
    "Tuche",
    "Wasabi",
    "Napoléon",
    "Au service de la France",
    "Une intime conviction",
    "J'ai rencontré le Diable",
    "Les trois mousquetaires",
    "Flow",
    "Skate kitchen",
    "Les chambres rouges",
    "Rock'n Roll",
    "Arthur",
    "attachement",
    "Les chevaliers du ciel",
    "Capharnaüm",
    "Sous la seine",
    "Kaamelott",
    "Un p'tit truc en plus",
    "The match",
    "Astérix & Obélix",
    "Intouchables",
    "Vaincre ou mourir",
    "la 7ème compagnie",
    "Indigènes",
    "Jérémy Ferrari",
    "Flashback",
    "Jamais sans mon psy",
    "F*ckin' Fred : Comme un Léopard",
    "Liars Club",
    "Challenger",
    "Monsieur Aznavour",
    "La promesse verte",
    "Bref",
    "C'est le monde à l'envers",
    "L'amour ouf",
    "L'exoconférence",
    "Heureux gagnants",
    "BAC Nord",
    "Sons",
    "Squid game",
    "Comment c'est loin",
    "Maison de retraite",
    "Le Comte de Monte-Cristo",
    "Senna",
    "Les choristes",
    "Vermines",
    "La flamme",
    "Le sens de la fête",
    "Parasite",
    "Le cercle des neiges",
    "Cœurs Noirs",
    "Le flambeau",
    "Rapide",
    "Fatal",
    "Vive la France",
    "Connasse",
    "Crows Zero",
    "Barbaque",
    "Climax",
    "Chien de la casse",
    "Five",
    "Enter the void",
    "11 commandements",
    "La haine",
    "McWalter",
    "Memories of Murder",
    "Old boy",
    "P-51 Dragon Fighter",
    "Bienvenue chez les Ch'tis",
    "Sept ans au Tibet",
    "Le Diable probablement",
    "Brice de Nice",
    "Jeux d'enfants",
    "Un singe en hiver",
    "Les tontons flingueurs",
    "Pour le meilleur et à l'aveugle",
    "99 Francs",
    "Mesrine :",
    "Last One Laughing",
    "Qui rit, sort",
    "Les Lyonnais",
    "La French",
    "Le Silence de l'eau",
    "Sous les jupes des filles",
    "La tour montparnasse infernale",
    "Goliath",
    "Le royaume des chats",
    "Certains l'aiment chauve",
    "Loups Garous",
    "Les orphelins",
    "Rascals",
    "Zion",
    "Le fil",
    "Le choix",
    "Baron noir",
    "Validé"
]

# French subtitles only content (only requires French subtitles, no audio language requirements)
# Use this for foreign films, documentaries, or content where audio language detection is unreliable
FRENCH_SUBS_ONLY_ALLOWLIST = [
    "Fire Country",
    "Ricky Gervais",
    "I Think You Should Leave with Tim Robinson",
    "Raving Iran",
    "Apocalypto",
]

# Items globally exempt from language checking
LANGUAGE_CHECK_ALLOWLIST = [
    "Napoléon",
    "Les visiteurs",
    "Lovely bones",
    "Ip man",
    "Pantheon",
    "Anatomie d'une chute",
    "One piece", 
    "Le Comte de Monte-Cristo",
    "Love",
    "La chambre de Mariana",
    "Les Garçons et Guillaume",
    "Sirāt",
    "Les Patriotes",
    "Paradis Express",
    "Fruitvale Station",
    "Les ailes du désir",
    "Escape from the 21st Century",
]

# Specific episodes exempt from language checking
# Format: {"Show Name": {"Season": [episode1, episode2, ...], "Season2": [episode1, ...]}}
LANGUAGE_CHECK_EPISODE_ALLOWLIST = {
    "Doctor Who": {
        "9": [0],
        "20": [5],
    },
    "The Office": {
        "3": [4]
    },
    "1883": {
        "1": [6]
    },
}


# Time-based Configuration (in months)
OLD_CONTENT_MONTHS_CUTOFF = 4      # Content not watched in X months
MIN_AGE_MONTHS = 3                 # Don't flag recently added content (months)

# Size Configuration
LARGE_MOVIE_SIZE_THRESHOLD_GB = 13  # Movies larger than this size (GB) will be flagged

# Recent Items Langugage Configuration
RECENT_ITEMS_DAYS_BACK = 1500        # Check items added in the last X days


# ============================================================================


def get_french_day_name(date: datetime) -> str:
    """Convert a date to French day name with date format (e.g., 'Mercredi 18/12')"""
    french_days = {
        0: "Lundi",
        1: "Mardi",
        2: "Mercredi",
        3: "Jeudi",
        4: "Vendredi",
        5: "Samedi",
        6: "Dimanche"
    }
    
    # Handle both datetime and date objects
    if hasattr(date, 'date'):
        date_obj = date.date() if callable(date.date) else date
    else:
        date_obj = date
    
    day_name = french_days[date_obj.weekday()]
    return f"{day_name} {date_obj.day:02d}/{date_obj.month:02d}"


def parse_jellyfin_datetime(date_string: str) -> datetime:
    """Parse Jellyfin datetime string with Python 3.9 compatibility
    
    Jellyfin returns microseconds with 7 digits, but Python 3.9's fromisoformat()
    only supports up to 6 digits. This function truncates microseconds for compatibility.
    """
    if not date_string:
        raise ValueError("Empty date string")
    
    # Replace Z with timezone offset
    date_str = date_string.replace('Z', '+00:00')
    
    # Fix microseconds for Python 3.9 compatibility
    if '.' in date_str:
        if '+' in date_str:
            date_part, tz_part = date_str.split('+', 1)
        elif '-' in date_str and date_str.count('-') > 2:  # Handle negative timezone
            # Find the last - which should be timezone
            parts = date_str.rsplit('-', 1)
            date_part, tz_part = parts[0], '-' + parts[1]
        else:
            date_part = date_str
            tz_part = '00:00'
            
        if '.' in date_part:
            main_part, microsec_part = date_part.split('.', 1)
            # Truncate microseconds to 6 digits max for Python 3.9 compatibility  
            microsec_part = microsec_part[:6]
            # Pad with zeros if less than 6 digits
            microsec_part = microsec_part.ljust(6, '0')
            
            if '+' in date_str:
                date_str = f"{main_part}.{microsec_part}+{tz_part}"
            elif '-' in tz_part:
                date_str = f"{main_part}.{microsec_part}{tz_part}"
            else:
                date_str = f"{main_part}.{microsec_part}+{tz_part}"
    
    return datetime.fromisoformat(date_str)



def send_slack_message(message: str, webhook_url: str = None) -> bool:
    """Send a message to Slack webhook, splitting if too long"""
    if not webhook_url:
        webhook_url = os.getenv('PLEX_HEALTH_SLACK_WEBHOOK')
    
    if not webhook_url:
        print("⚠️  PLEX_HEALTH_SLACK_WEBHOOK environment variable not set. Skipping Slack notification.")
        return False
    
    # Slack has a 4000 character limit per message
    MAX_MESSAGE_LENGTH = 3800  # Leave some buffer
    
    try:
        if len(message) <= MAX_MESSAGE_LENGTH:
            # Message fits in one piece
            payload = {"text": message}
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            print("✅ Slack message sent successfully")
            return True
        else:
            # Message is too long, need to split it
            print(f"⚠️  Message too long ({len(message)} chars), splitting into chunks...")
            
            # Extract header and content
            if "```" in message:
                parts = message.split("```")
                if len(parts) >= 3:
                    header = parts[0].strip()
                    content = parts[1].strip()
                    
                    # Split content into chunks
                    lines = content.split('\n')
                    chunks = []
                    current_chunk = []
                    current_length = len(header) + 10  # Account for ``` markers and newlines
                    
                    for line in lines:
                        line_length = len(line) + 1  # +1 for newline
                        if current_length + line_length > MAX_MESSAGE_LENGTH:
                            # Start new chunk
                            if current_chunk:
                                chunk_content = '\n'.join(current_chunk)
                                chunks.append((header, chunk_content))
                                current_chunk = []
                                current_length = len(header) + 10
                        
                        current_chunk.append(line)
                        current_length += line_length
                    
                    # Add remaining lines
                    if current_chunk:
                        chunk_content = '\n'.join(current_chunk)
                        chunks.append((header, chunk_content))
                    
                    # Send all chunks
                    for i, (chunk_header, chunk_content) in enumerate(chunks, 1):
                        if len(chunks) > 1:
                            # Add part indicator for multi-part messages
                            final_message = f"{chunk_header} (Part {i}/{len(chunks)}):\n```\n{chunk_content}\n```"
                        else:
                            final_message = f"{chunk_header}:\n```\n{chunk_content}\n```"
                        
                        payload = {"text": final_message}
                        response = requests.post(webhook_url, json=payload)
                        response.raise_for_status()
                    
                    print(f"✅ Slack message sent successfully in {len(chunks)} parts")
                    return True
                else:
                    # Malformed message with ```, send as is
                    payload = {"text": message}
                    response = requests.post(webhook_url, json=payload)
                    response.raise_for_status()
                    print("✅ Slack message sent successfully")
                    return True
            else:
                # Simple text message, just truncate
                truncated = message[:MAX_MESSAGE_LENGTH-50] + "...\n(Message truncated)"
                payload = {"text": truncated}
                response = requests.post(webhook_url, json=payload)
                response.raise_for_status()
                print("✅ Slack message sent successfully (truncated)")
                return True
        
    except Exception as e:
        print(f"❌ Failed to send Slack message: {e}")
        return False


def setup_jellyfin_client() -> Tuple[JellyfinClient, str, str]:
    """Set up and authenticate Jellyfin client, return client, server_url, and api_key"""
    client = JellyfinClient()
    
    client.config.app('jellyfin_monitor', '1.0.0', 'media_monitor', 'unique_jellyfin_monitor_id')
    client.config.data["auth.ssl"] = True
    
    SERVER_URL = 'https://jimmydore.eclipse.usbx.me/jellyfin'
    API_KEY = os.getenv('JELLYFIN_API_KEY')
    
    if not API_KEY:
        raise ValueError("JELLYFIN_API_KEY environment variable is required")
    
    client.config.data["app.name"] = 'jellyfin api'
    client.config.data["app.version"] = '1.0.0'
    client.authenticate({"Servers": [{"AccessToken": API_KEY, "address": SERVER_URL}]}, discover=False)
    
    return client, SERVER_URL, API_KEY


def fetch_jellyseer_requests() -> List[Dict[str, Any]]:
    """Fetch all requests from Jellyseer API with pagination support"""
    JELLYSEER_API_KEY = os.getenv('JELLYSEER_API_KEY')
    JELLYSEER_BASE_URL = os.getenv('JELLYSEER_BASE_URL')
    
    if not JELLYSEER_API_KEY:
        raise ValueError("JELLYSEER_API_KEY environment variable is required")
    
    if not JELLYSEER_BASE_URL:
        raise ValueError("JELLYSEER_BASE_URL environment variable is required")
    
    try:
        headers = {
            'X-Api-Key': JELLYSEER_API_KEY,
            'Content-Type': 'application/json'
        }
        
        all_requests = []
        page = 1
        take = 50  # Number of items per page
        total_pages = None
        
        print(f"🔍 Fetching requests from Jellyseer: {JELLYSEER_BASE_URL}/api/v1/request")
        
        while True:
            # Use the correct pagination parameters from Swagger docs
            params = {
                'take': take,
                'skip': (page - 1) * take
            }
            
            url = f"{JELLYSEER_BASE_URL}/api/v1/request"
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            page_results = data.get('results', [])
            page_info = data.get('pageInfo', {})
            
            # Add results from this page
            all_requests.extend(page_results)
            
            # Get pagination info from the pageInfo structure
            if total_pages is None:
                total_results = page_info.get('results', 0)
                total_pages = page_info.get('pages', 1)
                print(f"📄 Found {total_results} total requests across {total_pages} pages")
            
            print(f"   📥 Page {page}/{total_pages}: {len(page_results)} requests")
            
            # Check if we have more pages - based on actual page vs total pages
            if page >= total_pages or len(page_results) == 0:
                break
                
            page += 1
            
            # Safety check to prevent infinite loops
            if page > 100:  # Reasonable upper limit
                print("⚠️  Reached maximum page limit (100), stopping pagination")
                break
        
        print(f"✅ Successfully fetched {len(all_requests)} total requests from Jellyseer")
        return all_requests
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch Jellyseer requests: {e}")
        return []
    except Exception as e:
        print(f"❌ Error processing Jellyseer requests: {e}")
        return []


def fetch_movie_details(tmdb_id: int, language: str = 'en') -> Dict[str, Any]:
    """Fetch detailed movie information from Jellyseerr API with caching"""
    cache_key = f"movie_{tmdb_id}_{language}"
    
    # Check cache first
    if cache_key in _tmdb_cache:
        print(f"📋 Using cached movie details for TMDB ID {tmdb_id}")
        return _tmdb_cache[cache_key]
    
    JELLYSEER_API_KEY = os.getenv('JELLYSEER_API_KEY')
    JELLYSEER_BASE_URL = os.getenv('JELLYSEER_BASE_URL')
    
    if not JELLYSEER_API_KEY or not JELLYSEER_BASE_URL:
        return {}
    
    try:
        headers = {
            'X-Api-Key': JELLYSEER_API_KEY,
            'Content-Type': 'application/json'
        }
        
        url = f"{JELLYSEER_BASE_URL}/api/v1/movie/{tmdb_id}"
        params = {'language': language}
        print(f"🎬 Fetching movie details for TMDB ID {tmdb_id} ({language})")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        # Cache the result
        _tmdb_cache[cache_key] = data
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch movie details for TMDB ID {tmdb_id}: {e}")
        return {}
    except Exception as e:
        print(f"❌ Error processing movie details for TMDB ID {tmdb_id}: {e}")
        return {}


def fetch_tv_details(tmdb_id: int, language: str = 'en') -> Dict[str, Any]:
    """Fetch detailed TV show information from Jellyseerr API with caching"""
    cache_key = f"tv_{tmdb_id}_{language}"
    
    # Check cache first
    if cache_key in _tmdb_cache:
        print(f"📋 Using cached TV details for TMDB ID {tmdb_id}")
        return _tmdb_cache[cache_key]
    
    JELLYSEER_API_KEY = os.getenv('JELLYSEER_API_KEY')
    JELLYSEER_BASE_URL = os.getenv('JELLYSEER_BASE_URL')
    
    if not JELLYSEER_API_KEY or not JELLYSEER_BASE_URL:
        return {}
    
    try:
        headers = {
            'X-Api-Key': JELLYSEER_API_KEY,
            'Content-Type': 'application/json'
        }
        
        url = f"{JELLYSEER_BASE_URL}/api/v1/tv/{tmdb_id}"
        params = {'language': language}
        print(f"📺 Fetching TV details for TMDB ID {tmdb_id} ({language})")
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        # Cache the result
        _tmdb_cache[cache_key] = data
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch TV details for TMDB ID {tmdb_id}: {e}")
        return {}
    except Exception as e:
        print(f"❌ Error processing TV details for TMDB ID {tmdb_id}: {e}")
        return {}


def clear_tmdb_cache():
    """Clear the TMDB cache to prevent memory issues"""
    global _tmdb_cache
    cache_size = len(_tmdb_cache)
    _tmdb_cache.clear()
    print(f"🧹 Cleared TMDB cache ({cache_size} items)")


def get_cache_stats():
    """Get statistics about the TMDB cache"""
    return {
        'size': len(_tmdb_cache),
        'movie_count': len([k for k in _tmdb_cache.keys() if k.startswith('movie_')]),
        'tv_count': len([k for k in _tmdb_cache.keys() if k.startswith('tv_')])
    }


def fetch_media_details(tmdb_id: int, media_type: str = 'tv') -> Dict[str, Any]:
    """Fetch detailed media information including seasons from Jellyseer API"""
    JELLYSEER_API_KEY = os.getenv('JELLYSEER_API_KEY')
    JELLYSEER_BASE_URL = os.getenv('JELLYSEER_BASE_URL')
    
    if not JELLYSEER_API_KEY or not JELLYSEER_BASE_URL:
        return {}
    
    try:
        headers = {
            'X-Api-Key': JELLYSEER_API_KEY,
            'Content-Type': 'application/json'
        }
        
        # Use the correct endpoint from Overseerr API docs: /api/v1/media
        # We need to find the media by TMDB ID - search with pagination
        page = 0
        take = 100
        max_pages = 10  # Safety limit
        
        print(f"🔍 Searching for media with TMDB ID {tmdb_id} in media list")
        
        while page < max_pages:
            url = f"{JELLYSEER_BASE_URL}/api/v1/media"
            params = {
                'filter': 'all',
                'take': take,
                'skip': page * take
            }
            
            print(f"   📄 Searching page {page + 1} (items {page * take + 1}-{(page + 1) * take})")
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            media_results = data.get('results', [])
            page_info = data.get('pageInfo', {})
            
            print(f"   📥 Found {len(media_results)} results on this page")
            
            # Find the media with matching TMDB ID
            for media_item in media_results:
                if media_item.get('tmdbId') == tmdb_id and media_item.get('mediaType') == media_type:
                    print(f"📊 Found media for TMDB ID {tmdb_id} on page {page + 1}")
                    print(f"📊 Media data keys: {list(media_item.keys())}")
                    if media_item.get('seasons'):
                        print(f"📊 Found {len(media_item.get('seasons', []))} seasons in media data")
                        for season in media_item.get('seasons', []):
                            season_num = season.get('seasonNumber', 'Unknown')
                            season_status = season.get('status', 'Unknown')
                            print(f"   Season {season_num}: status {season_status}")
                    
                    return media_item
            
            # Check if we have more pages
            if len(media_results) < take or page + 1 >= page_info.get('pages', 1):
                break
                
            page += 1
        
        print(f"⚠️  Media with TMDB ID {tmdb_id} not found in media list after searching {page + 1} pages")
        return {}
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch media details for TMDB ID {tmdb_id}: {e}")
        return {}
    except Exception as e:
        print(f"❌ Error processing media details for TMDB ID {tmdb_id}: {e}")
        return {}


def fetch_season_episodes(tmdb_id: int, season_number: int) -> List[Dict[str, Any]]:
    """Fetch episode details for a specific season from Jellyseer API"""
    JELLYSEER_API_KEY = os.getenv('JELLYSEER_API_KEY')
    JELLYSEER_BASE_URL = os.getenv('JELLYSEER_BASE_URL')
    
    if not JELLYSEER_API_KEY or not JELLYSEER_BASE_URL:
        return []
    
    try:
        headers = {
            'X-Api-Key': JELLYSEER_API_KEY,
            'Content-Type': 'application/json'
        }
        
        # Fetch season details from Jellyseer
        url = f"{JELLYSEER_BASE_URL}/api/v1/tv/{tmdb_id}/season/{season_number}"
        print(f"🔍 Fetching episodes for TMDB ID {tmdb_id}, Season {season_number}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        episodes = data.get('episodes', [])
        
        print(f"📺 Found {len(episodes)} episodes in season {season_number}")
        
        # Filter to only available episodes (status 5)
        available_episodes = []
        for ep in episodes:
            episode_num = ep.get('episodeNumber')
            # Check if episode is available in Jellyseer's media tracking
            # Episodes are available if they exist in the response
            available_episodes.append({
                'episode_number': episode_num,
                'name': ep.get('name', ''),
                'air_date': ep.get('airDate', ''),
            })
        
        return available_episodes
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch season {season_number} episodes for TMDB ID {tmdb_id}: {e}")
        return []
    except Exception as e:
        print(f"❌ Error processing season {season_number} episodes for TMDB ID {tmdb_id}: {e}")
        return []


def get_recent_episodes_for_season(tmdb_id: int, season_number: int, days_back: int = 7) -> List[int]:
    """Get episode numbers for episodes that aired in the last N days"""
    episodes = fetch_season_episodes(tmdb_id, season_number)
    
    if not episodes:
        return []
    
    today = datetime.now().date()
    cutoff_date = today - timedelta(days=days_back)
    
    recent_episode_numbers = []
    
    for ep in episodes:
        air_date_str = ep.get('air_date')
        episode_num = ep.get('episode_number')
        
        if not air_date_str or not episode_num:
            continue
        
        try:
            # Parse air date (format: YYYY-MM-DD)
            air_date = datetime.strptime(air_date_str, '%Y-%m-%d').date()
            
            # Check if episode aired in the last N days and is not in the future
            if cutoff_date <= air_date <= today:
                recent_episode_numbers.append(episode_num)
                print(f"   📅 Episode {episode_num} aired on {air_date} (within last {days_back} days)")
        except Exception as e:
            print(f"⚠️  Could not parse air date '{air_date_str}' for episode {episode_num}: {e}")
            continue
    
    return sorted(recent_episode_numbers)


def analyze_tv_series_seasons(tmdb_id: int, media: Dict[str, Any], title: str, requested_season_numbers: List[int] = None) -> Dict[str, Any]:
    """Analyze TV series season-by-season availability
    
    Args:
        tmdb_id: The TMDB ID of the TV series
        media: The media object from Jellyseer
        title: The title of the series
        requested_season_numbers: Optional list of specific season numbers that were requested.
                                  If None, all seasons will be analyzed.
    """
    try:
        # Fetch detailed TV show information to get season data
        tv_details = fetch_tv_details(tmdb_id)
        if not tv_details:
            print(f"❌ Could not fetch TV details for TMDB ID {tmdb_id}")
            return {
                'analysis_available': False,
                'missing_seasons': [],
                'available_seasons': [],
                'future_seasons': [],
                'in_progress_seasons': [],
                'total_seasons': 0,
                'is_complete_for_released': False,
                'summary': f"Could not fetch season details for {title}"
            }
        
        # Update title with the one from TV details if available (more reliable)
        if tv_details.get('name'):
            title = tv_details['name']
            print(f"📺 Updated title from TV details: {title}")
        
        # Fetch detailed media information with season-level availability
        detailed_media_info = fetch_media_details(tmdb_id, 'tv')
        detailed_seasons = detailed_media_info.get('seasons', []) if detailed_media_info else []
        if detailed_seasons:
            print(f"📊 Using detailed media info with {len(detailed_seasons)} seasons from /media endpoint")
        else:
            print(f"📊 No detailed season info available from /media endpoint")
        
        # Get seasons information
        seasons = tv_details.get('seasons', [])
        if not seasons:
            return {
                'analysis_available': False,
                'missing_seasons': [],
                'available_seasons': [],
                'future_seasons': [],
                'in_progress_seasons': [],
                'total_seasons': 0,
                'is_complete_for_released': False,
                'summary': f"No season information available for {title}"
            }
        
        # Get current date for filtering future seasons
        today = datetime.now().date()
        
        missing_seasons = []
        available_seasons = []
        future_seasons = []
        in_progress_seasons = []
        
        # Analyze each season
        print(f"📺 Found {len(seasons)} total seasons for {title}")
        for season in seasons:
            season_number = season.get('seasonNumber', 0)
            season_name = season.get('name', f'Season {season_number}')
            air_date = season.get('airDate')
            episode_count = season.get('episodeCount', 0)
            
            print(f"   📅 Season {season_number}: {season_name}, air_date: {air_date}, episodes: {episode_count}")
            
            # Skip Season 0 (specials) as they're often not tracked properly
            if season_number == 0:
                print(f"   ⏩ Skipping Season 0 (specials)")
                continue
            
            # Skip seasons that were not requested (if specific seasons were requested)
            if requested_season_numbers is not None and season_number not in requested_season_numbers:
                print(f"   ⏩ Skipping Season {season_number} (not in requested seasons: {requested_season_numbers})")
                continue
            
            # Check if this season has been released yet
            is_future_season = False
            if air_date:
                try:
                    if 'T' in air_date:  # ISO format with time
                        season_date = datetime.fromisoformat(air_date.replace('Z', '+00:00')).date()
                    else:  # Just date format
                        season_date = datetime.strptime(air_date, '%Y-%m-%d').date()
                    
                    print(f"   📅 Season {season_number} air date: {season_date}, today: {today}")
                    if season_date > today:
                        is_future_season = True
                        future_seasons.append({
                            'season_number': season_number,
                            'name': season_name,
                            'air_date': air_date,
                            'episode_count': episode_count
                        })
                        print(f"   🔮 Season {season_number} is future - adding to future_seasons and skipping")
                        continue
                        
                except Exception as e:
                    print(f"⚠️  Could not parse season air date '{air_date}' for {title} {season_name}: {e}")
            else:
                # No air date means season is not yet announced - treat as future/unknown
                print(f"   ⚠️  No air date available for Season {season_number}, treating as future/unknown")
                future_seasons.append({
                    'season_number': season_number,
                    'name': season_name,
                    'air_date': None,
                    'episode_count': episode_count
                })
                continue
            
            # Check if this season is "in progress" (some episodes aired, but not all)
            # by fetching episode-level data
            episodes = fetch_season_episodes(tmdb_id, season_number)
            if episodes:
                # Use actual episode count from API if available, or fallback to season metadata
                actual_episode_count = len(episodes) if len(episodes) > 0 else episode_count
                
                episodes_aired = 0
                episodes_future = 0
                for ep in episodes:
                    ep_air_date_str = ep.get('air_date')
                    if ep_air_date_str:
                        try:
                            ep_air_date = datetime.strptime(ep_air_date_str, '%Y-%m-%d').date()
                            if ep_air_date <= today:
                                episodes_aired += 1
                            else:
                                episodes_future += 1
                        except Exception:
                            pass
                
                print(f"   📊 Season {season_number}: {episodes_aired}/{actual_episode_count} episodes have aired ({episodes_future} future)")
                
                # If some episodes aired but not all (some are still future), this is an in-progress season
                if episodes_aired > 0 and episodes_future > 0:
                    in_progress_seasons.append({
                        'season_number': season_number,
                        'name': season_name,
                        'air_date': air_date,
                        'episode_count': actual_episode_count,
                        'episodes_aired': episodes_aired
                    })
                    print(f"   🔄 Season {season_number} is in-progress ({episodes_aired}/{actual_episode_count} episodes) - adding to in_progress_seasons")
                    continue
                elif episodes_aired == 0:
                    # No episodes have aired yet - treat as future
                    future_seasons.append({
                        'season_number': season_number,
                        'name': season_name,
                        'air_date': air_date,
                        'episode_count': actual_episode_count
                    })
                    print(f"   🔮 Season {season_number} has no aired episodes yet - adding to future_seasons")
                    continue
                # If all episodes have aired (episodes_future == 0), continue to availability check
            
            # Check if this season is available in Jellyfin
            # First check basic media seasons data, then fetch detailed season info if needed
            season_available = False
            season_found = False
            
            # First, try basic media seasons data
            media_seasons = media.get('seasons', [])
            print(f"   🔍 Checking availability for Season {season_number} in basic media. Media has {len(media_seasons)} seasons data")
            
            for media_season in media_seasons:
                if media_season.get('seasonNumber') == season_number:
                    # Found this season in media data, check its status
                    season_status = media_season.get('status', 0)
                    season_found = True
                    print(f"   📊 Season {season_number} found in basic media with status: {season_status}")
                    if season_status == 5:  # Available
                        season_available = True
                        print(f"   ✅ Season {season_number} is available")
                    else:
                        print(f"   ❌ Season {season_number} is not available (status: {season_status})")
                    break
            
            # If not found in basic media data, try detailed media seasons data
            if not season_found and detailed_seasons:
                print(f"   ⚠️  Season {season_number} not found in basic media seasons data")
                print(f"   🔍 Checking detailed media seasons data from /media endpoint...")
                
                for detailed_season in detailed_seasons:
                    if detailed_season.get('seasonNumber') == season_number:
                        season_status = detailed_season.get('status', 0)
                        season_found = True
                        print(f"   📊 Season {season_number} found in detailed media with status: {season_status}")
                        if season_status == 5:  # Available
                            season_available = True
                            print(f"   ✅ Season {season_number} is available (from /media endpoint)")
                        else:
                            print(f"   ❌ Season {season_number} is not available (status: {season_status}) (from /media endpoint)")
                        break
                
                if not season_found:
                    print(f"   ⚠️  Season {season_number} not found in detailed media seasons data either")
            
            # If no season-specific data found anywhere, check overall media status as fallback
            if not season_found:
                overall_status = media.get('status', 0)
                print(f"   📊 No season-specific data found anywhere, checking overall media status: {overall_status}")
                
                if overall_status == 5:  # Completely available
                    season_available = True
                    print(f"   ✅ Using overall status - Season {season_number} considered available")
                elif overall_status == 4:  # Partially available - can't determine specific seasons
                    print(f"   🤔 Media is partially available (status 4) but no season-level data available")
                    print(f"   ⚠️  Cannot determine Season {season_number} availability - assuming missing")
                    season_available = False
                else:
                    season_available = False
                    print(f"   ❌ Overall status {overall_status} indicates not available")
            
            if season_available:
                available_seasons.append({
                    'season_number': season_number,
                    'name': season_name,
                    'air_date': air_date,
                    'episode_count': episode_count
                })
                print(f"   ✅ Added Season {season_number} to available_seasons")
            else:
                missing_seasons.append({
                    'season_number': season_number,
                    'name': season_name,
                    'air_date': air_date,
                    'episode_count': episode_count
                })
                print(f"   ❌ Added Season {season_number} to missing_seasons")
        
        # Determine if the series is complete for released seasons
        total_released_seasons = len(missing_seasons) + len(available_seasons)
        is_complete_for_released = len(missing_seasons) == 0 and total_released_seasons > 0
        
        # Create summary
        if is_complete_for_released:
            if future_seasons or in_progress_seasons:
                in_progress_info = f", {len(in_progress_seasons)} in-progress" if in_progress_seasons else ""
                future_info = f", {len(future_seasons)} future" if future_seasons else ""
                summary = f"{title} - Complete for all {len(available_seasons)} released season(s){in_progress_info}{future_info}"
            else:
                summary = f"{title} - Complete for all {len(available_seasons)} season(s)"
        else:
            summary = f"{title} - Missing {len(missing_seasons)} of {total_released_seasons} released season(s)"
            if in_progress_seasons:
                summary += f", {len(in_progress_seasons)} in-progress season(s)"
            if future_seasons:
                summary += f", {len(future_seasons)} future season(s) pending"
        
        return {
            'analysis_available': True,
            'title': title,  # Return the updated title
            'missing_seasons': missing_seasons,
            'available_seasons': available_seasons,
            'future_seasons': future_seasons,
            'in_progress_seasons': in_progress_seasons,
            'total_seasons': len(seasons) - 1,  # Exclude season 0
            'total_released_seasons': total_released_seasons,
            'is_complete_for_released': is_complete_for_released,
            'summary': summary
        }
        
    except Exception as e:
        print(f"❌ Error analyzing seasons for {title}: {e}")
        return {
            'analysis_available': False,
            'missing_seasons': [],
            'available_seasons': [],
            'future_seasons': [],
            'in_progress_seasons': [],
            'total_seasons': 0,
            'is_complete_for_released': False,
            'summary': f"Error analyzing seasons for {title}: {e}"
        }


def analyze_jellyseer_requests(requests_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze Jellyseer requests and categorize them"""
    if not requests_list:
        return {
            'total': 0,
            'by_status': {},
            'unavailable_requests': [],
            'in_progress_requests': [],
            'summary': "No requests found"
        }
    
    status_counts = {}
    unavailable_requests = []
    in_progress_requests = []
    complete_for_released_requests = []
    future_releases_filtered = 0
    recent_releases_filtered = 0
    series_complete_for_released = 0
    series_in_progress = 0
    
    for request in requests_list:
        # Count by status
        status = request.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
        
        # Only process unavailable requests (status 0, 1, 2, 4)
        if status in [0, 1, 2, 4]:  # Unknown, Pending, Approved, or Partially Available
            media = request.get('media', {})
            media_type = media.get('mediaType', 'unknown')
            tmdb_id = media.get('tmdbId')
            
            # Get better title information
            title = 'Unknown'
            release_date = 'Unknown'
            
            if media:
                # Try to get title from different possible fields
                title = (media.get('title') or 
                        media.get('name') or 
                        media.get('originalTitle') or 
                        media.get('originalName') or 
                        str(media.get('tmdbId', 'Unknown')))
            
            # For TV series, perform season-by-season analysis
            if media_type == 'tv' and tmdb_id:
                print(f"📺 Analyzing seasons for TV series: {title} (TMDB ID: {tmdb_id})")
                print(f"📊 Media object keys: {list(media.keys())}")
                print(f"📊 Media status: {media.get('status', 'No status')}")
                if media.get('seasons'):
                    print(f"📊 Media has {len(media.get('seasons', []))} seasons in media object")
                
                # Get the requested seasons from the request object
                requested_seasons = request.get('seasons', [])
                if requested_seasons:
                    # Try different possible key names for season number
                    requested_season_numbers = []
                    for s in requested_seasons:
                        season_num = s.get('seasonNumber') or s.get('season_number') or s.get('id') or s.get('season')
                        if season_num is not None and season_num > 0:  # Exclude season 0
                            requested_season_numbers.append(season_num)
                    print(f"📊 Request has {len(requested_seasons)} season entries, requested seasons: {requested_season_numbers}")
                    print(f"📊 Raw request seasons data: {requested_seasons}")
                    
                    # If we couldn't extract any season numbers, treat as all seasons requested
                    if not requested_season_numbers:
                        print(f"⚠️  Could not extract season numbers from request - treating as all seasons requested")
                        requested_season_numbers = None
                else:
                    requested_season_numbers = None  # None means all seasons were requested
                    print(f"📊 No specific seasons in request - all seasons requested")
                
                season_analysis = analyze_tv_series_seasons(tmdb_id, media, title, requested_season_numbers)
                
                if season_analysis['analysis_available']:
                    # Use the updated title from season analysis (more reliable)
                    updated_title = season_analysis.get('title', title)
                    
                    # Check for in-progress seasons
                    in_progress_seasons = season_analysis.get('in_progress_seasons', [])
                    missing_seasons = season_analysis.get('missing_seasons', [])
                    future_seasons = season_analysis.get('future_seasons', [])
                    total_released_seasons = season_analysis.get('total_released_seasons', 0)
                    
                    # If no seasons have been released yet (all future) and no in-progress seasons, skip this series
                    if total_released_seasons == 0 and len(missing_seasons) == 0 and len(in_progress_seasons) == 0:
                        print(f"🔮 {updated_title} has no released seasons yet (all {len(future_seasons)} future) - skipping")
                        continue
                    
                    # If the series is complete for all released seasons, don't include it in unavailable
                    if season_analysis['is_complete_for_released']:
                        series_complete_for_released += 1
                        complete_request_info = {
                            'id': request.get('id'),
                            'status': status,
                            'title': updated_title,
                            'type': media_type,
                            'requestedBy': request.get('requestedBy', {}).get('displayName', 'Unknown'),
                            'createdAt': request.get('createdAt'),
                            'media': media,
                            'season_analysis': season_analysis
                        }
                        complete_for_released_requests.append(complete_request_info)
                        print(f"✅ {season_analysis['summary']}")
                        
                        # If complete but has in-progress seasons, also add to in_progress_requests
                        if in_progress_seasons:
                            series_in_progress += 1
                            in_progress_info = {
                                'id': request.get('id'),
                                'status': status,
                                'title': updated_title,
                                'type': media_type,
                                'requestedBy': request.get('requestedBy', {}).get('displayName', 'Unknown'),
                                'createdAt': request.get('createdAt'),
                                'media': media,
                                'season_analysis': season_analysis,
                                'in_progress_seasons': in_progress_seasons
                            }
                            in_progress_requests.append(in_progress_info)
                            print(f"🔄 {updated_title} has {len(in_progress_seasons)} in-progress season(s)")
                        continue  # Don't add to unavailable list
                    
                    # Check if there are no truly missing seasons (only in-progress)
                    elif len(missing_seasons) == 0 and len(in_progress_seasons) > 0:
                        # All "missing" are actually in-progress - add to in_progress_requests
                        series_in_progress += 1
                        in_progress_info = {
                            'id': request.get('id'),
                            'status': status,
                            'title': updated_title,
                            'type': media_type,
                            'requestedBy': request.get('requestedBy', {}).get('displayName', 'Unknown'),
                            'createdAt': request.get('createdAt'),
                            'media': media,
                            'season_analysis': season_analysis,
                            'in_progress_seasons': in_progress_seasons
                        }
                        in_progress_requests.append(in_progress_info)
                        print(f"🔄 {updated_title} only has in-progress seasons - adding to currently airing")
                        continue
                    
                    else:
                        # Series has truly missing released seasons
                        print(f"⚠️  {season_analysis['summary']}")
                        request_info = {
                            'id': request.get('id'),
                            'status': status,
                            'title': updated_title,
                            'type': media_type,
                            'release_date': 'Multiple seasons',  # TV series don't have single release date
                            'requestedBy': request.get('requestedBy', {}).get('displayName', 'Unknown'),
                            'createdAt': request.get('createdAt'),
                            'media': media,
                            'season_analysis': season_analysis
                        }
                        unavailable_requests.append(request_info)
                        
                        # Also track in-progress seasons if the series has them
                        if in_progress_seasons:
                            series_in_progress += 1
                            in_progress_info = {
                                'id': request.get('id'),
                                'status': status,
                                'title': updated_title,
                                'type': media_type,
                                'requestedBy': request.get('requestedBy', {}).get('displayName', 'Unknown'),
                                'createdAt': request.get('createdAt'),
                                'media': media,
                                'season_analysis': season_analysis,
                                'in_progress_seasons': in_progress_seasons
                            }
                            in_progress_requests.append(in_progress_info)
                            print(f"🔄 {updated_title} also has {len(in_progress_seasons)} in-progress season(s)")
                        continue
                else:
                    # Fallback to original logic if season analysis fails
                    print(f"⚠️  Season analysis failed for {title}, using original logic")
            
            # For movies or TV series where season analysis failed, use original logic
            # Fetch additional details if we have a TMDB ID
            if tmdb_id:
                if media_type == 'movie':
                    details = fetch_movie_details(tmdb_id)
                    if details:
                        title = details.get('title', title)
                        release_date = details.get('releaseDate', 'Unknown')
                elif media_type == 'tv':
                    details = fetch_tv_details(tmdb_id)
                    if details:
                        title = details.get('name', title)
                        release_date = details.get('firstAirDate', 'Unknown')
            
            # Filter out content with future release dates or recent releases (if enabled)
            should_include = True
            if release_date and release_date != 'Unknown':
                try:
                    # Parse the release date
                    if 'T' in release_date:  # ISO format with time
                        release_datetime = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
                        release_date_only = release_datetime.date()
                    else:  # Just date format
                        release_date_only = datetime.strptime(release_date, '%Y-%m-%d').date()
                    
                    # Compare with today's date
                    today = datetime.now().date()
                    
                    # Filter future releases
                    if FILTER_FUTURE_RELEASES and release_date_only > today:
                        should_include = False
                        future_releases_filtered += 1
                        print(f"🗓️  Filtering out future release: {title} (releases {release_date_only})")
                    
                    # Filter recent releases (released less than X months ago)
                    elif FILTER_RECENT_RELEASES:
                        cutoff_date = today - timedelta(days=RECENT_RELEASE_MONTHS_CUTOFF * 30)  # Approximate months to days
                        if release_date_only > cutoff_date:
                            should_include = False
                            recent_releases_filtered += 1
                            print(f"🆕 Filtering out recent release: {title} (released {release_date_only}, less than {RECENT_RELEASE_MONTHS_CUTOFF} months ago)")
                            
                except Exception as e:
                    # If we can't parse the date, include the item (safer approach)
                    print(f"⚠️  Could not parse release date '{release_date}' for {title}: {e}")
            
            # Only add to unavailable requests if it's not a future release
            if should_include:
                request_info = {
                    'id': request.get('id'),
                    'status': status,
                    'title': title,
                    'type': media_type,
                    'release_date': release_date,
                    'requestedBy': request.get('requestedBy', {}).get('displayName', 'Unknown'),
                    'createdAt': request.get('createdAt'),
                    'media': media
                }
                unavailable_requests.append(request_info)
    
    # Create summary focused on unavailable requests
    total_requests = len(requests_list)
    unavailable_count = len(unavailable_requests)
    complete_for_released_count = len(complete_for_released_requests)
    in_progress_count = len(in_progress_requests)
    
    summary = f"Total requests: {total_requests} | Unavailable: {unavailable_count}"
    if in_progress_count > 0:
        summary += f" | Currently airing: {in_progress_count}"
        print(f"🔄 Found {in_progress_count} series with currently airing seasons")
    if series_complete_for_released > 0:
        summary += f" | Series complete for released seasons: {series_complete_for_released}"
        print(f"✅ Found {series_complete_for_released} TV series complete for all released seasons (only missing future seasons)")
    if future_releases_filtered > 0:
        summary += f" | Future releases filtered: {future_releases_filtered}"
        print(f"🗓️  Filtered out {future_releases_filtered} future releases from unavailable requests")
    if recent_releases_filtered > 0:
        summary += f" | Recent releases filtered: {recent_releases_filtered}"
        print(f"🆕 Filtered out {recent_releases_filtered} recent releases (less than {RECENT_RELEASE_MONTHS_CUTOFF} months old) from unavailable requests")
    
    return {
        'total': total_requests,
        'by_status': status_counts,
        'unavailable_requests': unavailable_requests,
        'in_progress_requests': in_progress_requests,
        'complete_for_released_requests': complete_for_released_requests,
        'series_complete_for_released': series_complete_for_released,
        'series_in_progress': series_in_progress,
        'future_releases_filtered': future_releases_filtered,
        'recent_releases_filtered': recent_releases_filtered,
        'summary': summary
    }


def get_all_users(server_url: str, api_key: str) -> List[Dict[str, Any]]:
    """Get all users from the Jellyfin server"""
    headers = {
        'X-Emby-Token': api_key,
        'Content-Type': 'application/json'
    }
    
    response = requests.get(f"{server_url}/Users", headers=headers)
    response.raise_for_status()
    
    users = response.json()
    if not users:
        raise ValueError("No users found on Jellyfin server")
    
    return users


def get_series_episodes_data(server_url: str, api_key: str, user_id: str, series_id: str) -> Dict[str, Any]:
    """Get episode-level play data for a TV series"""
    try:
        headers = {
            'X-Emby-Token': api_key,
            'Content-Type': 'application/json'
        }
        
        # Get all episodes for this series
        params = {
            'UserId': user_id,
            'ParentId': series_id,
            'IncludeItemTypes': 'Episode',
            'Recursive': 'true',
            'Fields': 'UserData,DateCreated',
            'Limit': 10000
        }
        
        url = f"{server_url}/Users/{user_id}/Items"
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        episodes = data.get('Items', [])
        
        # Aggregate episode play data
        total_episodes = len(episodes)
        played_episodes = 0
        total_play_count = 0
        latest_played_date = None
        
        for episode in episodes:
            episode_user_data = episode.get('UserData', {})
            episode_played = episode_user_data.get('Played', False)
            episode_last_played = episode_user_data.get('LastPlayedDate')
            
            if episode_played:
                played_episodes += 1
                play_count = episode_user_data.get('PlayCount', 0)
                total_play_count += play_count
                
                if episode_last_played:
                    if not latest_played_date or episode_last_played > latest_played_date:
                        latest_played_date = episode_last_played
        
        return {
            'total_episodes': total_episodes,
            'played_episodes': played_episodes,
            'total_play_count': total_play_count,
            'latest_played_date': latest_played_date,
            'has_played_episodes': played_episodes > 0
        }
        
    except Exception as e:
        print(f"      ⚠️  Failed to get episodes for series {series_id}: {e}")
        return {
            'total_episodes': 0,
            'played_episodes': 0,
            'total_play_count': 0,
            'latest_played_date': None,
            'has_played_episodes': False
        }


def get_movies_and_shows_for_user(server_url: str, api_key: str, user: Dict[str, Any]) -> List[Dict[Any, Any]]:
    """Get all movies and TV shows for a specific user"""
    try:
        headers = {
            'X-Emby-Token': api_key,
            'Content-Type': 'application/json'
        }
        
        user_id = user['Id']
        user_name = user.get('Name', 'Unknown')
        
        print(f"    👤 Getting items for user: {user_name}")
        
        # Use the Items endpoint with proper parameters
        params = {
            'UserId': user_id,
            'IncludeItemTypes': 'Movie,Series',
            'Recursive': 'true',
            'Fields': 'DateCreated,DateLastSaved,UserData,Path,Overview,Genres,Studios,People,ProductionYear,DateLastMediaAdded,MediaSources',
            'SortBy': 'SortName',
            'SortOrder': 'Ascending',
            'StartIndex': 0,
            'Limit': 10000  # Large limit to get all items
        }
        
        # Make direct API call to get items
        url = f"{server_url}/Users/{user_id}/Items"
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        items = data.get('Items', [])
        
        # Process each item and get episode data for series
        for item in items:
            if 'UserData' not in item:
                item['UserData'] = {}
            item['UserData']['UserName'] = user_name
            item['UserData']['UserId'] = user_id
            
            # For TV Series, get episode-level play data
            if item.get('Type') == 'Series':
                series_id = item.get('Id')
                if series_id:
                    episode_data = get_series_episodes_data(server_url, api_key, user_id, series_id)
                    
                    # Update the series UserData with episode-based information
                    if episode_data['has_played_episodes']:
                        item['UserData']['PlayCount'] = episode_data['total_play_count']
                        item['UserData']['Played'] = True
                        item['UserData']['LastPlayedDate'] = episode_data['latest_played_date']
                        item['UserData']['EpisodePlayData'] = {
                            'TotalEpisodes': episode_data['total_episodes'],
                            'PlayedEpisodes': episode_data['played_episodes'],
                            'TotalPlayCount': episode_data['total_play_count']
                        }
                    else:
                        # If no episodes were played, mark series as not played
                        item['UserData']['PlayCount'] = 0
                        item['UserData']['Played'] = False
                        item['UserData']['LastPlayedDate'] = None
        
        return items
        
    except Exception as e:
        print(f"    ❌ Error getting items for user {user.get('Name', 'Unknown')}: {e}")
        return []


def aggregate_all_user_data(server_url: str, api_key: str, users: List[Dict[str, Any]]) -> List[Dict[Any, Any]]:
    """Get play data from all users and aggregate it"""
    # Dictionary to store items by their ID, with play data from all users
    items_dict = {}
    
    for user in users:
        user_items = get_movies_and_shows_for_user(server_url, api_key, user)
        
        for item in user_items:
            item_id = item.get('Id')
            if not item_id:
                continue
                
            # If this is the first time we see this item, store it
            if item_id not in items_dict:
                items_dict[item_id] = {
                    'item': item.copy(),
                    'user_data': []  # List of UserData from different users
                }
                # Remove the UserData from the main item since we'll store it separately
                if 'UserData' in items_dict[item_id]['item']:
                    del items_dict[item_id]['item']['UserData']
            
            # Add this user's play data
            user_data = item.get('UserData', {})
            if user_data.get('PlayCount', 0) > 0 or user_data.get('Played', False):
                items_dict[item_id]['user_data'].append(user_data)
    
    # Convert back to list and add aggregated user data
    result_items = []
    for item_id, data in items_dict.items():
        item = data['item'].copy()
        user_data_list = data['user_data']
        
        # Create aggregated UserData
        aggregated_user_data = {
            'PlayCount': 0,
            'Played': False,
            'LastPlayedDate': None,
            'PlayedByUsers': [],
            'TotalPlayCount': 0
        }
        
        # Aggregate play data from all users
        latest_played_date = None
        for user_data in user_data_list:
            play_count = user_data.get('PlayCount', 0)
            played = user_data.get('Played', False)
            last_played = user_data.get('LastPlayedDate')
            user_name = user_data.get('UserName', 'Unknown')
            episode_play_data = user_data.get('EpisodePlayData')
            
            if play_count > 0 or played:
                user_play_info = {
                    'UserName': user_name,
                    'PlayCount': play_count,
                    'LastPlayedDate': last_played,
                    'Played': played
                }
                
                # Include episode data for TV series
                if episode_play_data:
                    user_play_info['EpisodePlayData'] = episode_play_data
                
                aggregated_user_data['PlayedByUsers'].append(user_play_info)
                aggregated_user_data['TotalPlayCount'] += play_count
                
                # Track the most recent play date across all users
                if last_played:
                    if not latest_played_date or last_played > latest_played_date:
                        latest_played_date = last_played
        
        # Set aggregated values
        if aggregated_user_data['PlayedByUsers']:
            aggregated_user_data['Played'] = True
            aggregated_user_data['PlayCount'] = aggregated_user_data['TotalPlayCount']
            aggregated_user_data['LastPlayedDate'] = latest_played_date
        
        item['UserData'] = aggregated_user_data
        result_items.append(item)
    
    return result_items

def get_series_total_size(server_url: str, api_key: str, series_id: str) -> int:
    """Get total size of all episodes in a TV series"""
    try:
        headers = {
            'X-Emby-Token': api_key,
            'Content-Type': 'application/json'
        }
        
        # Get all episodes for this series
        params = {
            'ParentId': series_id,
            'IncludeItemTypes': 'Episode',
            'Recursive': 'true',
            'Fields': 'MediaSources',
            'Limit': 10000
        }
        
        url = f"{server_url}/Items"
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        episodes = data.get('Items', [])
        
        total_size = 0
        for episode in episodes:
            media_sources = episode.get('MediaSources', [])
            if media_sources:
                episode_size = media_sources[0].get('Size', 0)
                total_size += episode_size
        
        return total_size
        
    except Exception as e:
        print(f"      ⚠️  Failed to get size for series {series_id}: {e}")
        return 0


def get_item_size(item: Dict[Any, Any]) -> int:
    """Get size of an item (movie or series)"""
    if item.get('Type') == 'Movie':
        # For movies, get size from MediaSources
        media_sources = item.get('MediaSources', [])
        if media_sources:
            return media_sources[0].get('Size', 0)
    elif item.get('Type') == 'Series':
        # For series, return cached size if available
        return item.get('_calculated_size', 0)
    
    return 0


def format_size(size_bytes: int) -> str:
    """Format size in bytes to human readable format"""
    if size_bytes == 0:
        return "Unknown size"
    
    # Convert to appropriate unit
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            if unit == 'B':
                return f"{int(size_bytes)} {unit}"
            else:
                return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} PB"


def is_allowlisted(item: Dict[Any, Any]) -> bool:
    """Check if an item is in the allowlist and should be protected from deletion"""
    item_name = item.get('Name', '').lower()
    
    # Check if item name contains any allowlisted term (case-insensitive partial matching)
    for allowed_term in CONTENT_ALLOWLIST:
        if allowed_term.lower() in item_name:
            return True
    
    return False


def is_french_only_allowlisted(item: Dict[Any, Any]) -> bool:
    """Check if an item is in the French-only allowlist (doesn't need English audio)"""
    item_name = item.get('Name', '').lower()
    
    # Check if item name contains any French-only allowlisted term (case-insensitive partial matching)
    for allowed_term in FRENCH_ONLY_ALLOWLIST:
        if allowed_term.lower() in item_name:
            return True
    
    return False


def is_french_subs_only_allowlisted(item: Dict[Any, Any]) -> bool:
    """Check if an item is in the French subs only allowlist (doesn't need French audio, but must have French subtitles)"""
    item_name = item.get('Name', '').lower()
    
    # Check if item name contains any French subs only allowlisted term (case-insensitive partial matching)
    for allowed_term in FRENCH_SUBS_ONLY_ALLOWLIST:
        if allowed_term.lower() in item_name:
            return True
    
    return False


def is_language_check_allowlisted(item: Dict[Any, Any]) -> bool:
    """Check if an item is globally exempt from language flagging"""
    item_name = item.get('Name', '').lower()
    
    # Check if item name contains any language-allowlisted term (case-insensitive partial matching)
    for allowed_term in LANGUAGE_CHECK_ALLOWLIST:
        if allowed_term.lower() in item_name:
            return True
    
    return False


def is_episode_language_check_allowlisted(series_name: str, season_number: int, episode_number: int) -> bool:
    """Check if a specific episode is exempt from language checking"""
    # Check if the series is in the episode allowlist
    for show_name, seasons in LANGUAGE_CHECK_EPISODE_ALLOWLIST.items():
        if show_name.lower() in series_name.lower():
            # Check if the season exists in the allowlist
            season_str = str(season_number)
            if season_str in seasons:
                # Check if the episode is in the allowlist for this season
                if episode_number in seasons[season_str]:
                    return True
    
    return False


def list_large_movies(items: List[Dict[Any, Any]], size_threshold_gb: int = 15) -> List[str]:
    """List movies that are larger than the specified size threshold (default 15GB)"""
    slack_formatted_items_list = []
    
    if not items:
        print("❌ No movies or TV shows found")
        return ["❌ No movies or TV shows found"]
    
    # Convert threshold to bytes
    size_threshold_bytes = size_threshold_gb * 1024 * 1024 * 1024
    
    print(f"🔍 Finding movies larger than {size_threshold_gb}GB...")
    
    # Filter for movies only and check size
    large_movies = []
    for item in items:
        if item.get('Type') == 'Movie':
            item_size = get_item_size(item)
            if item_size >= size_threshold_bytes:
                large_movies.append(item)
    
    if not large_movies:
        print(f"✅ No movies found larger than {size_threshold_gb}GB")
        return [f"✅ No movies found larger than {size_threshold_gb}GB - no movies need redownloading"]
    
    # Sort by size (largest first)
    large_movies.sort(key=lambda x: get_item_size(x), reverse=True)
    
    print(f"\n📋 Movies larger than {size_threshold_gb}GB (sorted by size, largest first):")
    print("=" * 120)
    
    total_size = 0
    for i, movie in enumerate(large_movies, 1):
        formatted_info = format_simple_item_info(movie)
        movie_size = get_item_size(movie)
        total_size += movie_size
        
        # Use consistent formatting - print to terminal
        print(f"{i:3d}. {formatted_info}")
        # Add to Slack list
        slack_formatted_items_list.append(f"{i:3d}. {formatted_info}")
    
    print("=" * 120)
    total_size_gb = total_size / (1024 * 1024 * 1024)
    print(f"💾 Total size of {len(large_movies)} large movies: {format_size(total_size)} ({total_size_gb:.1f} GB)")
    
    # Show average size
    avg_size_gb = total_size_gb / len(large_movies) if large_movies else 0
    print(f"📊 Average size: {avg_size_gb:.1f} GB per movie")
    
    # Show breakdown by watch status
    never_watched = [m for m in large_movies if not m.get('UserData', {}).get('Played', False)]
    watched = [m for m in large_movies if m.get('UserData', {}).get('Played', False)]
    
    never_watched_size = sum(get_item_size(m) for m in never_watched) / (1024 * 1024 * 1024)
    watched_size = sum(get_item_size(m) for m in watched) / (1024 * 1024 * 1024)
    
    print(f"\n📊 Breakdown by watch status:")
    print(f"  📥 Never watched: {len(never_watched)} movies ({never_watched_size:.1f} GB)")
    print(f"  ✅ Watched: {len(watched)} movies ({watched_size:.1f} GB)")
    
    print(f"\n💡 Tip: Consider manually redownloading these large movies in lower quality to save space")
    
    return slack_formatted_items_list


def filter_old_or_unwatched_items(items: List[Dict[Any, Any]], months_cutoff: int = None, min_age_months: int = None) -> Tuple[List[Dict[Any, Any]], List[Dict[Any, Any]]]:
    """Filter items that haven't been watched in X months or never played (but added more than min_age_months ago)"""
    # Use configuration values if not provided
    if months_cutoff is None:
        months_cutoff = OLD_CONTENT_MONTHS_CUTOFF
    if min_age_months is None:
        min_age_months = MIN_AGE_MONTHS
        
    cutoff_date = datetime.now() - timedelta(days=months_cutoff * 30)  # Approximate months to days
    min_age_date = datetime.now() - timedelta(days=min_age_months * 30)  # Don't flag recently added content
    old_or_unwatched = []
    protected_items = []
    
    for item in items:
        # Check allowlist first - if protected, skip this item
        if is_allowlisted(item):
            protected_items.append(item)
            continue
            
        user_data = item.get('UserData', {})
        is_played = user_data.get('Played', False)
        last_played_date = user_data.get('LastPlayedDate')
        date_created = item.get('DateCreated')
        
        # Check if item was added recently (skip if too new)
        item_age_ok = True
        if date_created:
            try:
                created_datetime = parse_jellyfin_datetime(date_created)
                if created_datetime.replace(tzinfo=None) > min_age_date:
                    item_age_ok = False  # Too new, skip this item
            except:
                pass  # If date parsing fails, assume it's old enough
        
        # Never played - but only include if item is old enough
        if not is_played:
            if item_age_ok:
                old_or_unwatched.append(item)
            continue
        
        # Played but no date (treat as old)
        if not last_played_date:
            old_or_unwatched.append(item)
            continue
        
        # Check if last played date is older than cutoff
        try:
            last_played_datetime = parse_jellyfin_datetime(last_played_date)
            if last_played_datetime.replace(tzinfo=None) < cutoff_date:
                old_or_unwatched.append(item)
        except:
            # If date parsing fails, treat as old
            old_or_unwatched.append(item)
    
    return old_or_unwatched, protected_items

def format_path(path: str) -> str:
    """Format path to show only the 4th and 5th parts"""
    if path:
        parts = path.strip("/").split("/")
        if len(parts) >= 5:
            return f"{parts[3]}/{parts[4]}"
    return path

def format_simple_item_info(item: Dict[Any, Any]) -> str:
    """Format item information for simple display"""
    name = item.get('Name', 'Unknown')
    item_type = item.get('Type', 'Unknown')
    year = item.get('ProductionYear', '')
    year_str = f" ({year})" if year else ""
    
    # Get size information
    item_size = get_item_size(item)
    size_str = format_size(item_size)
    
    user_data = item.get('UserData', {})
    is_played = user_data.get('Played', False)
    last_played = user_data.get('LastPlayedDate')
    date_created = item.get('DateCreated')
    path = item.get('Path', '')
    formatted_path = format_path(path)
    
    if not is_played:
        # Show when it was added
        if date_created:
            try:
                created_obj = parse_jellyfin_datetime(date_created)
                status = f"Never watched (added {created_obj.strftime('%Y-%m-%d')})"
            except:
                status = "Never watched"
        else:
            status = "Never watched"
    elif not last_played:
        status = "Watched (no date available)"
    else:
        try:
            date_obj = parse_jellyfin_datetime(last_played)
            # Calculate how long ago it was watched
            now = datetime.now()
            days_ago = (now - date_obj.replace(tzinfo=None)).days
            
            if days_ago < 30:
                time_ago = f"{days_ago} days ago"
            elif days_ago < 365:
                months_ago = days_ago // 30
                time_ago = f"{months_ago} month{'s' if months_ago != 1 else ''} ago"
            else:
                years_ago = days_ago // 365
                time_ago = f"{years_ago} year{'s' if years_ago != 1 else ''} ago"
            
            status = f"Last watched {date_obj.strftime('%Y-%m-%d')} ({time_ago})"
        except:
            status = "Watched (invalid date)"
    
    return f"{item_type}: {name}{year_str} - {status} - {size_str} - {formatted_path}"


def list_old_or_unwatched_content(items: List[Dict[Any, Any]], server_url: str, api_key: str) -> List[str]:
    """Main function to list content not watched in X months or never played (but added Y+ months ago), with allowlist protection"""
    slack_formatted_items_list = []
    
    if not items:
        print("❌ No movies or TV shows found")
        return ["❌ No movies or TV shows found"]
    
    print(f"🔍 Filtering content not watched in {OLD_CONTENT_MONTHS_CUTOFF}+ months or never played (excluding recently added)...")
    old_or_unwatched, protected_items = filter_old_or_unwatched_items(items)
    
    # Show protection info
    if protected_items:
        protected_size = sum(get_item_size(item) for item in protected_items)
        print(f"🛡️  Protected {len(protected_items)} items from allowlist ({format_size(protected_size)})")
        print("   Protected items:")
        for item in protected_items[:10]:  # Show first 10
            formatted_info = format_simple_item_info(item)
            print(f"     • {formatted_info}")
        if len(protected_items) > 10:
            print(f"     • ... and {len(protected_items) - 10} more")
        print()
    
    if not old_or_unwatched:
        print("✅ All remaining content has been watched recently!")
        return ["✅ All remaining content has been watched recently - no movies should be deleted!"]
    
    # Calculate sizes for TV series in the filtered results only (to avoid being slow)
    series_to_process = [item for item in old_or_unwatched if item.get('Type') == 'Series']
    if series_to_process:
        print(f"📏 Calculating sizes for {len(series_to_process)} TV series (this may take a moment)...")
        for i, item in enumerate(series_to_process, 1):
            series_id = item.get('Id')
            series_name = item.get('Name', 'Unknown')
            if series_id:
                print(f"   {i}/{len(series_to_process)}: {series_name}...")
                total_size = get_series_total_size(server_url, api_key, series_id)
                item['_calculated_size'] = total_size
    
    # Sort by size (biggest first) for better deletion prioritization
    print("📊 Sorting by size (largest first)...")
    old_or_unwatched.sort(key=lambda x: get_item_size(x), reverse=True)
    
    print(f"\n📋 Content not watched in {OLD_CONTENT_MONTHS_CUTOFF}+ months or never played (sorted by size, largest first):")
    print("=" * 120)
    
    total_size = 0
    for i, item in enumerate(old_or_unwatched, 1):
        formatted_info = format_simple_item_info(item)
        item_size = get_item_size(item)
        total_size += item_size
        
        # Add ranking number and show full info including type - print to terminal
        print(f"{i:3d}. {formatted_info}")
        # Add to Slack list
        slack_formatted_items_list.append(f"{i:3d}. {formatted_info}")
    
    print("=" * 120)
    print(f"💾 Total size of items to consider for deletion: {format_size(total_size)}")
    
    # Summary statistics
    movies = [item for item in old_or_unwatched if item.get('Type') == 'Movie']
    series = [item for item in old_or_unwatched if item.get('Type') == 'Series']
    never_watched = [item for item in old_or_unwatched if not item.get('UserData', {}).get('Played', False)]
    old_watched = [item for item in old_or_unwatched if item.get('UserData', {}).get('Played', False)]
    
    # Calculate size breakdown
    movies_size = sum(get_item_size(item) for item in movies)
    series_size = sum(get_item_size(item) for item in series)
    never_watched_size = sum(get_item_size(item) for item in never_watched)
    old_watched_size = sum(get_item_size(item) for item in old_watched)
    
    print(f"\n📊 Summary:")
    print(f"  🎬 Movies: {len(movies)} ({format_size(movies_size)})")
    print(f"  📺 TV Series: {len(series)} ({format_size(series_size)})")
    print(f"  📥 Never watched (but added {MIN_AGE_MONTHS}+ months ago): {len(never_watched)} ({format_size(never_watched_size)})")
    print(f"  📅 Watched but not in {OLD_CONTENT_MONTHS_CUTOFF}+ months: {len(old_watched)} ({format_size(old_watched_size)})")
    print(f"  📈 Total needing attention: {len(old_or_unwatched)} items ({format_size(total_size)}) out of {len(items)} total items")
    if protected_items:
        protected_total_size = sum(get_item_size(item) for item in protected_items)
        print(f"  🛡️  Protected by allowlist: {len(protected_items)} items ({format_size(protected_total_size)})")
    print(f"  💡 Note: Recently added content (< {MIN_AGE_MONTHS} months) is excluded from 'never watched'")
    
    return slack_formatted_items_list


def get_first_episode_for_series(server_url: str, api_key: str, series_id: str) -> Dict[str, Any]:
    """Get the first episode of a TV series to check its media streams"""
    try:
        headers = {
            'X-Emby-Token': api_key,
            'Content-Type': 'application/json'
        }
        
        # Get all episodes for this series
        params = {
            'ParentId': series_id,
            'IncludeItemTypes': 'Episode',
            'Recursive': 'true',
            'Fields': 'MediaSources',
            'SortBy': 'SortName',
            'SortOrder': 'Ascending',
            'Limit': 1  # Just get the first episode
        }
        
        url = f"{server_url}/Items"
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        episodes = data.get('Items', [])
        
        if episodes:
            return episodes[0]  # Return the first episode
        else:
            return {}
            
    except Exception as e:
        print(f"      ⚠️  Failed to get first episode for series {series_id}: {e}")
        return {}


def get_all_episodes_for_series(server_url: str, api_key: str, series_id: str) -> List[Dict[str, Any]]:
    """Get all episodes of a TV series to check their media streams"""
    try:
        headers = {
            'X-Emby-Token': api_key,
            'Content-Type': 'application/json'
        }
        
        # Get all episodes for this series
        params = {
            'ParentId': series_id,
            'IncludeItemTypes': 'Episode',
            'Recursive': 'true',
            'Fields': 'MediaSources,SeasonName,IndexNumber,ParentIndexNumber',
            'SortBy': 'ParentIndexNumber,IndexNumber',
            'SortOrder': 'Ascending',
            'Limit': 10000  # Get all episodes
        }
        
        url = f"{server_url}/Items"
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        episodes = data.get('Items', [])
        
        return episodes
            
    except Exception as e:
        print(f"      ⚠️  Failed to get all episodes for series {series_id}: {e}")
        return []


def check_episode_audio_languages(episode: Dict[str, Any]) -> Dict[str, Any]:
    """Check if a single episode has English and French audio tracks, and French subtitles"""
    media_sources = episode.get('MediaSources', [])
    
    if not media_sources:
        return {
            'has_english': False,
            'has_french': False,
            'has_french_subs': False,
            'audio_languages': [],
            'audio_tracks': [],
            'subtitle_languages': []
        }
    
    # Get the first media source (usually the main file)
    media_source = media_sources[0]
    media_streams = media_source.get('MediaStreams', [])
    
    audio_languages = set()
    subtitle_languages = set()
    audio_tracks = []
    has_english = False
    has_french = False
    has_french_subs = False
    
    for stream in media_streams:
        if stream.get('Type') == 'Audio':
            language = stream.get('Language', 'unknown').lower()
            title = stream.get('Title', '')
            codec = stream.get('Codec', '')
            channels = stream.get('Channels', 0)
            is_default = stream.get('IsDefault', False)
            
            audio_track = {
                'language': language,
                'title': title,
                'codec': codec,
                'channels': channels,
                'is_default': is_default
            }
            audio_tracks.append(audio_track)
            
            if language != 'unknown':
                audio_languages.add(language)
                
            # Check for English variants
            if language in ['eng', 'en', 'english']:
                has_english = True
                
            # Check for French variants
            if language in ['fre', 'fr', 'french', 'fra']:
                has_french = True
        
        elif stream.get('Type') == 'Subtitle':
            language = stream.get('Language', 'unknown').lower()
            if language != 'unknown':
                subtitle_languages.add(language)
            
            # Check for French subtitle variants
            if language in ['fre', 'fr', 'french', 'fra']:
                has_french_subs = True
    
    return {
        'has_english': has_english,
        'has_french': has_french,
        'has_french_subs': has_french_subs,
        'audio_languages': sorted(list(audio_languages)),
        'audio_tracks': audio_tracks,
        'subtitle_languages': sorted(list(subtitle_languages))
    }


def check_all_episodes_audio_languages(server_url: str, api_key: str, series_id: str, series_name: str) -> Dict[str, Any]:
    """Check all episodes of a TV series for English and French audio tracks, and French subtitles"""
    print(f"   📺 Checking all episodes of series: {series_name}...")
    
    episodes = get_all_episodes_for_series(server_url, api_key, series_id)
    
    if not episodes:
        return {
            'has_english': False,
            'has_french': False,
            'has_french_subs': False,
            'audio_languages': [],
            'audio_tracks': [],
            'subtitle_languages': [],
            'total_episodes': 0,
            'episodes_checked': 0,
            'problematic_episodes': [],
            'is_consistent': True,
            'summary': f"No episodes found for {series_name}"
        }
    
    total_episodes = len(episodes)
    episodes_checked = 0
    problematic_episodes = []
    all_languages = set()
    all_subtitle_languages = set()
    all_audio_tracks = []
    
    # Track overall language availability
    series_has_english = True  # Start optimistic, will be False if any episode lacks English
    series_has_french = True   # Start optimistic, will be False if any episode lacks French
    series_has_french_subs = True  # Start optimistic, will be False if any episode lacks French subs
    
    print(f"   📊 Found {total_episodes} episodes to check...")
    
    for episode in episodes:
        episode_name = episode.get('Name', 'Unknown')
        season_number = episode.get('ParentIndexNumber', 0)
        episode_number = episode.get('IndexNumber', 0)
        episode_identifier = f"S{season_number:02d}E{episode_number:02d}"
        
        # Check if this specific episode is exempt from language checking
        if is_episode_language_check_allowlisted(series_name, season_number, episode_number):
            episodes_checked += 1
            print(f"   🔇 Skipping language check for {episode_identifier} ({episode_name}) - in episode allowlist")
            continue
        
        episode_lang_check = check_episode_audio_languages(episode)
        episodes_checked += 1
        
        # Add languages to overall set
        all_languages.update(episode_lang_check['audio_languages'])
        all_subtitle_languages.update(episode_lang_check.get('subtitle_languages', []))
        all_audio_tracks.extend(episode_lang_check['audio_tracks'])
        
        # Check if this episode has language issues
        episode_has_english = episode_lang_check['has_english']
        episode_has_french = episode_lang_check['has_french']
        episode_has_french_subs = episode_lang_check.get('has_french_subs', False)
        
        # Update series-level language flags
        if not episode_has_english:
            series_has_english = False
        if not episode_has_french:
            series_has_french = False
        if not episode_has_french_subs:
            series_has_french_subs = False
        
        # Record problematic episodes
        if not episode_has_english or not episode_has_french:
            missing_langs = []
            if not episode_has_english:
                missing_langs.append('English')
            if not episode_has_french:
                missing_langs.append('French')
            
            problematic_episodes.append({
                'identifier': episode_identifier,
                'name': episode_name,
                'season': season_number,
                'episode': episode_number,
                'missing_languages': missing_langs,
                'available_languages': episode_lang_check['audio_languages'],
                'has_english': episode_has_english,
                'has_french': episode_has_french,
                'has_french_subs': episode_has_french_subs,
                'subtitle_languages': episode_lang_check.get('subtitle_languages', [])
            })
    
    # Determine if the series is consistent (all episodes have same language availability)
    is_consistent = len(problematic_episodes) == 0
    
    # Create summary
    if is_consistent:
        summary = f"All {total_episodes} episodes have both English and French audio"
    else:
        summary = f"{len(problematic_episodes)} of {total_episodes} episodes missing language tracks"
    
    return {
        'has_english': series_has_english,
        'has_french': series_has_french,
        'has_french_subs': series_has_french_subs,
        'audio_languages': sorted(list(all_languages)),
        'audio_tracks': all_audio_tracks,
        'subtitle_languages': sorted(list(all_subtitle_languages)),
        'total_episodes': total_episodes,
        'episodes_checked': episodes_checked,
        'problematic_episodes': problematic_episodes,
        'is_consistent': is_consistent,
        'summary': summary
    }


def check_audio_languages(item: Dict[Any, Any], server_url: str = None, api_key: str = None) -> Dict[str, Any]:
    """Check if item has English and French audio tracks, and French subtitles"""
    
    # For TV Series, check all episodes instead of just the first one
    if item.get('Type') == 'Series' and server_url and api_key:
        series_id = item.get('Id')
        series_name = item.get('Name', 'Unknown')
        if series_id:
            return check_all_episodes_audio_languages(server_url, api_key, series_id, series_name)
        else:
            return {
                'has_english': False,
                'has_french': False,
                'has_french_subs': False,
                'audio_languages': [],
                'audio_tracks': [],
                'subtitle_languages': [],
                'total_episodes': 0,
                'episodes_checked': 0,
                'problematic_episodes': [],
                'is_consistent': True,
                'summary': f"No series ID found for {series_name}"
            }
    else:
        # For movies, use the item's own MediaSources
        media_sources = item.get('MediaSources', [])
        
        if not media_sources:
            return {
                'has_english': False,
                'has_french': False,
                'has_french_subs': False,
                'audio_languages': [],
                'audio_tracks': [],
                'subtitle_languages': []
            }
        
        # Get the first media source (usually the main file)
        media_source = media_sources[0]
        media_streams = media_source.get('MediaStreams', [])
        
        audio_languages = set()
        subtitle_languages = set()
        audio_tracks = []
        has_english = False
        has_french = False
        has_french_subs = False
        
        for stream in media_streams:
            if stream.get('Type') == 'Audio':
                language = stream.get('Language', 'unknown').lower()
                title = stream.get('Title', '')
                codec = stream.get('Codec', '')
                channels = stream.get('Channels', 0)
                is_default = stream.get('IsDefault', False)
                
                audio_track = {
                    'language': language,
                    'title': title,
                    'codec': codec,
                    'channels': channels,
                    'is_default': is_default
                }
                audio_tracks.append(audio_track)
                
                if language != 'unknown':
                    audio_languages.add(language)
                    
                # Check for English variants
                if language in ['eng', 'en', 'english']:
                    has_english = True
                    
                # Check for French variants
                if language in ['fre', 'fr', 'french', 'fra']:
                    has_french = True
            
            elif stream.get('Type') == 'Subtitle':
                language = stream.get('Language', 'unknown').lower()
                if language != 'unknown':
                    subtitle_languages.add(language)
                
                # Check for French subtitle variants
                if language in ['fre', 'fr', 'french', 'fra']:
                    has_french_subs = True
        
        return {
            'has_english': has_english,
            'has_french': has_french,
            'has_french_subs': has_french_subs,
            'audio_languages': sorted(list(audio_languages)),
            'audio_tracks': audio_tracks,
            'subtitle_languages': sorted(list(subtitle_languages))
        }


def filter_recent_items(items: List[Dict[Any, Any]], days_back: int = 30) -> List[Dict[Any, Any]]:
    """Filter items added in the last X days"""
    cutoff_date = datetime.now() - timedelta(days=days_back)
    recent_items = []
    
    for item in items:
        date_created = item.get('DateCreated')
        if date_created:
            try:
                created_datetime = parse_jellyfin_datetime(date_created)
                created_naive = created_datetime.replace(tzinfo=None)
                
                if created_naive >= cutoff_date:
                    recent_items.append(item)
            except Exception:
                pass  # Skip items with invalid dates
    
    return recent_items


def list_recent_items_language_check(items: List[Dict[Any, Any]], server_url: str, api_key: str, days_back: int = 30) -> List[str]:
    """List recently added items and flag those missing English/French audio"""
    slack_formatted_items_list = []
    
    print(f"🕒 Filtering items added in the last {days_back} days...")
    recent_items = filter_recent_items(items, days_back)
    
    if not recent_items:
        print(f"✅ No items found added in the last {days_back} days")
        return [f"✅ No items found added in the last {days_back} days - no language issues found"]
    
    # Sort by date added (newest first)
    recent_items.sort(key=lambda x: x.get('DateCreated', ''), reverse=True)
    
    print(f"\n📋 Recently Added Content ({len(recent_items)} items):")
    print("=" * 140)
    
    missing_languages = []
    complete_items = []
    
    for i, item in enumerate(recent_items, 1):
        name = item.get('Name', 'Unknown')
        item_type = item.get('Type', 'Unknown')
        year = item.get('ProductionYear', '')
        year_str = f" ({year})" if year else ""
        date_created = item.get('DateCreated', '')
        
        # Format date
        date_str = "Unknown date"
        if date_created:
            try:
                created_obj = parse_jellyfin_datetime(date_created)
                date_str = created_obj.strftime('%Y-%m-%d')
            except:
                pass
        
        # Check if this item is globally exempt from language checking
        if is_language_check_allowlisted(item):
            complete_items.append(item)
            print(f"{i:3d}. {item_type}: {name}{year_str} | Added: {date_str} | 🔇 LANGUAGE CHECK SKIPPED (Global Allowlist)")
            continue
        
        # Check audio languages (pass server credentials for TV series)
        lang_check = check_audio_languages(item, server_url, api_key)
        
        # Check if this item is in the French-only allowlist
        is_french_only = is_french_only_allowlisted(item)
        
        # Check if this item is in the French subs only allowlist
        is_french_subs_only = is_french_subs_only_allowlisted(item)
        
        # Create status indicators
        status_indicators = []
        if lang_check['has_english']:
            status_indicators.append("🇬🇧 EN")
        else:
            if is_french_only or is_french_subs_only:
                status_indicators.append("⚪ EN")  # Neutral - not required for French-only or French subs only content
            else:
                status_indicators.append("❌ EN")
            
        if lang_check['has_french']:
            status_indicators.append("🇫🇷 FR")
        else:
            if is_french_subs_only and lang_check.get('has_french_subs', False):
                status_indicators.append("⚪ FR")  # Neutral - French audio not required if has French subs
            else:
                status_indicators.append("❌ FR")
        
        status_str = " | ".join(status_indicators)
        
        # Add special mode indicators if applicable
        french_only_indicator = ""
        if is_french_only:
            french_only_indicator = " [🇫🇷 FRENCH-ONLY OK]"
        elif is_french_subs_only and lang_check.get('has_french_subs', False):
            french_only_indicator = " [🇫🇷 FR SUBS OK]"
        
        # Show all available audio languages
        available_langs = ", ".join(lang_check['audio_languages']) if lang_check['audio_languages'] else "None"
        
        # Get and format the path
        path = item.get('Path', '')
        formatted_path = format_path(path)
        
        # For TV series with detailed episode analysis, add episode summary
        episode_summary = ""
        if item_type == 'Series' and 'total_episodes' in lang_check:
            total_eps = lang_check.get('total_episodes', 0)
            problematic_eps = lang_check.get('problematic_episodes', [])
            
            # For French subs only items, filter out episodes that have French subtitles
            if is_french_subs_only and problematic_eps:
                problematic_eps = [ep for ep in problematic_eps 
                                   if not ep.get('has_french_subs', False)]
            
            if problematic_eps:
                # Group problematic episodes by season
                seasons_dict = {}
                for ep in problematic_eps:
                    season_num = ep['season']
                    episode_num = ep['episode']
                    if season_num not in seasons_dict:
                        seasons_dict[season_num] = []
                    seasons_dict[season_num].append(episode_num)
                
                # Sort seasons and episodes
                season_summaries = []
                for season_num in sorted(seasons_dict.keys()):
                    episodes = sorted(seasons_dict[season_num])
                    episodes_str = ",".join(map(str, episodes))
                    season_summaries.append(f"S{season_num}({episodes_str})")
                
                # Create the summary
                seasons_summary = " - ".join(season_summaries)
                episode_summary = f" | Episodes: {len(problematic_eps)}/{total_eps} problematic => {seasons_summary}"
            else:
                episode_summary = f" | Episodes: All {total_eps} OK"
        
        # Format the line
        line = f"{i:3d}. {item_type}: {name}{year_str} | Added: {date_str} | {status_str} | Available: {available_langs}{french_only_indicator}{episode_summary} - {formatted_path}"
        
        # Categorize items based on requirements
        needs_attention = False
        
        if is_french_only:
            # For French-only content, only require French audio
            if not lang_check['has_french']:
                needs_attention = True
        elif is_french_subs_only:
            # For French subs only content, only require French subtitles (no audio language requirements)
            if not lang_check.get('has_french_subs', False):
                needs_attention = True
        else:
            # For regular content, require both English and French audio
            if not lang_check['has_english'] or not lang_check['has_french']:
                needs_attention = True
        
        if needs_attention:
            missing_languages.append(item)
            # Print to terminal
            print(f"{line}")
            
            # For TV series with problematic episodes, show detailed episode list
            if item_type == 'Series' and 'problematic_episodes' in lang_check:
                detail_problematic_eps = lang_check.get('problematic_episodes', [])
                
                # For French subs only items, filter out episodes that have French subtitles
                if is_french_subs_only and detail_problematic_eps:
                    detail_problematic_eps = [ep for ep in detail_problematic_eps 
                                              if not ep.get('has_french_subs', False)]
                
                if detail_problematic_eps and len(detail_problematic_eps) <= 20:  # Show details only if not too many
                    print(f"   📺 Problematic episodes:")
                    
                    # Group by season for better display
                    episodes_by_season = {}
                    for ep in detail_problematic_eps:
                        season_num = ep['season']
                        if season_num not in episodes_by_season:
                            episodes_by_season[season_num] = []
                        episodes_by_season[season_num].append(ep)
                    
                    # Display grouped by season
                    for season_num in sorted(episodes_by_season.keys()):
                        season_episodes = episodes_by_season[season_num]
                        episode_numbers = [ep['episode'] for ep in season_episodes]
                        episode_numbers_str = ",".join(map(str, sorted(episode_numbers)))
                        
                        print(f"     Season {season_num}: Episodes {episode_numbers_str}")
                        
                        # Show detailed info for first few episodes in this season
                        for ep in season_episodes[:3]:  # Show details for first 3 episodes per season
                            missing_langs_str = ", ".join(ep['missing_languages'])
                            available_langs_str = ", ".join(ep['available_languages']) if ep['available_languages'] else "None"
                            subs_info = f", FR Subs: {'Yes' if ep.get('has_french_subs', False) else 'No'}" if is_french_subs_only else ""
                            print(f"       • {ep['identifier']} - Missing: {missing_langs_str}, Available: {available_langs_str}{subs_info}")
                        
                        if len(season_episodes) > 3:
                            print(f"       • ... and {len(season_episodes) - 3} more episodes in this season")
                            
                elif len(detail_problematic_eps) > 20:
                    print(f"   📺 {len(detail_problematic_eps)} problematic episodes (too many to list in detail)")
                    
                    # Still show the season summary even when there are too many episodes
                    episodes_by_season = {}
                    for ep in detail_problematic_eps:
                        season_num = ep['season']
                        if season_num not in episodes_by_season:
                            episodes_by_season[season_num] = []
                        episodes_by_season[season_num].append(ep['episode'])
                    
                    season_summaries = []
                    for season_num in sorted(episodes_by_season.keys()):
                        episode_count = len(episodes_by_season[season_num])
                        season_summaries.append(f"S{season_num}({episode_count} eps)")
                    
                    seasons_overview = " - ".join(season_summaries)
                    print(f"   📺 Affected seasons: {seasons_overview}")
            
            # Add to Slack list
            slack_formatted_items_list.append(f"{i:3d}. {item_type}: {name}{year_str} | Added: {date_str} | {status_str} | Available: {available_langs}{french_only_indicator}{episode_summary} - {formatted_path}")
        else:
            complete_items.append(item)
    
    print("=" * 140)
    
    # Summary with French-only, French subs only consideration and global language allowlist
    globally_exempt = [item for item in complete_items if is_language_check_allowlisted(item)]
    french_only_complete = [item for item in complete_items if is_french_only_allowlisted(item) and not is_language_check_allowlisted(item)]
    french_subs_only_complete = [item for item in complete_items if is_french_subs_only_allowlisted(item) and not is_french_only_allowlisted(item) and not is_language_check_allowlisted(item)]
    regular_complete = [item for item in complete_items if not is_french_only_allowlisted(item) and not is_french_subs_only_allowlisted(item) and not is_language_check_allowlisted(item)]
    french_only_problems = [item for item in missing_languages if is_french_only_allowlisted(item)]
    french_subs_only_problems = [item for item in missing_languages if is_french_subs_only_allowlisted(item) and not is_french_only_allowlisted(item)]
    regular_problems = [item for item in missing_languages if not is_french_only_allowlisted(item) and not is_french_subs_only_allowlisted(item)]
    
    print(f"\n📊 Summary for last {days_back} days:")
    print(f"  🎬 Movies: {len([i for i in recent_items if i.get('Type') == 'Movie'])}")
    print(f"  📺 TV Series: {len([i for i in recent_items if i.get('Type') == 'Series'])}")
    print(f"  ✅ Regular items with both EN & FR audio: {len(regular_complete)}")
    print(f"  🇫🇷 French-only items with FR audio (EN not required): {len(french_only_complete)}")
    print(f"  🎧 French subs only items with FR subs: {len(french_subs_only_complete)}")
    print(f"  🔇 Items globally exempt from language checks: {len(globally_exempt)}")
    print(f"  ⚠️  Regular items missing EN or FR audio: {len(regular_problems)}")
    print(f"  ⚠️  French-only items missing FR audio: {len(french_only_problems)}")
    print(f"  ⚠️  French subs only items missing FR subs: {len(french_subs_only_problems)}")
    print(f"  📈 Total items needing attention: {len(missing_languages)} out of {len(recent_items)}")
    
    # Return appropriate message
    if not slack_formatted_items_list:
        return [f"✅ All {len(recent_items)} recently added items have proper language tracks - no language issues found"]
    
    return slack_formatted_items_list


def get_jellyseer_unavailable_requests() -> List[str]:
    """Fetch and return unavailable requests from Jellyseer for Slack notification"""
    try:
        # Fetch requests
        requests_list = fetch_jellyseer_requests()
        
        # Analyze requests
        analysis = analyze_jellyseer_requests(requests_list)
        
        print(f"📊 Jellyseer Analysis: {analysis['summary']}")
        
        # Format unavailable requests for Slack
        slack_formatted_requests = []
        
        if analysis['unavailable_requests']:
            print(f"⏳ Found {len(analysis['unavailable_requests'])} unavailable requests")
            
            # Sort by release date (oldest first), then by creation date as secondary sort
            def sort_key(request):
                release_date = request.get('release_date', 'Unknown')
                created_at = request.get('createdAt', '')
                
                # Parse release date for sorting
                if release_date and release_date != 'Unknown' and release_date != 'Multiple seasons':
                    try:
                        if 'T' in release_date:  # ISO format
                            date_obj = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
                            return date_obj.date()
                        else:  # Simple date format
                            return datetime.strptime(release_date, '%Y-%m-%d').date()
                    except:
                        pass
                
                # If no valid release date, use a far future date so it sorts last
                # But still sort by creation date as secondary
                return datetime(9999, 12, 31).date()
            
            sorted_requests = sorted(
                analysis['unavailable_requests'], 
                key=sort_key
            )
            
            for req in sorted_requests:
                # Parse and format the creation date
                created_date = "Unknown date"
                if req.get('createdAt'):
                    try:
                        # Parse ISO date string
                        date_obj = datetime.fromisoformat(req['createdAt'].replace('Z', '+00:00'))
                        created_date = date_obj.strftime('%Y-%m-%d')
                    except:
                        created_date = req.get('createdAt', 'Unknown date')[:10]  # Just take first 10 chars as fallback
                
                # Handle TV series with season analysis differently
                if req.get('type') == 'tv' and req.get('season_analysis'):
                    season_analysis = req['season_analysis']
                    missing_seasons = season_analysis['missing_seasons']
                    
                    # Create detailed season info
                    if len(missing_seasons) <= 3:
                        # Show specific missing seasons
                        season_numbers = [str(s['season_number']) for s in missing_seasons]
                        season_info = f" [Missing seasons: {', '.join(season_numbers)}]"
                    else:
                        # Just show count if too many
                        season_info = f" [Missing {len(missing_seasons)} seasons]"
                    
                    formatted_request = f"{req['title']}{season_info} - Requested by {req['requestedBy']} on {created_date}"
                    
                else:
                    # Handle movies and TV series without season analysis
                    # Format release date
                    release_date = req.get('release_date', 'Unknown')
                    if release_date and release_date != 'Unknown' and release_date != 'Multiple seasons':
                        try:
                            # Parse and format the release date if it's a valid date
                            if 'T' in release_date:  # ISO format
                                date_obj = datetime.fromisoformat(release_date.replace('Z', '+00:00'))
                                release_date = date_obj.strftime('%Y-%m-%d')
                            elif len(release_date) > 10:  # Just take the date part if it's longer
                                release_date = release_date[:10]
                        except:
                            pass  # Keep original value if parsing fails
                    
                    # Clean format for Slack - just title, release date, and requester info
                    release_info = f" [Released: {release_date}]" if release_date != 'Unknown' and release_date != 'Multiple seasons' else ""
                    formatted_request = f"{req['title']}{release_info} - Requested by {req['requestedBy']} on {created_date}"
                
                slack_formatted_requests.append(formatted_request)
                
                # Also print to console
                print(f"   • {formatted_request}")
        
        # Format in-progress requests for Slack (Currently Airing section)
        in_progress_formatted = []
        if analysis.get('in_progress_requests'):
            in_progress_reqs = analysis['in_progress_requests']
            print(f"🔄 Found {len(in_progress_reqs)} series with currently airing seasons")
            
            for req in in_progress_reqs:
                # Parse and format the creation date
                created_date = "Unknown date"
                if req.get('createdAt'):
                    try:
                        date_obj = datetime.fromisoformat(req['createdAt'].replace('Z', '+00:00'))
                        created_date = date_obj.strftime('%Y-%m-%d')
                    except:
                        created_date = req.get('createdAt', 'Unknown date')[:10]
                
                # Format in-progress seasons info
                in_progress_seasons = req.get('in_progress_seasons', [])
                if in_progress_seasons:
                    # Build season info with episode progress
                    season_infos = []
                    for season in in_progress_seasons:
                        season_num = season.get('season_number', '?')
                        episodes_aired = season.get('episodes_aired', 0)
                        total_episodes = season.get('episode_count', 0)
                        season_infos.append(f"S{season_num} [{episodes_aired}/{total_episodes} episodes]")
                    
                    season_info = ", ".join(season_infos)
                    formatted_request = f"{req['title']} ({season_info}) - Requested by {req['requestedBy']} on {created_date}"
                else:
                    formatted_request = f"{req['title']} [Currently Airing] - Requested by {req['requestedBy']} on {created_date}"
                
                in_progress_formatted.append(formatted_request)
                print(f"   🔄 {formatted_request}")
        
        # Also report series that are complete for released seasons (informational)
        if analysis.get('complete_for_released_requests'):
            complete_requests = analysis['complete_for_released_requests']
            print(f"✅ Found {len(complete_requests)} TV series complete for all released seasons:")
            for req in complete_requests[:5]:  # Show first 5 as examples
                season_analysis = req['season_analysis']
                print(f"   ✓ {season_analysis['summary']}")
            if len(complete_requests) > 5:
                print(f"   ✓ ... and {len(complete_requests) - 5} more")
        
        # Build the final result combining unavailable and in-progress sections
        final_results = []
        
        # Add unavailable requests section with header
        if slack_formatted_requests:
            final_results.append(f"⏳ 🎬 Unavailable Requests ({len(slack_formatted_requests)} items):")
            final_results.extend(slack_formatted_requests)
        
        # Add "Currently Airing" section with a separator if we have both
        if in_progress_formatted:
            if final_results:
                final_results.append("")  # Empty line separator
            final_results.append(f"📺 Currently Airing ({len(in_progress_formatted)} items):")
            final_results.extend(in_progress_formatted)
        
        if not final_results:
            print("✅ No unavailable or in-progress requests found")
            final_results.append("✅ No unavailable requests found - all requests are processed!")
        
        return final_results
        
    except Exception as e:
        print(f"❌ Jellyseer check failed: {e}")
        return [f"❌ Failed to check Jellyseer requests: {e}"]


def get_jellyseer_recently_available_requests() -> List[str]:
    """Fetch and return requests that became available in the previous week from Jellyseer for Slack notification"""
    try:
        # Fetch requests
        requests_list = fetch_jellyseer_requests()
        
        print(f"📊 Checking {len(requests_list)} total Jellyseer requests for recently available items")
        
        # Calculate date range for the previous week (including today)
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        print(f"🗓️  Looking for requests made available between {week_ago} and {today} (inclusive)")
        
        # Find requests that became available in the previous week
        recently_available = []
        
        for request in requests_list:
            # Process available requests (status 5 = Available) and partially available (status 4 = Partially Available)
            media = request.get('media', {})
            media_status = media.get('status')  # Use media status instead of request status
            tmdb_id = media.get('tmdbId')
            
            # Debug: Show all TV requests to see what's being processed (can be removed later)
            # if media.get('mediaType') == 'tv':
            #     title = media.get('title', 'Unknown')
            #     print(f"   🔍 Found TV request: {title} (TMDB {tmdb_id}), media status {media_status}")
            
            if media_status in [4, 5]:  # Partially Available or Available
                media = request.get('media', {})
                media_type = media.get('mediaType', 'unknown')
                tmdb_id = media.get('tmdbId')
                
                # Get better title information
                title = 'Unknown'
                
                if media:
                    # Try to get title from different possible fields
                    title = (media.get('title') or 
                            media.get('name') or 
                            media.get('originalTitle') or 
                            media.get('originalName') or 
                            str(media.get('tmdbId', 'Unknown')))
                
                # Fetch additional details if we have a TMDB ID (French for recently available)
                if tmdb_id:
                    if media_type == 'movie':
                        details = fetch_movie_details(tmdb_id, 'fr')
                        if details:
                            title = details.get('title', title)
                    elif media_type == 'tv':
                        details = fetch_tv_details(tmdb_id, 'fr')
                        if details:
                            title = details.get('name', title)

                
                # Check if the request (or new seasons) became available in the previous week
                availability_date = None
                has_recent_seasons = False
                
                # For fully available series (status 5), use overall media date
                if media_status == 5:
                    media_added_at = media.get('mediaAddedAt') or request.get('modifiedAt')
                    if media_added_at:
                        try:
                            date_obj = datetime.fromisoformat(media_added_at.replace('Z', '+00:00'))
                            availability_date = date_obj.date()
                        except Exception as e:
                            print(f"⚠️  Could not parse availability date '{media_added_at}' for {title}: {e}")
                            continue
                
                # For partially available series (status 4), check for recent episodes
                elif media_status == 4 and media_type == 'tv':
                    print(f"   🔍 Checking partially available series: {title}")
                    # Check if any seasons are available (regardless of when they were added)
                    media_seasons = media.get('seasons', [])
                    if not media_seasons:
                        # Try to get season info from detailed media endpoint
                        detailed_media = fetch_media_details(tmdb_id, 'tv')
                        media_seasons = detailed_media.get('seasons', []) if detailed_media else []
                    
                    has_available_seasons = False
                    latest_season_date = None
                    has_recent_episodes = False
                    
                    for season in media_seasons:
                        if season.get('status') == 5:  # Available season
                            has_available_seasons = True
                            # Try to get a date for sorting purposes (use creation date if available)
                            season_created = season.get('createdAt') or season.get('updatedAt')
                            if season_created:
                                try:
                                    season_date_obj = datetime.fromisoformat(season_created.replace('Z', '+00:00'))
                                    season_date = season_date_obj.date()
                                    if latest_season_date is None or season_date > latest_season_date:
                                        latest_season_date = season_date
                                except Exception as e:
                                    print(f"⚠️  Could not parse season date '{season_created}': {e}")
                        
                        # For partially available seasons (status 4), check for recent episodes
                        elif season.get('status') == 4:  # Partially available season
                            season_num = season.get('seasonNumber')
                            if season_num and season_num > 0:  # Exclude Season 0 (specials)
                                print(f"   🔍 Checking partially available season {season_num} for recent episodes")
                                recent_eps = get_recent_episodes_for_season(tmdb_id, season_num, days_back=7)
                                if recent_eps:
                                    has_recent_episodes = True
                                    print(f"   ✅ Found {len(recent_eps)} recent episodes in season {season_num}")
                    
                    # Include series if it has fully available seasons OR recent episodes
                    if has_available_seasons or has_recent_episodes:
                        # For series with recent episodes, always include them
                        if has_recent_episodes:
                            availability_date = today  # Force inclusion by using today's date
                            print(f"   ✅ Including series {title} with recent episodes")
                        else:
                            # For series with fully available seasons, use existing logic
                            request_created = request.get('createdAt') or request.get('updatedAt')
                            if request_created:
                                try:
                                    request_date_obj = datetime.fromisoformat(request_created.replace('Z', '+00:00'))
                                    request_date = request_date_obj.date()
                                    # If the request was made recently, use today's date to ensure inclusion
                                    if request_date >= week_ago:
                                        availability_date = today  # Force inclusion by using today's date
                                        print(f"   ✅ Including recently requested partially available series {title} (requested: {request_date})")
                                    else:
                                        availability_date = latest_season_date or today
                                        print(f"   ✅ Including partially available series {title} with available seasons (date: {availability_date})")
                                except Exception as e:
                                    availability_date = latest_season_date or today
                                    print(f"   ✅ Including partially available series {title} with available seasons (date: {availability_date})")
                            else:
                                availability_date = latest_season_date or today
                                print(f"   ✅ Including partially available series {title} with available seasons (date: {availability_date})")
                    else:
                        print(f"   ⏩ No available seasons or recent episodes found for {title}")
                        continue
                
                # For TV series, get season information and recent episodes for better display
                available_seasons = []
                recent_episodes_by_season = {}  # Dict mapping season_num -> list of episode numbers
                missing_seasons = []
                
                if media_type == 'tv':
                    # Check if media has seasons data
                    media_seasons = media.get('seasons', [])
                    if not media_seasons:
                        # Try to get season info from detailed media endpoint
                        print(f"   🔍 Fetching detailed season info for {title} (TMDB: {tmdb_id})")
                        detailed_media = fetch_media_details(tmdb_id, 'tv')
                        media_seasons = detailed_media.get('seasons', []) if detailed_media else []
                    
                    if media_seasons:
                        # Get available seasons and check for recent episodes in partially available seasons
                        for season in media_seasons:
                            season_num = season.get('seasonNumber')
                            season_status = season.get('status')
                            
                            if season_num and season_num > 0:  # Exclude Season 0 (specials)
                                if season_status == 5:  # Fully available
                                    available_seasons.append(season_num)
                                elif season_status == 4:  # Partially available - check for recent episodes
                                    print(f"   🔍 Checking season {season_num} for recent episodes")
                                    recent_eps = get_recent_episodes_for_season(tmdb_id, season_num, days_back=7)
                                    if recent_eps:
                                        recent_episodes_by_season[season_num] = recent_eps
                                        print(f"   ✅ Season {season_num}: found recent episodes {recent_eps}")
                                elif season_status in [2, 3]:  # Missing or processing
                                    missing_seasons.append(season_num)
                        
                        available_seasons.sort()
                        missing_seasons.sort()
                
                # Check if this request became available in the previous week
                if availability_date:
                    # For series with recent episodes, always include them regardless of date
                    if media_type == 'tv' and recent_episodes_by_season:
                        print(f"   📅 {title} has recent episodes - including")
                    elif week_ago <= availability_date <= today:
                        print(f"   📅 {title} availability date {availability_date} is within range [{week_ago} to {today}] - including")
                    else:
                        print(f"   📅 {title} availability date {availability_date} is outside range [{week_ago} to {today}] - excluding")
                        continue
                    
                    request_info = {
                        'id': request.get('id'),
                        'title': title,
                        'type': media_type,
                        'requestedBy': request.get('requestedBy', {}).get('displayName', 'Unknown'),
                        'createdAt': request.get('createdAt'),
                        'availabilityDate': availability_date,
                        'available_seasons': available_seasons,  # Fully available seasons
                        'recent_episodes': recent_episodes_by_season,  # Recent episodes by season
                        'missing_seasons': missing_seasons,  # Missing seasons
                        'media': media
                    }
                    recently_available.append(request_info)
        
        # Format recently available requests for Slack
        slack_formatted_requests = []
        
        if recently_available:
            print(f"🎉 Found {len(recently_available)} requests made available in the previous week")
            
            # Deduplicate by title and content (episodes/seasons)
            # Use a dict to track seen combinations: key = (title, type, episodes_str or seasons_str)
            seen_items = {}
            deduplicated_requests = []
            
            for req in recently_available:
                # Create a unique key based on title, type, and content
                title = req['title']
                media_type = req['type']
                
                # Create a content signature
                if media_type == 'tv':
                    recent_episodes = req.get('recent_episodes', {})
                    available_seasons = req.get('available_seasons', [])
                    
                    if recent_episodes:
                        # Sort episodes by season and episode number for consistent comparison
                        episodes_signature = tuple(sorted((s, tuple(eps)) for s, eps in recent_episodes.items()))
                    else:
                        episodes_signature = tuple(sorted(available_seasons))
                    
                    content_key = (title, media_type, episodes_signature)
                else:
                    content_key = (title, media_type, None)
                
                # Only add if not seen before
                if content_key not in seen_items:
                    seen_items[content_key] = True
                    deduplicated_requests.append(req)
                else:
                    print(f"   ⚠️  Skipping duplicate: {title}")
            
            print(f"📊 After deduplication: {len(deduplicated_requests)} unique items")
            
            # Group requests by availability date
            requests_by_date = {}
            for req in deduplicated_requests:
                date_key = req['availabilityDate']
                if date_key not in requests_by_date:
                    requests_by_date[date_key] = []
                requests_by_date[date_key].append(req)
            
            # Sort dates (most recent first)
            sorted_dates = sorted(requests_by_date.keys(), reverse=True)
            
            print(f"📅 Grouped into {len(sorted_dates)} days")
            
            # Format each date group
            for date_key in sorted_dates:
                # Add date header
                date_header = get_french_day_name(date_key)
                slack_formatted_requests.append(f"\n{date_header}:")
                print(f"\n📅 {date_header}:")
                
                # Format each request in this date group
                for req in requests_by_date[date_key]:
                    # Clean format for WhatsApp - show title with media type in parentheses
                    media_type_display = "Film" if req['type'] == 'movie' else "Série" if req['type'] == 'tv' else req['type'].capitalize()
                    
                    # For TV series, add season and episode information
                    if req['type'] == 'tv':
                        parts = []
                        
                        # Check if we have recent episodes (ongoing series)
                        recent_episodes = req.get('recent_episodes', {})
                        missing_seasons = req.get('missing_seasons', [])
                        
                        if recent_episodes:
                            # Series with recent episodes - show them
                            episode_info_parts = []
                            for season_num in sorted(recent_episodes.keys()):
                                episode_nums = recent_episodes[season_num]
                                if episode_nums:
                                    # Format: S1E1, E2, E3, E4
                                    first_ep = f"S{season_num}E{episode_nums[0]}"
                                    if len(episode_nums) > 1:
                                        other_eps = ', '.join([f"E{ep}" for ep in episode_nums[1:]])
                                        episode_str = f"{first_ep}, {other_eps}"
                                    else:
                                        episode_str = first_ep
                                    episode_info_parts.append(episode_str)
                            
                            if episode_info_parts:
                                episodes_str = ', '.join(episode_info_parts)
                                parts.append(f"Épisodes disponibles: {episodes_str}")
                            
                            # Show missing seasons if any
                            if missing_seasons:
                                if len(missing_seasons) == 1:
                                    parts.insert(0, f"Missing seasons: {missing_seasons[0]}")
                                else:
                                    missing_str = ', '.join(map(str, missing_seasons))
                                    parts.insert(0, f"Missing seasons: {missing_str}")
                            
                            # Combine title with info - format: Title [Missing seasons: X] - Episodes disponibles: S1E1, E2, E3
                            if parts:
                                if missing_seasons and len(parts) > 1:
                                    # Format with missing seasons and episodes
                                    formatted_request = f"- {req['title']} [{parts[0]}] - {parts[1]} ({media_type_display})"
                                else:
                                    # Format with only episodes (no missing seasons)
                                    formatted_request = f"- {req['title']} - {parts[0]} ({media_type_display})"
                            else:
                                formatted_request = f"- {req['title']} ({media_type_display})"
                        
                        # No recent episodes - show fully available seasons (old behavior)
                        elif req.get('available_seasons'):
                            seasons = req['available_seasons']
                            if len(seasons) == 1:
                                season_info = f"Saison {seasons[0]}"
                            elif len(seasons) <= 5:
                                season_list = ', '.join(map(str, seasons))
                                season_info = f"Saisons {season_list}"
                            else:
                                # Too many seasons, show range
                                season_info = f"Saisons {seasons[0]}-{seasons[-1]} ({len(seasons)} saisons)"
                            
                            formatted_request = f"- {req['title']} - {season_info} ({media_type_display})"
                        else:
                            formatted_request = f"- {req['title']} ({media_type_display})"
                    else:
                        # Movies
                        formatted_request = f"- {req['title']} ({media_type_display})"
                    
                    slack_formatted_requests.append(formatted_request)
                    
                    # Also print to console
                    print(f"   • {formatted_request}")
        else:
            print("✅ No requests were made available in the previous week")
            slack_formatted_requests.append("✅ No requests were made available in the previous week")
        
        return slack_formatted_requests
        
    except Exception as e:
        print(f"❌ Jellyseer recently available check failed: {e}")
        return [f"❌ Failed to check recently available Jellyseer requests: {e}"]


if __name__ == "__main__":
    load_dotenv()
    
    print("\n" + "="*80 + "\n")
    
    JELLYSEER_CHECK = True
    JELLYSEER_RECENTLY_AVAILABLE_CHECK = True
    OLD_UNWATCHED_CHECK = True
    LANGUAGE_CHECK = True
    LARGE_MOVIE_CHECK = True

    if OLD_UNWATCHED_CHECK or LANGUAGE_CHECK or LARGE_MOVIE_CHECK:
        print("🎬 Connecting to Jellyfin server...")
        client, server_url, api_key = setup_jellyfin_client()
        
        print("👥 Getting all users...")
        users = get_all_users(server_url, api_key)

        # Keep only user jimmydore - DEBUGGING PURPOSES
        # users = [user for user in users if user.get('Name') == 'jimmydore']
        
        print("📺 Getting movies and TV shows from all users...")
        items = aggregate_all_user_data(server_url, api_key, users)

        print("\n" + "="*80 + "\n")



    if OLD_UNWATCHED_CHECK:
        # 1. List content not watched in X+ months (configured)
        old_or_unwatched_results = list_old_or_unwatched_content(items, server_url, api_key)
        
        # Send old/unwatched content notification
        if old_or_unwatched_results and len(old_or_unwatched_results) == 1 and old_or_unwatched_results[0].startswith("✅"):
            # Everything is OK message
            send_slack_message(f"✅ 🎬 Old/Unwatched Content OK")
        elif old_or_unwatched_results:
            # Problematic items found - format as code block for better readability
            message = f"🚨 🎬 Old/Unwatched Content - Items to Consider for Deletion ({len(old_or_unwatched_results)} items):\n```\n" + "\n".join(old_or_unwatched_results) + "\n```"
            send_slack_message(message)

        print("\n" + "="*80 + "\n")

    # 2. List large movies (configured size threshold) for manual redownload consideration
    if LARGE_MOVIE_CHECK:
        # Send large movies notification
        large_movies_results = list_large_movies(items, size_threshold_gb=LARGE_MOVIE_SIZE_THRESHOLD_GB)
        if large_movies_results and len(large_movies_results) == 1 and large_movies_results[0].startswith("✅"):
            # Everything is OK message
            send_slack_message(f"✅ 📦 Large Movies Check OK")
        elif large_movies_results:
            # Problematic items found - format as code block for better readability
            message = f"🚨 📦 Large Movies - Consider Redownloading in Lower Quality ({len(large_movies_results)} items):\n```\n" + "\n".join(large_movies_results[:10]) + "\n```"
            send_slack_message(message)

        print("\n" + "="*80 + "\n")

    if LANGUAGE_CHECK:
        # 3. Check recently added items for English/French audio
        language_check_results = list_recent_items_language_check(items, server_url, api_key, days_back=RECENT_ITEMS_DAYS_BACK)
        
        print("\n" + "="*80 + "\n")
        
        # Send Slack notifications
        print("📤 Sending Slack notifications...")

        # Send language check notification
        if language_check_results and len(language_check_results) == 1 and language_check_results[0].startswith("✅"):
            # Everything is OK message
            send_slack_message(f"✅ 🇫🇷 Language Check OK")
        elif language_check_results:
            # Problematic items found - format as code block for better readability
            message = f"🚨 🇫🇷 Recent Items with Language Issues ({len(language_check_results)} items):\n```\n" + "\n".join(language_check_results[:10]) + "\n```"
            send_slack_message(message)

    if JELLYSEER_CHECK:
        # 4. Check Jellyseer unavailable requests
        jellyseer_results = get_jellyseer_unavailable_requests()
        
        # Send Jellyseer unavailable requests notification
        if jellyseer_results and len(jellyseer_results) == 1 and jellyseer_results[0].startswith("✅"):
            # Everything is OK message
            send_slack_message(f"✅ 🎬 Jellyseer Requests OK")
        elif jellyseer_results:
            # Unavailable/in-progress requests found - format with code block for better readability
            message = "```\n" + "\n".join(jellyseer_results) + "\n```"
            send_slack_message(message)

    if JELLYSEER_RECENTLY_AVAILABLE_CHECK:
        # 5. Check Jellyseer recently available requests (past week)
        recently_available_results = get_jellyseer_recently_available_requests()
        
        # Send Jellyseer recently available requests notification
        if recently_available_results and len(recently_available_results) == 1 and recently_available_results[0].startswith("✅"):
            # Everything is OK message (no new available requests)
            send_slack_message(f"✅ 🎉 Jellyseer Recently Available OK")
        elif recently_available_results:
            # Recently available requests found - format as WhatsApp-friendly French message
            message = f"Salut les plexeurs,\nDerniers téléchargements disponibles sur le Plex :\n\n" + "\n".join(recently_available_results)
            send_slack_message(message)
    

    print("✅ Script execution completed!")