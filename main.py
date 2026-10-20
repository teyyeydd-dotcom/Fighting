"""
🎵 ᴀᴜᴅɪᴏ ꜰᴏʀᴡᴀʀᴅᴇʀ ʙᴏᴛ - ᴄᴏᴍᴘʟᴇᴛᴇ ꜰɪxᴇᴅ ᴠᴇʀꜱɪᴏɴ
ᴡɪᴛʜ ꜰᴜʟʟ ᴀᴜᴅɪᴏ ᴇꜰꜰᴇᴄᴛꜱ ᴀɴᴅ ᴘʀᴏᴘᴇʀ ᴇʀʀᴏʀ ʜᴀɴᴅʟɪɴɢ
ᴏɴʟʏ ᴏᴡɴᴇʀ ᴀɴᴅ ᴀᴘᴘʀᴏᴠᴇᴅ ᴜꜱᴇʀꜱ ᴄᴀɴ ᴜꜱᴇ ᴄᴏᴍᴍᴀɴᴅꜱ
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
import numpy as np
import os
import re
import json
import logging
import asyncio
import warnings
import time
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Try to import scipy, fallback to basic processing if not available
try:
    from scipy import signal
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False
    print("⚠️ ꜱᴄɪᴘʏ ʟᴏᴀᴅ ꜰᴀɪʟᴇᴅ - ʙᴀꜱɪᴄ ᴀᴜᴅɪᴏ ᴘʀᴏᴄᴇꜱꜱɪɴɢ ᴏɴʟʏ")

from pyrogram import Client, filters as pyro_filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.enums import ParseMode, ChatType
from pyrogram.errors import PeerIdInvalid

from pytgcalls import PyTgCalls, idle
from pytgcalls import filters as pytg_filters
from pytgcalls.types import (
    Device,
    Direction,
    ExternalMedia,
    MediaStream,
    RecordStream,
    StreamFrames
)
from pytgcalls.types.raw import AudioParameters
from pytgcalls.exceptions import NoActiveGroupCall

# ==================== ᴄᴏɴꜰɪɢᴜʀᴀᴛɪᴏɴ ====================
# ⚠️ Credentials hardcoded directly (no environment variables).
# Keep this file PRIVATE — anyone with it can control your bot & account.
API_ID = 30434687
API_HASH = "d4adb52774efd1cbbbebdfc1647b4ee9"
BOT_TOKEN = "8770566331:AAEocStpT3k50MLmJUPDSjYz9yMMjTxd3yI"
OWNER_ID = 6131324339
STRING_SESSION = "BQHQZX8ACta9g8RH-4_nxpPyW4hjp_2SkdhrPCMEPmu5I41VR87MrWY5VeVnVODjmAkLY4PPmFIM5fhuZhm-yDdTDj2Y5-tPiOLnCG76JDHrtonaG8Xxkzwj74AWUMeKChPoXO-rr-2EenrTuxK-79aw2-3COB7DRfHU0dqx2aX6FHeuD7_kT7EhMDLljUoMOJkJXiqcEJn9aix8O2pKL6HoEBaxEnjabBNn4-JWoE2Nn6FWWKGQjBqVetDdBLolPr6IPMOHOnUIJmGzEyiDuA22Tfp0lZ7llA3DyLowbNUtjmQe74j7vDyr9JkuoSbUwCOrDZr3LDy_Z7yJ1BZRcXhfPvVXxAAAAAFtdJWzAA"
RECORD_GROUP = -1004384774368
# ======================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Disable noisy logs
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pytgcalls").setLevel(logging.WARNING)

AUDIO_PARAMETERS = AudioParameters(bitrate=48000, channels=2)

# ==================== ᴄʟɪᴇɴᴛꜱ ====================
bot_app = Client("bot_session_v5", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_app = Client("user_session_v5", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION)
call_py = PyTgCalls(user_app)

# ==================== ꜱᴛᴀᴛᴇ ====================
forward_chats = set()
is_muted = False
is_recording = False
RECORD_SOURCE = RECORD_GROUP
processing_lock = asyncio.Lock()
bot_start_time = time.time()
auto_mute_enabled = False

# ᴜꜱᴇʀ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ
approved_users = set()

audio_config = {
    # ===== MAIN CONTROLS (TAGDA + CLEAR) =====
    'volume': 250,        # 200 → 220 (thoda aur loud, peak-safe)
    'bass': 60,           # 25 → 15 (kam bass = zyada clarity, voice mask nahi)
    'treble': 60,         # 35 → 45 (presence boost = crystal clear voice)
    'gain': 60,           # 6 → 25 (proper compression = consistent loudness)

    # ===== DYNAMICS =====
    'compressor': True,
    'limiter': True,

    # ===== FILTERS =====
    'highpass': True,     # ✅ ON — rumble/noise hatao
    'lowpass': False
}

# ==================== ᴘᴇʀꜱɪꜱᴛᴇɴᴄᴇ ====================

STATE_FILE = "bot_state.json"

def save_state():
    """ᴘᴇʀꜱɪꜱᴛ ᴀᴘᴘʀᴏᴠᴇᴅ ᴜꜱᴇʀꜱ ᴀɴᴅ ᴀᴜᴅɪᴏ ᴄᴏɴꜰɪɢ ᴛᴏ ᴅɪꜱᴋ"""
    try:
        tmp = f"{STATE_FILE}.tmp"
        with open(tmp, "w") as f:
            json.dump({
                "approved_users": sorted(approved_users),
                "audio_config": audio_config,
                "record_source": RECORD_SOURCE,
                "forward_chats": sorted(forward_chats),
                "auto_mute_enabled": auto_mute_enabled,
                "is_muted": is_muted,
                "string_session": STRING_SESSION,  # Save session
                "session_updated_at": time.time(),  # Track when session was updated
            }, f, indent=2)
        os.replace(tmp, STATE_FILE)
    except Exception as e:
        logger.error(f"ꜰᴀɪʟᴇᴅ ᴛᴏ ꜱᴀᴠᴇ ꜱᴛᴀᴛᴇ: {e}")

def load_state():
    """ʟᴏᴀᴅ ᴘᴇʀꜱɪꜱᴛᴇᴅ ꜱᴛᴀᴛᴇ ɪꜰ ᴀᴠᴀɪʟᴀʙʟᴇ"""
    global RECORD_SOURCE, auto_mute_enabled, is_muted, STRING_SESSION
    
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        
        # Load approved users
        approved_users.update(int(uid) for uid in data.get("approved_users", []))
        
        # Load audio config
        saved_config = data.get("audio_config")
        if isinstance(saved_config, dict):
            audio_config.update(saved_config)
        
        # Load record source
        saved_source = data.get("record_source")
        if saved_source is not None:
            RECORD_SOURCE = saved_source

        # Load forward chats
        saved_forwards = data.get("forward_chats")
        if isinstance(saved_forwards, list):
            forward_chats.update(int(cid) for cid in saved_forwards)
        
        # Load mute settings
        auto_mute_enabled = data.get("auto_mute_enabled", False)
        is_muted = data.get("is_muted", False)
        
        # ===== LOAD SESSION FROM STATE =====
        saved_session = data.get("string_session")
        if saved_session and isinstance(saved_session, str) and len(saved_session) > 50:
            STRING_SESSION = saved_session
            session_time = data.get("session_updated_at", "ɴᴏᴛ ᴛʀᴀᴄᴋᴇᴅ")
            logger.info(f"🔄 ꜱᴇꜱꜱɪᴏɴ ʟᴏᴀᴅᴇᴅ ꜰʀᴏᴍ ꜱᴛᴀᴛᴇ ꜰɪʟᴇ (ʟᴇɴɢᴛʜ: {len(STRING_SESSION)}, ᴜᴘᴅᴀᴛᴇᴅ: {session_time})")
        else:
            if saved_session:
                logger.warning(f"⚠️ ꜱᴀᴠᴇᴅ ꜱᴇꜱꜱɪᴏɴ ᴛᴏᴏ ꜱʜᴏʀᴛ (ʟᴇɴɢᴛʜ: {len(saved_session)}), ᴜꜱɪɴɢ ʜᴀʀᴅᴄᴏᴅᴇᴅ ᴏɴᴇ")
            else:
                logger.info("ℹ️ ɴᴏ ꜱᴇꜱꜱɪᴏɴ ꜰᴏᴜɴᴅ ɪɴ ꜱᴛᴀᴛᴇ, ᴜꜱɪɴɢ ʜᴀʀᴅᴄᴏᴅᴇᴅ ᴏɴᴇ")
        
        logger.info(f"✅ ʟᴏᴀᴅᴇᴅ ꜱᴛᴀᴛᴇ: {len(approved_users)} ᴀᴘᴘʀᴏᴠᴇᴅ ᴜꜱᴇʀ(ꜱ), ꜱᴏᴜʀᴄᴇ: {RECORD_SOURCE}, ᴍᴜᴛᴇᴅ: {is_muted}, ꜰᴏʀᴡᴀʀᴅꜱ: {len(forward_chats)}")
    except FileNotFoundError:
        logger.info("📄 ɴᴏ ꜱᴀᴠᴇᴅ ꜱᴛᴀᴛᴇ ꜰɪʟᴇ ꜰᴏᴜɴᴅ - ꜱᴛᴀʀᴛɪɴɢ ꜰʀᴇꜱʜ")
    except json.JSONDecodeError as e:
        logger.error(f"❌ ᴄᴏʀʀᴜᴘᴛᴇᴅ ꜱᴛᴀᴛᴇ ꜰɪʟᴇ: {e}")
        logger.info("🔄 ꜱᴛᴀʀᴛɪɴɢ ᴡɪᴛʜ ᴅᴇꜰᴀᴜʟᴛ ᴄᴏɴꜰɪɢᴜʀᴀᴛɪᴏɴ")
    except Exception as e:
        logger.error(f"❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ʟᴏᴀᴅ ꜱᴛᴀᴛᴇ: {e}")
        logger.info("🔄 ꜱᴛᴀʀᴛɪɴɢ ᴡɪᴛʜ ᴅᴇꜰᴀᴜʟᴛ ᴄᴏɴꜰɪɢᴜʀᴀᴛɪᴏɴ")

def reload_session():
    """ʀᴇʟᴏᴀᴅ ꜱᴇꜱꜱɪᴏɴ ꜰʀᴏᴍ ꜱᴛᴀᴛᴇ ꜰɪʟᴇ ᴡɪᴛʜᴏᴜᴛ ʀᴇꜱᴛᴀʀᴛɪɴɢ"""
    global STRING_SESSION
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
        
        saved_session = data.get("string_session")
        if saved_session and isinstance(saved_session, str) and len(saved_session) > 50:
            STRING_SESSION = saved_session
            logger.info(f"🔄 ꜱᴇꜱꜱɪᴏɴ ʀᴇʟᴏᴀᴅᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ (ʟᴇɴɢᴛʜ: {len(STRING_SESSION)})")
            return True
        else:
            logger.warning(f"⚠️ ɪɴᴠᴀʟɪᴅ ꜱᴇꜱꜱɪᴏɴ ɪɴ ꜱᴛᴀᴛᴇ ꜰɪʟᴇ (ʟᴇɴɢᴛʜ: {len(saved_session) if saved_session else 0})")
            return False
    except Exception as e:
        logger.error(f"❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ʀᴇʟᴏᴀᴅ ꜱᴇꜱꜱɪᴏɴ: {e}")
        return False

# ==================== ᴀᴜᴛʜᴇɴᴛɪᴄᴀᴛɪᴏɴ ====================

async def _authorized_filter(_, __, message):
    """ᴄʜᴇᴄᴋ ɪꜰ ᴜꜱᴇʀ ɪꜱ ᴏᴡɴᴇʀ ᴏʀ ᴀᴘᴘʀᴏᴠᴇᴅ"""
    user_id = message.from_user.id if message.from_user else None
    if user_id == OWNER_ID or user_id in approved_users:
        return True
    logger.info(f"ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴀᴄᴄᴇꜱꜱ ꜰʀᴏᴍ {user_id} - ɪɢɴᴏʀᴇᴅ")
    return False

def authorized_only():
    """ʀᴇᴛᴜʀɴ ᴀ ᴘʏʀᴏɢʀᴀᴍ ꜰɪʟᴛᴇʀ ᴛʜᴀᴛ ᴀʟʟᴏᴡꜱ ᴏɴʟʏ ᴏᴡɴᴇʀ/ᴀᴘᴘʀᴏᴠᴇᴅ ᴜꜱᴇʀꜱ"""
    return pyro_filters.create(_authorized_filter)

# ==================== ᴜᴛɪʟɪᴛʏ ꜰᴜɴᴄᴛɪᴏɴꜱ ====================

def escape_markdown(text):
    """Escape characters special to Pyrogram's legacy Markdown parser."""
    if not text:
        return ""
    specials = "\\`*_[]()~>#+-=|{}.!"
    return "".join("\\" + c if c in specials else c for c in text)

def get_uptime():
    """ɢᴇᴛ ʙᴏᴛ ᴜᴘᴛɪᴍᴇ"""
    uptime_seconds = int(time.time() - bot_start_time)
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    if days > 0:
        return f"{days}ᴅ {hours}ʜ {minutes}ᴍ {seconds}ꜱ"
    elif hours > 0:
        return f"{hours}ʜ {minutes}ᴍ {seconds}ꜱ"
    elif minutes > 0:
        return f"{minutes}ᴍ {seconds}ꜱ"
    else:
        return f"{seconds}ꜱ"

def create_progress_bar(value, max_val, length=12):
    """ᴄʀᴇᴀᴛᴇ ᴀ ᴠɪꜱᴜᴀʟ ᴘʀᴏɢʀᴇꜱꜱ ʙᴀʀ"""
    if not max_val:
        max_val = 1
    filled = int((value / max_val) * length)
    return "█" * filled + "░" * (length - filled)

def get_effect_status(value, max_val):
    """ɢᴇᴛ ꜱᴛᴀᴛᴜꜱ ʙᴀꜱᴇᴅ ᴏɴ ᴠᴀʟᴜᴇ"""
    if not max_val:
        max_val = 1
    percentage = (value / max_val) * 100
    if percentage == 0:
        return "⚪ ᴏꜰꜰ"
    elif percentage <= 30:
        return "🟢 ʟɪɢʜᴛ"
    elif percentage <= 60:
        return "🟡 ᴍᴇᴅɪᴜᴍ"
    elif percentage <= 80:
        return "🟠 ꜱᴛʀᴏɴɢ"
    else:
        return "🔴 ᴇxᴛʀᴇᴍᴇ"


# ==================== ᴀᴜᴅɪᴏ ᴘʀᴏᴄᴇꜱꜱɪɴɢ ====================

def apply_voice_priority_agc(audio_data, target_rms=9000.0, max_boost=3.0):
    """
    🎙️ VOICE AGC — SMOOTH & SAFE (FIGHT-READY)

    FIXES vs old:
      • target_rms 9000 (was 14000) → safe headroom, no cramming
      • max_boost 3x (was 10x)     → no severe pumping
      • smooth power curve          → no audible jumping
      • neutral mid-zone            → voice doesn't flutter
    """
    if audio_data is None or len(audio_data) == 0:
        return audio_data

    audio = audio_data.astype(np.float32)
    rms = float(np.sqrt(np.mean(audio ** 2) + 1e-9))

    if rms < 100:                      # silence / noise floor
        return audio_data

    if rms < target_rms:
        ratio = rms / target_rms       # 0..1
        # Smooth rise — quiet gets most, near-target ~1x
        boost = 1.0 + (max_boost - 1.0) * (1.0 - ratio) ** 1.5
    elif rms < target_rms * 2.0:
        boost = 1.0                    # neutral
    else:
        # Loud content — gentle reduce, floor -6dB
        boost = max(0.5, (target_rms * 1.5) / rms)

    audio *= boost
    audio = 32000.0 * np.tanh(audio / 32000.0)
    return np.clip(audio, -32768, 32767).astype(np.int16)


def apply_volume_boost(audio_data, level):
    """
    🔊 VOLUME — SANE GAIN CURVE (was 35x / +31dB → now 5x / +14dB max)
      • 0-100   → 0.1x .. 1.0x  (gentle cut / unity)
      • 100-200 → 1.0x .. 3.5x  (+10.9dB max)
      • 200-300 → 3.5x .. 5.0x  (hard cap +14dB)
    """
    if level <= 0:
        return audio_data
    if level == 100:
        return audio_data

    audio = audio_data.astype(np.float32)

    if level < 100:
        gain_factor = max(0.1, level / 100.0)
    elif level <= 200:
        gain_factor = 1.0 + ((level - 100) / 100.0) * 2.5
    else:
        gain_factor = 3.5 + min((level - 200) / 100.0, 1.5)

    gain_factor = min(gain_factor, 5.0)          # HARD CAP

    processed = audio * gain_factor
    processed = 32000.0 * np.tanh(processed / 31000.0)

    ceiling = 32500.0
    peak = float(np.max(np.abs(processed)))
    if peak > ceiling:
        processed *= (ceiling / peak)

    return np.clip(processed, -32768, 32767).astype(np.int16)


def apply_bass_boost_basic(audio_data, bass_level):
    """BASIC BASS — clean, no mud"""
    if bass_level <= 0:
        return audio_data

    audio = audio_data.astype(np.float32)
    window_size = max(4, int(40 - bass_level * 0.6))
    kernel = np.ones(window_size, dtype=np.float32) / window_size
    low = np.convolve(audio, kernel, mode="same")

    # Gentle mix — bass voice mask karta hai
    mix = min(0.4, bass_level / 150.0)
    processed = audio + (low * mix * 1.5)

    processed = 32500.0 * np.tanh(processed / 24000.0)
    return np.clip(processed, -32768, 32767).astype(np.int16)


def apply_bass_boost_advanced(audio_data, bass_level, sample_rate=48000):
    """
    ADVANCED BASS — max +12dB (was +24dB → muddy)
    Focus at 90Hz (was 50-74Hz → sub-bass rumble)
    """
    if bass_level == 0:
        return audio_data

    try:
        f0 = 85 + (bass_level * 0.3)        # 85..103Hz — voice body zone
        Q = 1.0
        gain_db = bass_level / 5.0          # 60 → +12dB max (was +24dB)

        w0 = 2 * np.pi * f0 / sample_rate
        A = 10 ** (gain_db / 40)
        cos_w0 = np.cos(w0)
        sin_w0 = np.sin(w0)
        alpha = sin_w0 / (2 * Q)

        b0 = 1 + alpha * A
        b1 = -2 * cos_w0
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * cos_w0
        a2 = 1 - alpha / A

        b = np.array([b0, b1, b2]) / a0
        a = np.array([1, a1 / a0, a2 / a0])

        filtered = signal.lfilter(b, a, audio_data.astype(np.float32))

        # Kill sub-bass rumble always
        b_hp, a_hp = signal.butter(2, 45 / (sample_rate / 2), btype='high')
        filtered = signal.lfilter(b_hp, a_hp, filtered)

        filtered = 32000.0 * np.tanh(filtered / 32000.0)
        return np.clip(filtered, -32768, 32767).astype(np.int16)

    except Exception as e:
        logger.error(f"ʙᴀꜱꜱ ᴀᴅᴠᴀɴᴄᴇᴅ ᴇʀʀᴏʀ: {e}")
        return apply_bass_boost_basic(audio_data, bass_level)


def apply_treble_boost_basic(audio_data, treble_level):
    """BASIC TREBLE — presence without harshness"""
    if treble_level <= 0:
        return audio_data

    audio = audio_data.astype(np.float32)
    window_size = 2
    kernel = np.ones(window_size, dtype=np.float32) / window_size
    low = np.convolve(audio, kernel, mode="same")
    high = audio - low

    mix = min(0.6, treble_level / 60.0)        # was 1.2 → half
    processed = audio + (high * mix)
    processed = 32500.0 * np.tanh(processed / 26000.0)
    return np.clip(processed, -32768, 32767).astype(np.int16)


def apply_treble_boost_advanced(audio_data, treble_level, sample_rate=48000):
    """
    ADVANCED TREBLE — +15dB max (was +33dB → ear-piercing)
    Focus at 3.5kHz (was 3.2kHz harsh sibilance zone)
    """
    if treble_level == 0:
        return audio_data

    try:
        f0 = 3500                            # presence band
        Q = 1.2                              # more focused
        gain_db = treble_level / 4.0         # 60 → +15dB max (was +33dB)

        w0 = 2 * np.pi * f0 / sample_rate
        A = 10 ** (gain_db / 40)
        cos_w0 = np.cos(w0)
        sin_w0 = np.sin(w0)
        alpha = sin_w0 / (2 * Q)

        b0 = 1 + alpha * A
        b1 = -2 * cos_w0
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * cos_w0
        a2 = 1 - alpha / A

        b = np.array([b0, b1, b2]) / a0
        a = np.array([1, a1 / a0, a2 / a0])

        filtered = signal.lfilter(b, a, audio_data.astype(np.float32))
        return np.clip(filtered, -32768, 32767).astype(np.int16)

    except Exception as e:
        logger.error(f"ᴀᴅᴠᴀɴᴄᴇᴅ ᴛʀᴇʙʟᴇ ᴇʀʀᴏʀ: {e}")
        return apply_treble_boost_basic(audio_data, treble_level)


def apply_de_esser(audio_data, amount=1.0, sample_rate=48000):
    """
    🐍 DE-ESSER — gentle high-shelf cut above 7kHz
    Prevents harsh "S / SH / CH" piercing after presence boost.
    """
    if not SCIPY_AVAILABLE or amount <= 0:
        return audio_data

    try:
        f0 = 7000.0
        Q = 0.7
        gain_db = -abs(amount) * 2.5          # gentle -2.5dB shelf cut

        w0 = 2 * np.pi * f0 / sample_rate
        A = 10 ** (gain_db / 40)
        cos_w0 = np.cos(w0)
        sin_w0 = np.sin(w0)
        alpha = sin_w0 / (2 * Q)

        b0 = 1 + alpha * A
        b1 = -2 * cos_w0
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * cos_w0
        a2 = 1 - alpha / A

        b = np.array([b0, b1, b2]) / a0
        a = np.array([1, a1 / a0, a2 / a0])

        filtered = signal.lfilter(b, a, audio_data.astype(np.float32))
        return np.clip(filtered, -32768, 32767).astype(np.int16)
    except Exception as e:
        logger.debug(f"De-esser error: {e}")
        return audio_data


def apply_soft_gain(audio_data, gain_level):
    """
    📈 PRO COMPRESSOR — FIXED (was 6.5x pre × 3.7x makeup = 24x = distortion)
      • pre_gain  max 4x   (+12dB)  was 6.5x
      • ratio     4:1               was 4.9:1
      • makeup    2.5x   (+8dB)    was 3.7x
    """
    if gain_level <= 0:
        return audio_data

    audio = audio_data.astype(np.float32)

    # ── STAGE 1: moderate pre-gain
    pre_gain = 1.0 + (gain_level / 20.0)       # 60 → 4.0x
    processed = audio * pre_gain

    # ── STAGE 2: soft-knee compressor
    if audio_config.get("compressor", True):
        threshold = 8000.0
        ratio = 2.5 + (gain_level / 40.0)      # 60 → 4.0:1
        knee = 3000.0

        abs_p = np.abs(processed)
        above = abs_p > threshold

        if np.any(above):
            x = abs_p[above]
            over = x - threshold
            soft = np.where(
                over < knee,
                threshold + (over ** 2) / (2.0 * knee),
                threshold + knee / 2.0 + (over - knee) / ratio
            )
            processed[above] = np.sign(processed[above]) * soft

        # ── STAGE 3: gentle makeup
        makeup = 1.0 + (gain_level / 40.0)     # 60 → 2.5x
        processed *= makeup

    # ── STAGE 4: soft limiter
    if audio_config.get("limiter", True):
        processed = 32000.0 * np.tanh(processed / 32000.0)
        ceiling = 32500.0
        peak = float(np.max(np.abs(processed)))
        if peak > ceiling:
            processed *= (ceiling / peak)

    return np.clip(processed, -32768, 32767).astype(np.int16)


def apply_loudness_maximizer(audio_data, target_rms=9000.0):
    """
    FINAL LOUDNESS — peak-safe, max +6dB (was +11dB)
    """
    if audio_data is None or len(audio_data) == 0:
        return audio_data

    audio = audio_data.astype(np.float32)
    rms = float(np.sqrt(np.mean(audio ** 2) + 1e-9))

    if rms <= 1.0:
        return audio_data

    if rms < target_rms:
        gain = min(target_rms / rms, 2.0)      # was 3.5x → now max +6dB
        audio *= gain

    audio = 32500.0 * np.tanh(audio / 32500.0)
    return np.clip(audio, -32768, 32767).astype(np.int16)


def process_audio(audio_data):
    """
    🥊 VC FIGHT CHAIN — CLEAN & POWERFUL

    ORDER:
      1. HPF 100Hz        — remove rumble
      2. AGC              — bring quiet up (gentle)
      3. Bass boost       — small voice body
      4. Presence boost   — intelligibility
      5. De-esser         — kill harsh S/SH
      6. Compressor/Gain  — consistent loudness
      7. Volume           — final gain
      8. Loudness Limiter — peak safety
    """
    if audio_data is None or len(audio_data) == 0:
        return audio_data

    try:
        processed = audio_data.astype(np.float32)
        config = audio_config

        # 1) HPF — 100Hz (was 80Hz → bass still muddy)
        if config.get('highpass', False) and SCIPY_AVAILABLE:
            try:
                nyquist = 24000
                b, a = signal.butter(2, 100 / nyquist, btype='high')
                processed = signal.lfilter(b, a, processed)
            except Exception as e:
                logger.debug(f"HPF failed: {e}")

        # 2) AGC — gentle voice priority
        processed = apply_voice_priority_agc(
            processed, target_rms=9000.0, max_boost=3.0
        )
        processed = np.clip(processed, -32768, 32767)

        # 3) Bass — small body, no mud
        if config.get('bass', 0) > 0:
            if SCIPY_AVAILABLE:
                processed = apply_bass_boost_advanced(processed, config.get('bass', 0))
            else:
                processed = apply_bass_boost_basic(processed, config.get('bass', 0))
            processed = np.clip(processed, -32768, 32767)

        # 4) Treble — presence, not harshness
        if config.get('treble', 0) > 0:
            if SCIPY_AVAILABLE:
                processed = apply_treble_boost_advanced(processed, config.get('treble', 0))
            else:
                processed = apply_treble_boost_basic(processed, config.get('treble', 0))
            processed = np.clip(processed, -32768, 32767)

        # 5) De-esser — clean sibilance
        if SCIPY_AVAILABLE and config.get('de_esser', True):
            processed = apply_de_esser(processed, amount=1.0)
            processed = np.clip(processed, -32768, 32767)

        # 6) Compressor / Gain — consistent loudness
        if config.get('gain', 0) > 0:
            processed = apply_soft_gain(processed, config.get('gain', 0))
            processed = np.clip(processed, -32768, 32767)

        # 7) Volume — final push (capped)
        if config.get('volume', 100) != 100:
            processed = apply_volume_boost(processed, config.get('volume', 100))
            processed = np.clip(processed, -32768, 32767)

        # 8) Loudness maximizer — peak-safe
        processed = apply_loudness_maximizer(processed, target_rms=9000.0)
        processed = np.clip(processed, -32768, 32767)

        return processed.astype(np.int16)

    except Exception as e:
        logger.error(f"ᴠᴄ ꜰɪɢʜᴛ ᴘʀᴏᴄᴇꜱꜱɪɴɢ ᴇʀʀᴏʀ: {e}")
        return audio_data.astype(np.int16) if audio_data.dtype != np.int16 else audio_data
        
# ==================== ᴀᴜᴅɪᴏ ʜᴀɴᴅʟᴇʀ ====================

async def _forward_incoming_frames(update):
    """ᴘʀᴏᴄᴇꜱꜱ ᴀɴᴅ ꜰᴏʀᴡᴀʀᴅ ᴀᴜᴅɪᴏ ꜰʀᴀᴍᴇꜱ"""
    global is_muted, forward_chats, RECORD_SOURCE, call_py  # ← FIX: Added all globals
    
    # 🔥 MUTE CHECK - SAB SE PEHLE
    if is_muted:
        return
    
    if update.chat_id != RECORD_SOURCE or not forward_chats:
        return
    
    async with processing_lock:
        try:
            if not update.frames:
                return
            frame_length = len(update.frames[0].frame) // 2
            # ᴀᴄᴄᴜᴍᴜʟᴀᴛᴇ ɪɴ ɪɴᴛ32 ᴛᴏ ᴀᴠᴏɪᴅ ɪɴᴛ16 ᴏᴠᴇʀꜰʟᴏᴡ ᴡʜᴇɴ ᴍɪxɪɴɢ ꜰʀᴀᴍᴇꜱ
            mixed_acc = np.zeros(frame_length, dtype=np.int32)
            valid_frames = 0
            for frame_data in update.frames:
                try:
                    source_samples = np.frombuffer(frame_data.frame, dtype=np.int16)
                    if len(source_samples) == frame_length:
                        mixed_acc += source_samples.astype(np.int32)
                        valid_frames += 1
                except Exception:
                    continue
            if valid_frames == 0:
                return
            mixed_acc //= valid_frames
            mixed_output = np.clip(mixed_acc, -32768, 32767).astype(np.int16)
            loop = asyncio.get_running_loop()
            processed_output = await loop.run_in_executor(None, process_audio, mixed_output)
            mixed_bytes = processed_output.tobytes()
            
            # ✅ FIX: Copy forward_chats to list to avoid mutation during iteration
            for chat_id in list(forward_chats):
                try:
                    await call_py.send_frame(chat_id, Device.MICROPHONE, mixed_bytes)
                except Exception as e:
                    logger.debug(f"ꜱᴇɴᴅ ᴇʀʀᴏʀ ᴛᴏ {chat_id}: {e}")
                    if "not found" in str(e).lower() or "invalid" in str(e).lower():
                        forward_chats.discard(chat_id)
                        logger.warning(f"ʀᴇᴍᴏᴠᴇᴅ {chat_id} ꜰʀᴏᴍ ꜰᴏʀᴡᴀʀᴅɪɴɢ ʟɪꜱᴛ")
        except Exception as e:
            logger.error(f"ᴀᴜᴅɪᴏ ʜᴀɴᴅʟᴇʀ ᴇʀʀᴏʀ: {e}")

# ==================== ᴄʜᴀᴛ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ====================

@call_py.on_update(pytg_filters.stream_frame(Direction.INCOMING, Device.MICROPHONE))
async def audio_forwarder(_, update: StreamFrames):
    await _forward_incoming_frames(update)


async def cache_chat_info(chat_id):
    """ᴄᴀᴄʜᴇ ᴄʜᴀᴛ ɪɴꜰᴏ ᴡɪᴛʜ ᴘʀᴏᴘᴇʀ ᴇʀʀᴏʀ ʜᴀɴᴅʟɪɴɢ"""
    try:
        logger.info(f"ᴄᴀᴄʜɪɴɢ ᴄʜᴀᴛ ɪɴꜰᴏ ꜰᴏʀ {chat_id}...")
        try:
            chat = await user_app.get_chat(chat_id)
            chat_title = chat.title if hasattr(chat, 'title') else str(chat_id)
            logger.info(f"✅ ᴄᴀᴄʜᴇᴅ: {chat_id} - {chat_title}")
            return True
        except (PeerIdInvalid, ValueError) as e:
            logger.debug(f"ᴅɪʀᴇᴄᴛ ɢᴇᴛ_ᴄʜᴀᴛ ꜰᴀɪʟᴇᴅ: {e}")
            try:
                async for dialog in user_app.get_dialogs(limit=50):
                    if dialog.chat.id == chat_id:
                        logger.info(f"✅ ꜰᴏᴜɴᴅ ɪɴ ᴅɪᴀʟᴏɢꜱ: {chat_id}")
                        return True
            except Exception:
                pass
            logger.error(f"❌ ᴄᴀɴɴᴏᴛ ꜰɪɴᴅ ᴄʜᴀᴛ: {chat_id}")
            return False
    except Exception as e:
        logger.error(f"ᴄᴀᴄʜᴇ ᴇʀʀᴏʀ ꜰᴏʀ {chat_id}: {e}")
        return False

async def join_call_safe(chat_id):
    """ꜱᴀꜰᴇʟʏ ᴊᴏɪɴ ᴄᴀʟʟ ᴡɪᴛʜ ᴀᴜᴛᴏ-ᴄʟᴇᴀɴᴜᴘ ᴀɴᴅ ʀᴇᴛʀʏ (ᴠᴄ-ᴄᴜᴛ ꜱᴀꜰᴇ)"""
    try:
        if not await cache_chat_info(chat_id):
            return False, "ᴄʜᴀᴛ ɴᴏᴛ ꜰᴏᴜɴᴅ ᴏʀ ɪɴᴀᴄᴄᴇꜱꜱɪʙʟᴇ"

        # ===== STEP 1: CLEAN any stale call state =====
        for _ in range(2):
            try:
                await call_py.leave_call(chat_id)
                await asyncio.sleep(0.4)
            except Exception:
                break

        # ===== STEP 2: JOIN with retry loop =====
        last_error = "ᴜɴᴋɴᴏᴡɴ ᴇʀʀᴏʀ"
        for attempt in range(4):
            try:
                await call_py.play(
                    chat_id,
                    MediaStream(ExternalMedia.AUDIO, AUDIO_PARAMETERS),
                )
                return True, None

            except NoActiveGroupCall:
                return False, "ɴᴏ ᴀᴄᴛɪᴠᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ"

            except Exception as e:
                err = str(e)
                err_low = err.lower()
                last_error = err

                # already participating / in call → force leave & retry
                if "already" in err_low and ("participat" in err_low or "in call" in err_low or "call" in err_low):
                    logger.warning(f"ᴀʟʀᴇᴀᴅʏ ɪɴ ᴄᴀʟʟ ({chat_id}) - ꜰᴏʀᴄɪɴɢ ʟᴇᴀᴠᴇ & ʀᴇᴛʀʏ")
                    try:
                        await call_py.leave_call(chat_id)
                        await asyncio.sleep(0.6)
                    except Exception:
                        pass
                    continue

                # group call invalid / ended / disconnected → cleanup & retry
                if any(k in err_low for k in [
                    "group call", "invalid", "not found",
                    "ended", "closed", "disconnected", "groupcall"
                ]):
                    logger.warning(f"ꜱᴛᴀʟᴇ ᴄᴀʟʟ ꜱᴛᴀᴛᴇ ({chat_id}) - ᴄʟᴇᴀɴɪɴɢ & ʀᴇᴛʀʏ: {err[:80]}")
                    try:
                        await call_py.leave_call(chat_id)
                        await asyncio.sleep(0.6)
                    except Exception:
                        pass
                    continue

                if attempt < 3:
                    await asyncio.sleep(0.5)
                    continue
                return False, err

        return False, last_error

    except Exception as e:
        return False, str(e)

# ==================== ᴄᴏᴍᴍᴀɴᴅꜱ ====================

# ===== ᴜꜱᴇʀ ᴍᴀɴᴀɢᴇᴍᴇɴᴛ ᴄᴏᴍᴍᴀɴᴅꜱ =====

@bot_app.on_message(pyro_filters.command("approve") & authorized_only())
async def cmd_approve(client, message):
    """ᴀᴘᴘʀᴏᴠᴇ ᴀ ᴜꜱᴇʀ ᴛᴏ ᴜꜱᴇ ᴛʜᴇ ʙᴏᴛ"""
    try:
        user_id = None
        user_mention = None
        username = None
        first_name = None
        if message.reply_to_message:
            user = message.reply_to_message.from_user
            user_id = user.id
            user_mention = user.mention
            username = user.username or "ɴᴏ ᴜꜱᴇʀɴᴀᴍᴇ"
            first_name = user.first_name or "ᴜɴᴋɴᴏᴡɴ"
        else:
            parts = message.text.split()
            if len(parts) < 2:
                await message.reply(
                    "❌ **ᴜꜱᴀɢᴇ:** `/approve` (ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ)\n"
                    "ᴏʀ: `/approve <ᴜꜱᴇʀ_ɪᴅ>`"
                )
                return
            try:
                user_id = int(parts[1])
                try:
                    user = await client.get_users(user_id)
                    user_mention = user.mention
                    username = user.username or "ɴᴏ ᴜꜱᴇʀɴᴀᴍᴇ"
                    first_name = user.first_name or "ᴜɴᴋɴᴏᴡɴ"
                except Exception:
                    user_mention = f"ᴜꜱᴇʀ {user_id}"
                    username = "ᴜɴᴋɴᴏᴡɴ"
                    first_name = "ᴜɴᴋɴᴏᴡɴ"
            except ValueError:
                await message.reply("❌ **ɪɴᴠᴀʟɪᴅ ᴜꜱᴇʀ ɪᴅ ꜰᴏʀᴍᴀᴛ!**")
                return
        if user_id in approved_users:
            await message.reply(
                f"ℹ️ **ᴜꜱᴇʀ ᴀʟʀᴇᴀᴅʏ ᴀᴘᴘʀᴏᴠᴇᴅ!**\n\n"
                f"👤 {user_mention}\n"
                f"🔢 `{user_id}`"
            )
            return
        approved_users.add(user_id)
        save_state()
        approve_msg = f"""
✅ **ᴜꜱᴇʀ ᴀᴘᴘʀᴏᴠᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!**

────────────────────
👤 **ɴᴀᴍᴇ:** {first_name} ({user_mention})
🔢 **ɪᴅ:** `{user_id}`
📝 **ᴜꜱᴇʀɴᴀᴍᴇ:** @{username}
📊 **ꜱᴛᴀᴛᴜꜱ:** 🟢 ᴀᴘᴘʀᴏᴠᴇᴅ
────────────────────

🎯 **ᴛʜᴇʏ ᴄᴀɴ ɴᴏᴡ ᴜꜱᴇ ᴛʜᴇ ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅꜱ!**
"""
        await message.reply(approve_msg)
        logger.info(f"ᴜꜱᴇʀ {user_id} ᴀᴘᴘʀᴏᴠᴇᴅ ʙʏ ᴏᴡɴᴇʀ")
    except Exception as e:
        await message.reply(f"❌ **ᴇʀʀᴏʀ:** `{str(e)}`")

@bot_app.on_message(pyro_filters.command("disapprove") & authorized_only())
async def cmd_disapprove(client, message):
    """ʀᴇᴍᴏᴠᴇ ᴜꜱᴇʀ ᴀᴘᴘʀᴏᴠᴀʟ"""
    try:
        user_id = None
        user_mention = None
        if message.reply_to_message:
            user = message.reply_to_message.from_user
            user_id = user.id
            user_mention = user.mention
        else:
            parts = message.text.split()
            if len(parts) < 2:
                await message.reply(
                    "❌ **ᴜꜱᴀɢᴇ:** `/disapprove` (ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴜꜱᴇʀ)\n"
                    "ᴏʀ: `/disapprove <ᴜꜱᴇʀ_ɪᴅ>`"
                )
                return
            try:
                user_id = int(parts[1])
                try:
                    user = await client.get_users(user_id)
                    user_mention = user.mention
                except Exception:
                    user_mention = f"ᴜꜱᴇʀ {user_id}"
            except ValueError:
                await message.reply("❌ **ɪɴᴠᴀʟɪᴅ ᴜꜱᴇʀ ɪᴅ ꜰᴏʀᴍᴀᴛ!**")
                return
        if user_id not in approved_users:
            await message.reply(
                f"ℹ️ **ᴜꜱᴇʀ ɴᴏᴛ ꜰᴏᴜɴᴅ ɪɴ ᴀᴘᴘʀᴏᴠᴇᴅ ʟɪꜱᴛ!**\n\n"
                f"👤 {user_mention}\n"
                f"🔢 `{user_id}`"
            )
            return
        approved_users.discard(user_id)
        save_state()
        disapprove_msg = f"""
❌ **ᴜꜱᴇʀ ᴅɪꜱᴀᴘᴘʀᴏᴠᴇᴅ!**

────────────────────
👤 **ɴᴀᴍᴇ:** {user_mention}
🔢 **ɪᴅ:** `{user_id}`
📊 **ꜱᴛᴀᴛᴜꜱ:** 🔴 ʀᴇᴍᴏᴠᴇᴅ
────────────────────

🚫 **ᴛʜᴇʏ ᴄᴀɴ ɴᴏ ʟᴏɴɢᴇʀ ᴜꜱᴇ ᴛʜᴇ ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅꜱ!**
"""
        await message.reply(disapprove_msg)
        logger.info(f"ᴜꜱᴇʀ {user_id} ᴅɪꜱᴀᴘᴘʀᴏᴠᴇᴅ ʙʏ ᴏᴡɴᴇʀ")
    except Exception as e:
        await message.reply(f"❌ **ᴇʀʀᴏʀ:** `{str(e)}`")

@bot_app.on_message(pyro_filters.command("userlist") & pyro_filters.user(OWNER_ID))
async def cmd_userlist(client, message):
    """ꜱʜᴏᴡ ʟɪꜱᴛ ᴏꜰ ᴀᴘᴘʀᴏᴠᴇᴅ ᴜꜱᴇʀꜱ"""
    try:
        if not approved_users:
            await message.reply(
                "📭 **ɴᴏ ᴜꜱᴇʀꜱ ᴀʀᴇ ᴀᴘᴘʀᴏᴠᴇᴅ ʏᴇᴛ.**\n\n"
                "ᴜꜱᴇ `/approve` ᴛᴏ ᴀᴅᴅ ᴜꜱᴇʀꜱ."
            )
            return
        user_list = []
        total = len(approved_users)
        processed = 0
        for user_id in approved_users:
            processed += 1
            try:
                user = await client.get_users(user_id)
                username = f"@{user.username}" if user.username else "ɴᴏ ᴜꜱᴇʀɴᴀᴍᴇ"
                mention = user.mention
                user_list.append(f"• {mention}\n  🔢 `{user_id}` | {username}")
            except Exception:
                user_list.append(f"• ᴜꜱᴇʀ `{user_id}` (⚠️ ᴄᴏᴜʟᴅ ɴᴏᴛ ꜰᴇᴛᴄʜ)")
        response = f"""
🔥 **ᴀᴘᴘʀᴏᴠᴇᴅ ᴜꜱᴇʀꜱ**

────────────────────
📊 **ᴛᴏᴛᴀʟ:** {total} ᴜꜱᴇʀꜱ
📌 **ᴘʀᴏᴄᴇꜱꜱɪɴɢ:** {processed}/{total}
────────────────────

"""
        response += "\n\n".join(user_list)
        response += f"\n\n────────────────────\n✅ **ᴛᴏᴛᴀʟ:** {total}"
        buttons = build_keyboard([
            ("🔄 ʀᴇꜰʀᴇꜱʜ", "refresh_userlist", ButtonStyle.PRIMARY),
            ("📊 ꜱᴛᴀᴛꜱ", "userlist_stats", ButtonStyle.PRIMARY),
            ("⬅️ ʙᴀᴄᴋ", "back_start", ButtonStyle.SUCCESS)
        ], row_width=2)
        if len(response) > 4000:
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    await message.reply(part, reply_markup=buttons)
                else:
                    await message.reply(part)
        else:
            await message.reply(response, reply_markup=buttons)
    except Exception as e:
        await message.reply(f"❌ **ᴇʀʀᴏʀ:** `{str(e)}`")

# ==================== ᴄᴜꜱᴛᴏᴍ ʙᴜᴛᴛᴏɴ ꜱᴛʏʟɪɴɢ ====================

from io import BytesIO
from pyrogram.raw.core import TLObject
from pyrogram.raw.base import KeyboardButton
from pyrogram.raw.core.primitives import Int, Bytes, String

class RawKeyboardButtonStyle(TLObject):
    ID = 0x4fdd3430
    QUALNAME = "types.KeyboardButtonStyle"
    def __init__(self, bg_primary=False, bg_danger=False, bg_success=False):
        self.bg_primary = bg_primary
        self.bg_danger = bg_danger
        self.bg_success = bg_success
    def write(self, *args):
        b = BytesIO()
        b.write(Int(self.ID, False))
        flags = 0
        if self.bg_primary: flags |= (1 << 0)
        if self.bg_danger: flags |= (1 << 1)
        if self.bg_success: flags |= (1 << 2)
        b.write(Int(flags))
        return b.getvalue()

class RawKeyboardButtonCallback(KeyboardButton, TLObject):
    ID = 0xe62bc960
    QUALNAME = "types.KeyboardButtonCallback"
    def __init__(self, text, data, requires_password, style):
        self.text = text
        self.data = data
        self.requires_password = requires_password
        self.style = style
    def write(self, *args):
        b = BytesIO()
        b.write(Int(self.ID, False))
        flags = 0
        if self.requires_password: flags |= (1 << 0)
        if self.style is not None: flags |= (1 << 10)
        b.write(Int(flags))
        if self.style is not None:
            b.write(self.style.write())
        b.write(String(self.text))
        b.write(Bytes(self.data))
        return b.getvalue()

class RawKeyboardButtonUrl(KeyboardButton, TLObject):
    ID = 0xd80c25ec
    QUALNAME = "types.KeyboardButtonUrl"
    def __init__(self, text, url, style):
        self.text = text
        self.url = url
        self.style = style
    def write(self, *args):
        b = BytesIO()
        b.write(Int(self.ID, False))
        flags = 0
        if self.style is not None: flags |= (1 << 10)
        b.write(Int(flags))
        if self.style is not None:
            b.write(self.style.write())
        b.write(String(self.text))
        b.write(String(self.url))
        return b.getvalue()

class StyledInlineKeyboardButton(InlineKeyboardButton):
    def __init__(self, text: str, callback_data: str = None, url: str = None, style: str = None, **kwargs):
        super().__init__(text=text, callback_data=callback_data, url=url, **kwargs)
        self.style = style

    async def write(self, client: "pyrogram.Client"):
        if not self.style:
            return await super().write(client)
            
        style_str = self.style
        if style_str.startswith("bg_"):
            style_str = style_str[3:]
            
        if style_str not in ["primary", "danger", "success"]:
            return await super().write(client)
            
        bg_primary = (style_str == "primary")
        bg_danger = (style_str == "danger")
        bg_success = (style_str == "success")
        style_obj = RawKeyboardButtonStyle(bg_primary=bg_primary, bg_danger=bg_danger, bg_success=bg_success)
        
        if self.callback_data is not None:
            data_bytes = bytes(self.callback_data, "utf-8") if isinstance(self.callback_data, str) else self.callback_data
            # FIXED: Use getattr with default False for requires_password
            requires_password = getattr(self, 'requires_password', False)
            return RawKeyboardButtonCallback(
                text=self.text,
                data=data_bytes,
                requires_password=requires_password,
                style=style_obj
            )
            
        if self.url is not None:
            return RawKeyboardButtonUrl(
                text=self.text,
                url=self.url,
                style=style_obj
            )
            
        return await super().write(client)

class ButtonStyle:
    PRIMARY = "bg_primary"
    SUCCESS = "bg_success"
    DANGER = "bg_danger"

def styled_button(text: str, callback_data: str = None, url: str = None, style: str = ButtonStyle.PRIMARY) -> InlineKeyboardButton:
    """ᴄʀᴇᴀᴛᴇ ᴀ ʙᴜᴛᴛᴏɴ ᴀɴᴅ ɪɴᴊᴇᴄᴛ ᴛᴇʟᴇɢʀᴀᴍ ʙᴀᴄᴋᴇɴᴅ ᴄᴏʟᴏʀ ꜱᴛʏʟᴇ"""
    return StyledInlineKeyboardButton(text=text, callback_data=callback_data, url=url, style=style)

def build_keyboard(buttons: list, row_width: int = 2) -> InlineKeyboardMarkup:
    """ʙᴜɪʟᴅ ᴋᴇʏʙᴏᴀʀᴅ ꜰʀᴏᴍ ʙᴜᴛᴛᴏɴ ᴅᴀᴛᴀ (ᴄᴏʟᴏʀ ꜱᴜᴘᴘᴏʀᴛᴇᴅ)"""
    rows, row = [], []
    
    for btn in buttons:
        if len(btn) == 4:
            text, callback, style, url = btn
            if style not in [ButtonStyle.PRIMARY, ButtonStyle.SUCCESS, ButtonStyle.DANGER]:
                style = ButtonStyle.PRIMARY
            row.append(styled_button(text, callback_data=callback, url=url, style=style))
        elif len(btn) == 3:
            text, callback, style = btn
            if style not in [ButtonStyle.PRIMARY, ButtonStyle.SUCCESS, ButtonStyle.DANGER]:
                style = ButtonStyle.PRIMARY
            row.append(styled_button(text, callback_data=callback, style=style))
        else:
            text, callback = btn[0], btn[1]
            row.append(styled_button(text, callback_data=callback, style=ButtonStyle.PRIMARY))
        
        if len(row) >= row_width:
            rows.append(row)
            row = []
    
    if row:
        rows.append(row)
    
    return InlineKeyboardMarkup(rows)

# ==================== ᴄᴀʟʟʙᴀᴄᴋ ʜᴀɴᴅʟᴇʀꜱ ====================

@bot_app.on_callback_query(~pyro_filters.regex(r"^panel_"))
async def handle_callbacks(client, callback_query: CallbackQuery):
    """ʜᴀɴᴅʟᴇ ᴀʟʟ ɴᴏɴ-ᴘᴀɴᴇʟ ᴄᴀʟʟʙᴀᴄᴋ Qᴜᴇʀɪᴇꜱ"""
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    # 🔐 ᴀᴜᴛʜᴇɴᴛɪᴄᴀᴛɪᴏɴ ᴄʜᴇᴄᴋ
    if user_id != OWNER_ID and user_id not in approved_users:
        await callback_query.answer("⛔ ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ!", show_alert=True)
        return
    
    await callback_query.answer()
    
    # ──────────────────────────────────────────────────────
    # ʀᴇꜰʀᴇꜱʜ ᴜꜱᴇʀʟɪꜱᴛ
    # ──────────────────────────────────────────────────────
    if data == "refresh_userlist":
        if not approved_users:
            keyboard = build_keyboard([
                ("➕ ᴀᴘᴘʀᴏᴠᴇ", "help_info", ButtonStyle.SUCCESS),
                ("🏠 ʜᴏᴍᴇ", "back_start", ButtonStyle.PRIMARY)
            ], row_width=2)
            await callback_query.edit_message_text(
                "📭 **ɴᴏ ᴜꜱᴇʀꜱ ᴀʀᴇ ᴀᴘᴘʀᴏᴠᴇᴅ ʏᴇᴛ.**\n\n"
                "💡 ᴜꜱᴇ `/ᴀᴘᴘʀᴏᴠᴇ` ᴛᴏ ᴀᴅᴅ ᴜꜱᴇʀꜱ",
                reply_markup=keyboard
            )
            return
        
        user_list = []
        for uid in approved_users:
            try:
                user = await client.get_users(uid)
                username = f"@{user.username}" if user.username else "ɴᴏ ᴜꜱᴇʀɴᴀᴍᴇ"
                mention = user.mention
                user_list.append(f"• {mention}\n  🔢 `{uid}` | {username}")
            except Exception:
                user_list.append(f"• ᴜꜱᴇʀ `{uid}` (⚠️ ᴄᴏᴜʟᴅ ɴᴏᴛ ꜰᴇᴛᴄʜ)")
        
        response = f"""
🔥 **ᴀᴘᴘʀᴏᴠᴇᴅ ᴜꜱᴇʀꜱ** (🔄 ʀᴇꜰʀᴇꜱʜᴇᴅ)
────────────────────
📊 **ᴛᴏᴛᴀʟ:** {len(approved_users)} ᴜꜱᴇʀꜱ
────────────────────
"""
        response += "\n\n".join(user_list)
        response += f"\n\n────────────────────\n✅ **ᴛᴏᴛᴀʟ:** {len(approved_users)}"
        
        keyboard = build_keyboard([
            ("🔄 ʀᴇꜰʀᴇꜱʜ", "refresh_userlist", ButtonStyle.PRIMARY),
            ("📊 ꜱᴛᴀᴛꜱ", "userlist_stats", ButtonStyle.PRIMARY),
            ("🏠 ʜᴏᴍᴇ", "back_start", ButtonStyle.SUCCESS)
        ], row_width=2)
        
        await callback_query.edit_message_text(response, reply_markup=keyboard)
    
    # ──────────────────────────────────────────────────────
    # ᴜꜱᴇʀʟɪꜱᴛ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ
    # ──────────────────────────────────────────────────────
    elif data == "userlist_stats":
        total = len(approved_users)
        stats_msg = f"""
📊 **ᴜꜱᴇʀ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ**
────────────────────
🔥 **ᴛᴏᴛᴀʟ:** {total}
📌 **ꜱᴛᴀᴛᴜꜱ:** {'🟢 ᴀᴄᴛɪᴠᴇ' if total > 0 else '🔴 ᴇᴍᴘᴛʏ'}
────────────────────
📈 **ᴘʀᴏɢʀᴇꜱꜱ**
{('█' * min(total, 10)) + ('░' * (10 - min(total, 10))) if total > 0 else '░░░░░░░░░░'}
⚡ **ᴜꜱᴀɢᴇ:** {'ɢᴏᴏᴅ' if total < 50 else 'ʜᴇᴀᴠʏ' if total < 100 else 'ᴍᴀx'}
"""
        keyboard = build_keyboard([
            ("⬅️ ʙᴀᴄᴋ", "back_userlist", ButtonStyle.PRIMARY)
        ], row_width=1)
        await callback_query.edit_message_text(stats_msg, reply_markup=keyboard)
    
    # ──────────────────────────────────────────────────────
    # ʙᴀᴄᴋ ᴛᴏ ᴜꜱᴇʀʟɪꜱᴛ
    # ──────────────────────────────────────────────────────
    elif data == "back_userlist":
        if not approved_users:
            keyboard = build_keyboard([
                ("➕ ᴀᴘᴘʀᴏᴠᴇ", "help_info", ButtonStyle.SUCCESS),
                ("🏠 ʜᴏᴍᴇ", "back_start", ButtonStyle.PRIMARY)
            ], row_width=2)
            await callback_query.edit_message_text(
                "📭 **ɴᴏ ᴜꜱᴇʀꜱ ᴀᴘᴘʀᴏᴠᴇᴅ**\n\n"
                "💡 ᴜꜱᴇ `/ᴀᴘᴘʀᴏᴠᴇ` ᴛᴏ ᴀᴅᴅ",
                reply_markup=keyboard
            )
            return
        
        user_list = []
        for uid in approved_users:
            try:
                user = await client.get_users(uid)
                username = f"@{user.username}" if user.username else "ɴᴏ ᴜꜱᴇʀɴᴀᴍᴇ"
                mention = user.mention
                user_list.append(f"• {mention}\n  🔢 `{uid}` | {username}")
            except Exception:
                user_list.append(f"• ᴜꜱᴇʀ `{uid}` (⚠️ ᴄᴏᴜʟᴅ ɴᴏᴛ ꜰᴇᴛᴄʜ)")
        
        response = f"""
🔥 **ᴀᴘᴘʀᴏᴠᴇᴅ ᴜꜱᴇʀꜱ**
────────────────────
📊 **ᴛᴏᴛᴀʟ:** {len(approved_users)}
────────────────────
"""
        response += "\n\n".join(user_list)
        response += f"\n\n────────────────────\n✅ **ᴛᴏᴛᴀʟ:** {len(approved_users)}"
        
        keyboard = build_keyboard([
            ("🔄 ʀᴇꜰʀᴇꜱʜ", "refresh_userlist", ButtonStyle.PRIMARY),
            ("📊 ꜱᴛᴀᴛꜱ", "userlist_stats", ButtonStyle.PRIMARY),
            ("🏠 ʜᴏᴍᴇ", "back_start", ButtonStyle.SUCCESS)
        ], row_width=2)
        
        await callback_query.edit_message_text(response, reply_markup=keyboard)
    
    # ──────────────────────────────────────────────────────
    # ʜᴇʟᴘ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ
    # ──────────────────────────────────────────────────────
    elif data == "help_info":
        help_text = """
📖 **ʜᴇʟᴘ ᴍᴇɴᴜ**
────────────────────
🎵 **ᴀᴜᴅɪᴏ ᴄᴏɴᴛʀᴏʟ**
/record - ꜱᴛᴀʀᴛ ʀᴇᴄᴏʀᴅɪɴɢ
/join <ɪᴅ> - ꜰᴏʀᴡᴀʀᴅ ᴛᴏ ᴄʜᴀᴛ 
/rejoin - ʀᴇᴄᴏɴɴᴇᴄᴛ ᴀʟʟ
/leave <ɪᴅ> - ꜱᴛᴏᴘ ꜰᴏʀᴡᴀʀᴅɪɴɢ
/leaveall - ꜱᴛᴏᴘ ᴀʟʟ
/leaverecord - ʟᴇᴀᴠᴇ ꜱᴏᴜʀᴄᴇ
────────────────────
/mute - ᴍᴜᴛᴇ
/unmute - ᴜɴᴍᴜᴛᴇ
/automute - ᴀᴜᴛᴏ ᴍᴜᴛᴇ ᴏɴ/ᴏꜰꜰ
────────────────────
🎛️ **ᴇꜰꜰᴇᴄᴛꜱ**
/level <0-200> - ᴠᴏʟᴜᴍᴇ
/bass <0-60> - ʙᴀꜱꜱ
/treble <0-60> - ᴛʀᴇʙʟᴇ
/gain <0-60> - ɢᴀɪɴ
/effects - ꜱʜᴏᴡ ᴄᴜʀʀᴇɴᴛ
/reset - ʀᴇꜱᴇᴛ ᴀʟʟ
────────────────────
📊 **ᴜᴛɪʟɪᴛʏ**
/ping - ᴄʜᴇᴄᴋ ʙᴏᴛ
/stats - ʙᴏᴛ ꜱᴛᴀᴛꜱ
/status - ꜱʏꜱᴛᴇᴍ ꜱᴛᴀᴛᴜꜱ
/list - ꜰᴏʀᴡᴀʀᴅɪɴɢ ʟɪꜱᴛ
/id - ɢᴇᴛ ᴄʜᴀᴛ ɪᴅ
/panel - ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ
/joinlink <ʟɪɴᴋ> - ᴊᴏɪɴ ᴠɪᴀ ɪɴᴠɪᴛᴇ ʟɪɴᴋ
────────────────────
👤 **ᴜꜱᴇʀ ᴍɢᴍᴛ** (ᴏᴡɴᴇʀ)
/approve - ᴀᴅᴅ ᴜꜱᴇʀ
/disapprove - ʀᴇᴍᴏᴠᴇ
/userlist - ʟɪꜱᴛ ᴜꜱᴇʀꜱ
────────────────────
/setrecordgroup - ᴄʜᴀɴɢᴇ ꜱᴏᴜʀᴄᴇ
/setsession <ꜱᴇꜱꜱɪᴏɴ> - ꜱᴇꜱꜱɪᴏɴ ᴜᴘᴅᴀᴛᴇ + ʀᴇꜱᴛᴀʀᴛ
/restart - ʀᴇꜱᴛᴀʀᴛ ʙᴏᴛ
"""
        keyboard = build_keyboard([
            ("🏠 ʜᴏᴍᴇ", "back_start", ButtonStyle.SUCCESS)
        ], row_width=1)
        await callback_query.edit_message_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    # ──────────────────────────────────────────────────────
    # ʙᴀᴄᴋ ᴛᴏ ꜱᴛᴀʀᴛ
    # ──────────────────────────────────────────────────────
    elif data == "back_start":
        user = callback_query.from_user
        first_name = escape_markdown(user.first_name or "ᴜꜱᴇʀ")
        last_name = escape_markdown(user.last_name or "")
        username = f"@{user.username}" if user.username else ""
        
        welcome_text = f"""
✨ **ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴀᴜᴅɪᴏ ꜰᴏʀᴡᴀʀᴅᴇʀ** ✨
────────────────────
👋 **ʜᴇʟʟᴏ, {first_name}!**
{last_name}
{username}
────────────────────
🎵 **ʀᴇᴀʟ-ᴛɪᴍᴇ ᴀᴜᴅɪᴏ ꜰᴏʀᴡᴀʀᴅɪɴɢ**
📊 **ꜱʏꜱᴛᴇᴍ:** ██████████ 100% ✅
⚡ **ꜰᴇᴀᴛᴜʀᴇꜱ:**
• ʀᴇᴀʟ-ᴛɪᴍᴇ ꜰᴏʀᴡᴀʀᴅɪɴɢ
• ᴀᴅᴠᴀɴᴄᴇᴅ ᴇꜰꜰᴇᴄᴛꜱ
• ᴠᴏʟᴜᴍᴇ ᴄᴏɴᴛʀᴏʟ
• ᴍᴜʟᴛɪ-ᴄʜᴀᴛ ꜰᴏʀᴡᴀʀᴅɪɴɢ
────────────────────
📌 **ᴜꜱᴇ /ʜᴇʟᴘ ꜰᴏʀ ᴄᴏᴍᴍᴀɴᴅꜱ**
"""
        keyboard = build_keyboard([
            ("👤 ᴏᴡɴᴇʀ", "owner", ButtonStyle.PRIMARY),
            ("📖 ʜᴇʟᴘ", "help_info", ButtonStyle.PRIMARY)
        ], row_width=2)
        
        try:
            photos = []
            async for photo in client.get_chat_photos(user.id, limit=1):
                photos.append(photo)
            
            if photos:
                photo = photos[0]
                await callback_query.edit_message_media(
                    media=photo.file_id,
                    caption=welcome_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
            else:
                await callback_query.edit_message_text(
                    welcome_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
        except Exception as e:
            logger.error(f"ʙᴀᴄᴋ_ꜱᴛᴀʀᴛ ᴇʀʀᴏʀ: {e}")
            if "MESSAGE_NOT_MODIFIED" not in str(e):
                try:
                    await callback_query.edit_message_text(
                        welcome_text,
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=keyboard
                    )
                except Exception:
                    pass
    
    # ──────────────────────────────────────────────────────
    # ᴏᴡɴᴇʀ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ
    # ──────────────────────────────────────────────────────
    elif data == "owner":
        keyboard = build_keyboard([
            ("🏠 ʜᴏᴍᴇ", "back_start", ButtonStyle.SUCCESS)
        ], row_width=1)
        await callback_query.edit_message_text(
            "👤 **ᴏᴡɴᴇʀ**\n\n"
            "📌 **ᴛᴇʟᴇɢʀᴀᴍ:** @Why_not_ZarKo\n"
            "🔗 [ᴘʀᴏꜰɪʟᴇ ʟɪɴᴋ](t.me/Why_not_ZarKo)\n\n"
            "💡 **ꜰᴏʀ ꜱᴜᴘᴘᴏʀᴛ ᴏʀ Qᴜᴇʀɪᴇꜱ:**\n"
            "• ᴅᴍ ᴏɴ ᴛᴇʟᴇɢʀᴀᴍ\n"
            "• ᴜꜱᴇ /ʜᴇʟᴘ ꜰᴏʀ ᴄᴏᴍᴍᴀɴᴅꜱ",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )


# ===== ꜱᴛᴀʀᴛ ᴄᴏᴍᴍᴀɴᴅ =====

@bot_app.on_message(pyro_filters.command("start"))
async def cmd_start(client, message):
    """ꜱᴛᴀʀᴛ ᴄᴏᴍᴍᴀɴᴅ ᴡɪᴛʜ ʙᴜᴛᴛᴏɴꜱ"""
    user_id = message.from_user.id if message.from_user else None
    
    # 🔐 ᴀᴜᴛʜᴇɴᴛɪᴄᴀᴛɪᴏɴ - ꜱɪʟᴇɴᴛ ɪɢɴᴏʀᴇ
    if user_id != OWNER_ID and user_id not in approved_users:
        logger.info(f"ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ /ꜱᴛᴀʀᴛ ꜰʀᴏᴍ {user_id}")
        return
    
    user = message.from_user
    first_name = escape_markdown(user.first_name or "ᴜꜱᴇʀ")
    last_name = escape_markdown(user.last_name or "")
    username = f"@{user.username}" if user.username else ""
    
    welcome_text = f"""
✨ **ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴀᴜᴅɪᴏ ꜰᴏʀᴡᴀʀᴅᴇʀ** ✨
────────────────────
👋 **ʜᴇʟʟᴏ, {first_name}!**
{last_name}
{username}
────────────────────
🎵 **ʀᴇᴀʟ-ᴛɪᴍᴇ ᴀᴜᴅɪᴏ ꜰᴏʀᴡᴀʀᴅɪɴɢ**
📊 **ꜱʏꜱᴛᴇᴍ:** ██████████ 100% ✅
⚡ **ꜰᴇᴀᴛᴜʀᴇꜱ:**
• ʀᴇᴀʟ-ᴛɪᴍᴇ ꜰᴏʀᴡᴀʀᴅɪɴɢ
• ᴀᴅᴠᴀɴᴄᴇᴅ ᴇꜰꜰᴇᴄᴛꜱ
• ᴠᴏʟᴜᴍᴇ ᴄᴏɴᴛʀᴏʟ
• ᴍᴜʟᴛɪ-ᴄʜᴀᴛ ꜰᴏʀᴡᴀʀᴅɪɴɢ
────────────────────
📌 **ᴜꜱᴇ /ʜᴇʟᴘ ꜰᴏʀ ᴄᴏᴍᴍᴀɴᴅꜱ**
"""
    
    keyboard = build_keyboard([
        ("👤 ᴏᴡɴᴇʀ", "owner", ButtonStyle.PRIMARY),
        ("📖 ʜᴇʟᴘ", "help_info", ButtonStyle.PRIMARY)
    ], row_width=2)
    
    try:
        photos = []
        async for photo in client.get_chat_photos(user.id, limit=1):
            photos.append(photo)
        
        if photos:
            photo = photos[0]
            await message.reply_photo(
                photo=photo.file_id,
                caption=welcome_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
            return
    except Exception as e:
        logger.debug(f"ᴄᴏᴜʟᴅ ɴᴏᴛ ɢᴇᴛ ᴘʀᴏꜰɪʟᴇ ᴘʜᴏᴛᴏ: {e}")
    
    await message.reply(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

# ===== ʜᴇʟᴘ ᴄᴏᴍᴍᴀɴᴅ =====

@bot_app.on_message(pyro_filters.command("help") & authorized_only())
async def cmd_help(client, message):
    """ꜱʜᴏᴡ ʜᴇʟᴘ ᴍᴇɴᴜ ᴡɪᴛʜ ʙᴜᴛᴛᴏɴꜱ"""
    help_text = """
📖 **ʜᴇʟᴘ ᴍᴇɴᴜ**
────────────────────
🎵 **ᴀᴜᴅɪᴏ ᴄᴏɴᴛʀᴏʟ**
/record - ꜱᴛᴀʀᴛ ʀᴇᴄᴏʀᴅɪɴɢ
/join <ɪᴅ> - ꜰᴏʀᴡᴀʀᴅ ᴛᴏ ᴄʜᴀᴛ
/rejoin - ʀᴇᴄᴏɴɴᴇᴄᴛ ᴀʟʟ
/leave <ɪᴅ> - ꜱᴛᴏᴘ ꜰᴏʀᴡᴀʀᴅɪɴɢ
/leaveall - ꜱᴛᴏᴘ ᴀʟʟ
/leaverecord - ʟᴇᴀᴠᴇ ꜱᴏᴜʀᴄᴇ
────────────────────
/mute - ᴍᴜᴛᴇ
/unmute - ᴜɴᴍᴜᴛᴇ
/automute - ᴀᴜᴛᴏ ᴍᴜᴛᴇ ᴏɴ/ᴏꜰꜰ
────────────────────
🎛️ **ᴇꜰꜰᴇᴄᴛꜱ**
/level <0-200> - ᴠᴏʟᴜᴍᴇ
/bass <0-60> - ʙᴀꜱꜱ
/treble <0-60> - ᴛʀᴇʙʟᴇ
/gain <0-60> - ɢᴀɪɴ
/effects - ꜱʜᴏᴡ ᴄᴜʀʀᴇɴᴛ
/reset - ʀᴇꜱᴇᴛ ᴀʟʟ
────────────────────
📊 **ᴜᴛɪʟɪᴛʏ**
/ping - ᴄʜᴇᴄᴋ ʙᴏᴛ
/stats - ʙᴏᴛ ꜱᴛᴀᴛꜱ
/status - ꜱʏꜱᴛᴇᴍ ꜱᴛᴀᴛᴜꜱ
/list - ꜰᴏʀᴡᴀʀᴅɪɴɢ ʟɪꜱᴛ
/id - ɢᴇᴛ ᴄʜᴀᴛ ɪᴅ
/panel - ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ (ʙᴜᴛᴛᴏɴꜱ)
/joinlink <ʟɪɴᴋ> - ᴊᴏɪɴ ᴠɪᴀ ɪɴᴠɪᴛᴇ ʟɪɴᴋ
────────────────────
👤 **ᴜꜱᴇʀ ᴍɢᴍᴛ** (ᴏᴡɴᴇʀ)
/approve - ᴀᴅᴅ ᴜꜱᴇʀ
/disapprove - ʀᴇᴍᴏᴠᴇ
/userlist - ʟɪꜱᴛ ᴜꜱᴇʀꜱ
────────────────────
/setrecordgroup <ɪᴅ> - ᴄʜᴀɴɢᴇ ꜱᴏᴜʀᴄᴇ
/setsession <ꜱᴇꜱꜱɪᴏɴ> - ꜱᴇꜱꜱɪᴏɴ ᴜᴘᴅᴀᴛᴇ + ʀᴇꜱᴛᴀʀᴛ
/restart - ʀᴇꜱᴛᴀʀᴛ ʙᴏᴛ
"""
    keyboard = build_keyboard([
        ("🏠 ʜᴏᴍᴇ", "back_start", ButtonStyle.SUCCESS),
        ("👤 ᴏᴡɴᴇʀ", "owner", ButtonStyle.PRIMARY)
    ], row_width=2)
    
    await message.reply(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

# ===== ᴜᴛɪʟɪᴛʏ Coᴍᴍᴀɴᴅꜱ =====

@bot_app.on_message(pyro_filters.command("id") & pyro_filters.user(OWNER_ID))
async def cmd_id(client, message):
    """ɢᴇᴛ ᴄʜᴀᴛ ɪᴅ"""
    chat_type = "ɢʀᴏᴜᴘ" if message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP) else "ᴘʀɪᴠᴀᴛᴇ"
    id_msg = f"""
📱 **ᴄʜᴀᴛ ɪɴꜰᴏʀᴍᴀᴛɪᴏɴ**

────────────────────
🔢 **ᴄʜᴀᴛ ɪᴅ:** `{message.chat.id}`
📌 **ᴛʏᴘᴇ:** {chat_type}
📝 **ᴛɪᴛʟᴇ:** {message.chat.title or 'ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ'}
───────────────────

✅ **ᴄᴏᴘʏ ᴛʜɪꜱ ɪᴅ ꜰᴏʀ ᴜꜱᴇ ɪɴ ᴄᴏᴍᴍᴀɴᴅꜱ**
"""
    await message.reply(id_msg)

@bot_app.on_message(pyro_filters.command("ping") & authorized_only())
async def cmd_ping(client, message):
    """ᴄʜᴇᴄᴋ ʙᴏᴛ ᴘɪɴɢ"""
    start = time.time()
    msg = await message.reply("🏓 ᴘɪɴɢ...")
    end = time.time()
    ping = round((end - start) * 1000)
    await msg.edit_text(
        f"🏓 **ᴘᴏɴɢ!**\n\n"
        f"📡 **ᴘɪɴɢ:** `{ping}ᴍꜱ`\n"
        f"⏱️ **ᴜᴘᴛɪᴍᴇ:** `{get_uptime()}`"
    )

@bot_app.on_message(pyro_filters.command("stats") & pyro_filters.user(OWNER_ID))
async def cmd_stats(client, message):
    """ꜱʜᴏᴡ ʙᴏᴛ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ"""
    stats_msg = f"""
📊 **ʙᴏᴛ ꜱᴛᴀᴛɪꜱᴛɪᴄꜱ**

────────────────────
⏱️ **ᴜᴘᴛɪᴍᴇ:** `{get_uptime()}`
👥 **ᴀᴘᴘʀᴏᴠᴇᴅ ᴜꜱᴇʀꜱ:** {len(approved_users)}
📤 **ᴀᴄᴛɪᴠᴇ ꜰᴏʀᴡᴀʀᴅꜱ:** {len(forward_chats)}
📡 **ꜱᴏᴜʀᴄᴇ:** `{RECORD_SOURCE}`
🔊 **ᴀᴜᴅɪᴏ:** {'🔇 ᴍᴜᴛᴇᴅ' if is_muted else '🔊 ʟɪᴠᴇ'}
🎵 **ʀᴇᴄᴏʀᴅɪɴɢ:** {'🟢 ᴏɴ' if is_recording else '🔴 ᴏꜰꜰ'}
────────────────────

🎛️ **ᴀᴄᴛɪᴠᴇ ᴇꜰꜰᴇᴄᴛꜱ**
• ᴠᴏʟᴜᴍᴇ: `{audio_config['volume']}%`
• ʙᴀꜱꜱ: `{audio_config['bass']}`
• ᴛʀᴇʙʟᴇ: `{audio_config['treble']}`
• ɢᴀɪɴ: `{audio_config['gain']}`
"""
    await message.reply(stats_msg)

# ===== ᴀᴜᴅɪᴏ ᴄᴏɴᴛʀᴏʟ ᴄᴏᴍᴍᴀɴᴅꜱ =====

@bot_app.on_message(pyro_filters.command("record") & authorized_only())
async def cmd_record(client, message):
    """ꜱᴛᴀʀᴛ ʀᴇᴄᴏʀᴅɪɴɢ ꜰʀᴏᴍ ꜱᴏᴜʀᴄᴇ ɢʀᴏᴜᴘ (ᴠᴄ-ᴄᴜᴛ ꜱᴀꜰᴇ)"""
    global is_recording

    # Agar already recording hai to bhi SOFT rejoin maaro (VC cut ho sakti hai)
    if is_recording:
        status_msg = await message.reply(
            f"🔄 **ᴀʟʀᴇᴀᴅʏ ʀᴇᴄᴏʀᴅɪɴɢ — ꜱᴏꜰᴛ ʀᴇᴊᴏɪɴ ᴀᴛᴛᴇᴍᴘᴛ...**\n\n"
            f"📡 **ꜱᴏᴜʀᴄᴇ:** `{RECORD_SOURCE}`\n"
            f"📤 **ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {len(forward_chats)} ᴄʜᴀᴛꜱ"
        )
        success, error = await join_call_safe(RECORD_SOURCE)
        if success:
            try:
                await call_py.record(RECORD_SOURCE, RecordStream(True, AUDIO_PARAMETERS))
                is_recording = True
                await status_msg.edit_text(
                    f"✅ **ʀᴇᴄᴏʀᴅɪɴɢ ʀᴇꜱᴛᴏʀᴇᴅ!**\n\n"
                    f"────────────────────\n"
                    f"📡 **ꜱᴏᴜʀᴄᴇ:** `{RECORD_SOURCE}`\n"
                    f"📤 **ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {len(forward_chats)} ᴄʜᴀᴛꜱ\n"
                    f"📊 **ꜱᴛᴀᴛᴜꜱ:** 🟢 ʟɪᴠᴇ\n"
                    f"────────────────────"
                )
                logger.info("ʀᴇᴄᴏʀᴅɪɴɢ ꜱᴏꜰᴛ-ʀᴇᴊᴏɪɴᴇᴅ")
            except Exception as e:
                is_recording = False
                await status_msg.edit_text(
                    f"❌ **ʀᴇᴄᴏʀᴅ ꜰᴀɪʟᴇᴅ!**\n\n⚠️ `{str(e)[:200]}`"
                )
        else:
            is_recording = False
            await status_msg.edit_text(
                f"❌ **ʀᴇᴄᴏʀᴅ ꜰᴀɪʟᴇᴅ!**\n\n"
                f"⚠️ **ᴇʀʀᴏʀ:** `{error}`\n\n"
                f"💡 ᴍᴀᴋᴇ ꜱᴜʀᴇ ᴠᴄ ɪꜱ ᴀᴄᴛɪᴠᴇ ɪɴ ꜱᴏᴜʀᴄᴇ ɢʀᴏᴜᴘ"
            )
        return

    # Fresh start
    try:
        status_msg = await message.reply(
            "🔄 **ꜱᴛᴀʀᴛɪɴɢ ʀᴇᴄᴏʀᴅɪɴɢ...**\n\n"
            "📡 ᴄᴏɴɴᴇᴄᴛɪɴɢ ᴛᴏ ꜱᴏᴜʀᴄᴇ..."
        )
        success, error = await join_call_safe(RECORD_SOURCE)
        if success:
            await call_py.record(RECORD_SOURCE, RecordStream(True, AUDIO_PARAMETERS))
            is_recording = True
            record_msg = f"""
✅ **ꜱᴛᴀʀᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!**

────────────────────
📡 **ꜱᴏᴜʀᴄᴇ:** `{RECORD_SOURCE}`
📤 **ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {len(forward_chats)} ᴄʜᴀᴛꜱ
📊 **ꜱᴛᴀᴛᴜꜱ:** 🟢 ʟɪᴠᴇ
────────────────────

🎵 **ᴀᴜᴅɪᴏ ɪꜱ ɴᴏᴡ ꜰʟᴏᴡɪɴɢ!**
"""
            await status_msg.edit_text(record_msg)
            logger.info("ʀᴇᴄᴏʀᴅɪɴɢ ꜱᴛᴀʀᴛᴇᴅ")
        else:
            is_recording = False
            await status_msg.edit_text(
                f"❌ **ꜰᴀɪʟᴇᴅ ᴛᴏ ꜱᴛᴀʀᴛ ʀᴇᴄᴏʀᴅɪɴɢ!**\n\n"
                f"⚠️ **ᴇʀʀᴏʀ:** `{error}`\n\n"
                f"💡 ᴍᴀᴋᴇ ꜱᴜʀᴇ ᴠᴄ ɪꜱ ᴀᴄᴛɪᴠᴇ ɪɴ ꜱᴏᴜʀᴄᴇ ɢʀᴏᴜᴘ"
            )
    except Exception as e:
        is_recording = False
        await message.reply(f"❌ **ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!**\n\n⚠️ `{str(e)}`")

@bot_app.on_message(pyro_filters.command("join") & authorized_only())
async def cmd_join(client, message):
    """ꜰᴏʀᴡᴀʀᴅ ᴀᴜᴅɪᴏ ᴛᴏ ᴀ ᴄʜᴀᴛ (ᴠᴄ-ᴄᴜᴛ ꜱᴀꜰᴇ — ᴀʟᴡᴀʏꜱ ꜱᴏꜰᴛ ʀᴇᴊᴏɪɴ)"""
    global is_muted
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ **ᴜꜱᴀɢᴇ:** `/join <ᴄʜᴀᴛ_ɪᴅ>`")
        return

    chat_id_str = re.sub(r'[^\d-]', '', parts[1])
    try:
        chat_id = int(chat_id_str)

        if chat_id == RECORD_SOURCE:
            await message.reply(
                "⚠️ **ᴄᴀɴɴᴏᴛ ꜰᴏʀᴡᴀʀᴅ ᴛᴏ ꜱᴏᴜʀᴄᴇ ᴄʜᴀᴛ!**\n\n"
                f"📡 **ꜱᴏᴜʀᴄᴇ:** `{RECORD_SOURCE}`\n"
                "💡 ᴜꜱᴇ ᴀ ᴅɪꜰꜰᴇʀᴇɴᴛ ᴄʜᴀᴛ ꜰᴏʀ ꜰᴏʀᴡᴀʀᴅɪɴɢ"
            )
            return

        # ===== CASE 1: Already in list → SOFT REJOIN (VC cut ho sakti hai) =====
        if chat_id in forward_chats:
            status_msg = await message.reply(
                f"🔄 **ᴀʟʀᴇᴀᴅʏ ɪɴ ʟɪꜱᴛ — ꜱᴏꜰᴛ ʀᴇᴊᴏɪɴ ᴀᴛᴛᴇᴍᴘᴛ...**\n\n"
                f"🎯 `{chat_id}`\n"
                f"📡 ᴄʟᴇᴀɴɪɴɢ ꜱᴛᴀʟᴇ ꜱᴛᴀᴛᴇ & ʀᴇᴊᴏɪɴɪɴɢ..."
            )
            success, error = await join_call_safe(chat_id)
            if success:
                # restore mute state for this chat if globally muted
                if is_muted or auto_mute_enabled:
                    try:
                        await call_py.mute(chat_id)
                    except Exception:
                        pass
                await status_msg.edit_text(
                    f"✅ **ʀᴇᴊᴏɪɴ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟ!**\n\n"
                    f"────────────────────\n"
                    f"🎯 **ᴄʜᴀᴛ:** `{chat_id}`\n"
                    f"📤 **ᴛᴏᴛᴀʟ:** {len(forward_chats)} ᴄʜᴀᴛꜱ\n"
                    f"📊 **ꜱᴛᴀᴛᴜꜱ:** 🟢 ʟɪᴠᴇ\n"
                    f"────────────────────\n\n"
                    f"💡 ᴠᴄ ᴄᴜᴛ ᴛʜɪ ᴛᴏ ᴀʙ ɪɴꜱᴛᴀɴᴛ ʀᴇᴊᴏɪɴ ʜᴏ ɢᴀʏᴀ!"
                )
                logger.info(f"ꜱᴏꜰᴛ ʀᴇᴊᴏɪɴ ꜱᴜᴄᴄᴇꜱꜱ: {chat_id}")
            else:
                await status_msg.edit_text(
                    f"❌ **ʀᴇᴊᴏɪɴ ꜰᴀɪʟᴇᴅ!**\n\n"
                    f"🎯 **ᴄʜᴀᴛ:** `{chat_id}`\n"
                    f"⚠️ **ᴇʀʀᴏʀ:** `{error}`\n\n"
                    f"💡 ᴛʀʏ:\n"
                    f"• `/ʟᴇᴀᴠᴇ {chat_id}` ᴛʜᴇɴ `/ᴊᴏɪɴ {chat_id}`\n"
                    f"• ᴇɴꜱᴜʀᴇ ᴠᴄ ɪꜱ ᴀᴄᴛɪᴠᴇ ɪɴ ᴛʜᴀᴛ ɢʀᴏᴜᴘ"
                )
                logger.error(f"ꜱᴏꜰᴛ ʀᴇᴊᴏɪɴ ꜰᴀɪʟᴇᴅ {chat_id}: {error}")
            return

        # ===== CASE 2: Fresh join =====
        status_msg = await message.reply(
            f"🔄 **ᴄᴏɴɴᴇᴄᴛɪɴɢ ᴛᴏ `{chat_id}`...**\n\n"
            "📡 ᴇꜱᴛᴀʙʟɪꜱʜɪɴɢ ᴀᴜᴅɪᴏ ꜰᴏʀᴡᴀʀᴅɪɴɢ..."
        )
        success, error = await join_call_safe(chat_id)
        if success:
            forward_chats.add(chat_id)

            if auto_mute_enabled:
                try:
                    await call_py.mute(chat_id)
                except Exception as e:
                    logger.debug(f"ᴀᴜᴛᴏ-ᴍᴜᴛᴇ ꜰᴀɪʟᴇᴅ ꜰᴏʀ {chat_id}: {e}")

            save_state()
            join_msg = f"""
✅ **ꜰᴏʀᴡᴀʀᴅɪɴɢ ꜱᴛᴀʀᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!**

────────────────────
🎯 **ᴛᴀʀɢᴇᴛ:** `{chat_id}`
📤 **ᴛᴏᴛᴀʟ ᴅᴇꜱᴛɪɴᴀᴛɪᴏɴꜱ:** {len(forward_chats)}
📊 **ꜱᴛᴀᴛᴜꜱ:** 🟢 ᴄᴏɴɴᴇᴄᴛᴇᴅ
────────────────────

🎵 **ᴀᴜᴅɪᴏ ɪꜱ ɴᴏᴡ ꜰᴏʀᴡᴀʀᴅɪɴɢ ᴛᴏ ᴛʜɪꜱ ᴄʜᴀᴛ!**
"""
            await status_msg.edit_text(join_msg)
            logger.info(f"ᴊᴏɪɴᴇᴅ {chat_id}")
        else:
            await status_msg.edit_text(
                f"❌ **ꜰᴀɪʟᴇᴅ ᴛᴏ ᴊᴏɪɴ ᴄʜᴀᴛ!**\n\n"
                f"⚠️ **ᴇʀʀᴏʀ:** `{error}`\n\n"
                f"💡 **ᴛʀᴏᴜʙʟᴇꜱʜᴏᴏᴛɪɴɢ:**\n"
                f"• ᴇɴꜱᴜʀᴇ ᴠᴄ ɪꜱ ᴀᴄᴛɪᴠᴇ\n"
                f"• ᴄʜᴇᴄᴋ ɪꜰ ᴜꜱᴇʀ ᴀᴄᴄᴏᴜɴᴛ ɪꜱ ᴀᴅᴍɪɴ\n"
                f"• ᴠᴇʀɪꜰʏ ᴄʜᴀᴛ ɪᴅ ɪꜱ ᴄᴏʀʀᴇᴄᴛ"
            )
    except ValueError:
        await message.reply(
            f"❌ **ɪɴᴠᴀʟɪᴅ ᴄʜᴀᴛ ɪᴅ ꜰᴏʀᴍᴀᴛ!**\n\n"
            f"📌 **ʏᴏᴜ ᴇɴᴛᴇʀᴇᴅ:** `{parts[1]}`\n"
            f"💡 ᴜꜱᴇ ᴀ ɴᴜᴍᴇʀɪᴄ ɪᴅ (ᴇ.ɢ., `-1003929100976`)"
        )
    except Exception as e:
        await message.reply(f"❌ **ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!**\n\n⚠️ `{str(e)}`")

# ===== ʀᴇᴊᴏɪɴ ᴄᴏᴍᴍᴀɴᴅ =====

@bot_app.on_message(pyro_filters.command("rejoin") & authorized_only())
async def cmd_rejoin(client, message):
    """ʟᴇᴀᴠᴇ ᴀɴᴅ ᴊᴏɪɴ ᴀʟʟ ᴄʜᴀᴛꜱ ᴀɢᴀɪɴ (ᴠᴄ-ᴄᴜᴛ ꜱᴀꜰᴇ)"""
    global is_recording, is_muted

    status_msg = await message.reply(
        "🔄 **ʀᴇᴊᴏɪɴɪɴɢ ᴀʟʟ ᴄʜᴀᴛꜱ...**\n\n"
        "📡 ᴅɪꜱᴄᴏɴɴᴇᴄᴛɪɴɢ ᴀɴᴅ ʀᴇᴄᴏɴɴᴇᴄᴛɪɴɢ ᴀʟʟ ᴄᴏɴɴᴇᴄᴛɪᴏɴꜱ..."
    )

    rejoin_results = {
        "source": {"status": "❌", "error": None},
        "forwards": {"total": 0, "success": 0, "failed": 0, "errors": []}
    }

    was_muted = is_muted
    was_recording = is_recording
    source_chat = RECORD_SOURCE

    # ===== 1. Rejoin source =====
    if was_recording:
        try:
            await call_py.leave_call(source_chat)
            await asyncio.sleep(0.8)
        except Exception as e:
            logger.debug(f"ᴄᴏᴜʟᴅ ɴᴏᴛ ʟᴇᴀᴠᴇ ꜱᴏᴜʀᴄᴇ: {e}")

        # join_call_safe already cleans up, so this is safe even if leave failed
        success, error = await join_call_safe(source_chat)
        if success:
            try:
                await call_py.record(source_chat, RecordStream(True, AUDIO_PARAMETERS))
                is_recording = True
                rejoin_results["source"]["status"] = "✅"
                logger.info(f"ʀᴇᴊᴏɪɴᴇᴅ ꜱᴏᴜʀᴄᴇ {source_chat}")
            except Exception as e:
                is_recording = False
                rejoin_results["source"]["status"] = "❌"
                rejoin_results["source"]["error"] = str(e)
        else:
            is_recording = False
            rejoin_results["source"]["status"] = "❌"
            rejoin_results["source"]["error"] = error
    else:
        rejoin_results["source"]["status"] = "⏸️"
        rejoin_results["source"]["error"] = "ɴᴏᴛ ʀᴇᴄᴏʀᴅɪɴɢ"

    # ===== 2. Rejoin forward chats =====
    forward_list = list(forward_chats)
    rejoin_results["forwards"]["total"] = len(forward_list)

    if forward_list:
        for chat_id in forward_list:
            try:
                await call_py.leave_call(chat_id)
            except Exception:
                pass

        await asyncio.sleep(1.0)

        for chat_id in forward_list:
            try:
                success, error = await join_call_safe(chat_id)
                if success:
                    rejoin_results["forwards"]["success"] += 1
                    logger.info(f"ʀᴇᴊᴏɪɴᴇᴅ {chat_id}")
                else:
                    rejoin_results["forwards"]["failed"] += 1
                    rejoin_results["forwards"]["errors"].append(f"`{chat_id}`: {error[:50]}")
                    forward_chats.discard(chat_id)
            except Exception as e:
                rejoin_results["forwards"]["failed"] += 1
                rejoin_results["forwards"]["errors"].append(f"`{chat_id}`: {str(e)[:50]}")
                forward_chats.discard(chat_id)

    # ===== 3. Restore mute state =====
    if was_muted and forward_chats:
        paused = 0
        for chat_id in list(forward_chats):
            try:
                await call_py.mute(chat_id)
                paused += 1
            except Exception:
                pass
        is_muted = paused > 0
    elif forward_chats:
        resumed = 0
        for chat_id in list(forward_chats):
            try:
                await call_py.unmute(chat_id)
                resumed += 1
            except Exception:
                pass
        is_muted = False
    else:
        is_muted = False

    save_state()

    response = f"""
🔄 **ʀᴇᴊᴏɪɴ ᴄᴏᴍᴘʟᴇᴛᴇ!**

────────────────────
📡 **ꜱᴏᴜʀᴄᴇ ɢʀᴏᴜᴘ:** `{source_chat}`
{'✅ ʀᴇᴄᴏɴɴᴇᴄᴛᴇᴅ' if rejoin_results['source']['status'] == '✅' else '❌ ꜰᴀɪʟᴇᴅ' if rejoin_results['source']['status'] == '❌' else '⏸️ ɴᴏᴛ ᴀᴄᴛɪᴠᴇ'}
"""
    if rejoin_results['source']['error']:
        response += f"⚠️ **ᴇʀʀᴏʀ:** `{rejoin_results['source']['error']}`\n"

    response += f"""
────────────────────
📤 **ꜰᴏʀᴡᴀʀᴅ ꜱᴛᴀᴛᴜꜱ:**
• **ᴛᴏᴛᴀʟ:** {rejoin_results['forwards']['total']}
• **✅ ꜱᴜᴄᴄᴇꜱꜱ:** {rejoin_results['forwards']['success']}
• **❌ ꜰᴀɪʟᴇᴅ:** {rejoin_results['forwards']['failed']}
"""
    if rejoin_results['forwards']['errors']:
        response += "\n⚠️ **ꜰᴀɪʟᴇᴅ ᴄʜᴀᴛꜱ:**\n"
        for err in rejoin_results['forwards']['errors'][:5]:
            response += f"• {err}\n"
        if len(rejoin_results['forwards']['errors']) > 5:
            response += f"• ... ᴀɴᴅ {len(rejoin_results['forwards']['errors'])-5} ᴍᴏʀᴇ\n"

    response += f"""
────────────────────
📊 **ꜰɪɴᴀʟ ꜱᴛᴀᴛᴜꜱ:**
• **ʀᴇᴄᴏʀᴅɪɴɢ:** {'🟢 ᴀᴄᴛɪᴠᴇ' if is_recording else '🔴 ɪɴᴀᴄᴛɪᴠᴇ'}
• **ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {len(forward_chats)} ᴄʜᴀᴛꜱ
• **ᴀᴜᴅɪᴏ:** {'🔇 ᴍᴜᴛᴇᴅ' if is_muted else '🔊 ʟɪᴠᴇ'}
────────────────────

💡 **ɴᴏᴛᴇ:** ꜰᴀɪʟᴇᴅ ᴄʜᴀᴛꜱ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ʀᴇᴍᴏᴠᴇᴅ
"""
    await status_msg.edit_text(response)
    logger.info(
        f"ʀᴇᴊᴏɪɴ ᴅᴏɴᴇ: ꜱᴏᴜʀᴄᴇ={rejoin_results['source']['status']}, "
        f"ꜰᴏʀᴡᴀʀᴅꜱ={rejoin_results['forwards']['success']}/{rejoin_results['forwards']['total']}, "
        f"ᴍᴜᴛᴇ={is_muted}"
    )
# ===== ʟᴇᴀᴠᴇ ᴄᴏᴍᴍᴀɴᴅꜱ =====

@bot_app.on_message(pyro_filters.command("leaverecord") & authorized_only())
async def cmd_leaverecord(client, message):
    """ʟᴇᴀᴠᴇ ᴛʜᴇ ꜱᴏᴜʀᴄᴇ ʀᴇᴄᴏʀᴅɪɴɢ ɢʀᴏᴜᴘ"""
    global is_recording
    try:
        status_msg = await message.reply("🔄 **ʟᴇᴀᴠɪɴɢ ꜱᴏᴜʀᴄᴇ ɢʀᴏᴜᴘ...**")
        await call_py.leave_call(RECORD_SOURCE)
        is_recording = False
        leave_msg = f"""
✅ **ʟᴇꜰᴛ ꜱᴏᴜʀᴄᴇ ɢʀᴏᴜᴘ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!**

────────────────────
📡 **ꜱᴏᴜʀᴄᴇ:** `{RECORD_SOURCE}`
📊 **ꜱᴛᴀᴛᴜꜱ:** 🔴 ᴅɪꜱᴄᴏɴɴᴇᴄᴛᴇᴅ
📤 **ᴀᴄᴛɪᴠᴇ ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {len(forward_chats)}
────────────────────

🎵 **ʀᴇᴄᴏʀᴅɪɴɢ ʜᴀꜱ ʙᴇᴇɴ ꜱᴛᴏᴘᴘᴇᴅ!**
"""
        await status_msg.edit_text(leave_msg)
        logger.info("ʟᴇꜰᴛ ʀᴇᴄᴏʀᴅ ɢʀᴏᴜᴘ")
    except Exception as e:
        await message.reply(f"❌ **ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!**\n\n⚠️ `{str(e)}`")

@bot_app.on_message(pyro_filters.command("leave") & authorized_only())
async def cmd_leave(client, message):
    """ʟᴇᴀᴠᴇ ᴀ ꜱᴘᴇᴄɪꜰɪᴄ ᴄʜᴀᴛ ᴏʀ ᴀʟʟ ᴄʜᴀᴛꜱ"""
    parts = message.text.split()
    if len(parts) >= 2:
        chat_id_str = re.sub(r'[^\d-]', '', parts[1])
        try:
            chat_id = int(chat_id_str)
        except ValueError:
            await message.reply(
                f"❌ **ɪɴᴠᴀʟɪᴅ ᴄʜᴀᴛ ɪᴅ!**\n\n"
                f"📌 **ʏᴏᴜ ᴇɴᴛᴇʀᴇᴅ:** `{parts[1]}`\n"
                f"💡 ᴜꜱᴇ ᴀ ɴuᴍᴇʀɪᴄ ɪᴅ (ᴇ.ɢ., `-1003929100976`)"
            )
            return
        if chat_id not in forward_chats:
            await message.reply(
                f"⚠️ **ɴᴏᴛ ꜰᴏʀᴡᴀʀᴅɪɴɢ ᴛᴏ ᴛʜɪꜱ ᴄʜᴀᴛ!**\n\n🎯 `{chat_id}`"
            )
            return
        try:
            status_msg = await message.reply(f"🔄 **ʟᴇᴀᴠɪɴɢ `{chat_id}`...**")
            await call_py.leave_call(chat_id)
            forward_chats.discard(chat_id)
            save_state()
            leave_msg = f"""
✅ **ʟᴇꜰᴛ ᴄʜᴀᴛ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!**

────────────────────
🎯 **ᴄʜᴀᴛ:** `{chat_id}`
📤 **ʀᴇᴍᴀɪɴɪɴɢ ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {len(forward_chats)}
📊 **ꜱᴛᴀᴛᴜꜱ:** 🔴 ᴅɪꜱᴄᴏɴɴᴇᴄᴛᴇᴅ
────────────────────

📌 **ᴀᴜᴅɪᴏ ɴᴏ ʟᴏɴɢᴇʀ ꜰʟᴏᴡꜱ ᴛᴏ ᴛʜɪꜱ ᴄʜᴀᴛ!**
"""
            await status_msg.edit_text(leave_msg)
            logger.info(f"ʟᴇꜰᴛ ᴄʜᴀᴛ {chat_id}")
        except Exception as e:
            logger.error(f"ᴄᴍᴅ_ʟᴇᴀᴠᴇ ᴇʀʀᴏʀ ꜰᴏʀ {chat_id}: {e}")
            await message.reply(f"❌ **ᴇʀʀᴏʀ ʟᴇᴀᴠɪɴɢ ᴄʜᴀᴛ!**\n\n⚠️ `{str(e)}`")
    else:
        if not forward_chats:
            await message.reply(
                "📭 **ɴᴏ ᴄʜᴀᴛꜱ ᴛᴏ ʟᴇᴀᴠᴇ!**\n\n💡 ᴜꜱᴇ `/ᴊᴏɪɴ` ᴛᴏ ꜱᴛᴀʀᴛ ꜰᴏʀᴡᴀʀᴅɪɴɢ"
            )
            return
        count = len(forward_chats)
        status_msg = await message.reply(f"🔄 **ʟᴇᴀᴠɪɴɢ ᴀʟʟ {count} ᴄʜᴀᴛꜱ...**")
        left_count = 0
        for cid in list(forward_chats):
            try:
                await call_py.leave_call(cid)
                left_count += 1
            except Exception:
                pass
        forward_chats.clear()
        save_state()
        leave_msg = f"""
✅ **ʟᴇꜰᴛ ᴀʟʟ ᴄʜᴀᴛꜱ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!**

────────────────────
📤 **ᴛᴏᴛᴀʟ ʟᴇꜰᴛ:** {left_count}/{count} ᴄʜᴀᴛꜱ
📊 **ꜱᴛᴀᴛᴜꜱ:** 🔴 ᴀʟʟ ᴅɪꜱᴄᴏɴɴᴇᴄᴛᴇᴅ
📡 **ꜱᴏᴜʀᴄᴇ:** {'🟢 ᴀᴄᴛɪᴠᴇ' if is_recording else '🔴 ɪɴᴀᴄᴛɪᴠᴇ'}
────────────────────

🎵 **ᴀʟʟ ᴀᴜᴅɪᴏ ꜰᴏʀᴡᴀʀᴅɪɴɢ ʜᴀꜱ ꜱᴛᴏᴘᴘᴇᴅ!**
"""
        await status_msg.edit_text(leave_msg)

@bot_app.on_message(pyro_filters.command("leaveall") & authorized_only())
async def cmd_leaveall(client, message):
    """ʟᴇᴀᴠᴇ ᴀʟʟ ᴄʜᴀᴛꜱ ɪɴᴄʟᴜᴅɪɴɢ ꜱᴏᴜʀᴄᴇ"""
    global is_recording
    total_forward = len(forward_chats)
    status_msg = await message.reply(
        "🔄 **ᴅɪꜱᴄᴏɴɴᴇᴄᴛɪɴɢ ᴀʟʟ ᴄʜᴀᴛꜱ...**\n\n📡 ᴄʟᴇᴀɴɪɴɢ ᴜᴘ ᴀʟʟ ᴄᴏɴɴᴇᴄᴛɪᴏɴꜱ..."
    )
    try:
        await call_py.leave_call(RECORD_SOURCE)
        is_recording = False
    except Exception:
        pass
    left_count = 0
    for cid in list(forward_chats):
        try:
            await call_py.leave_call(cid)
            left_count += 1
        except Exception:
            pass
    forward_chats.clear()
    save_state()
    leaveall_msg = f"""
✅ **ᴀʟʟ ᴄʜᴀᴛꜱ ᴅɪꜱᴄᴏɴɴᴇᴄᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!**

────────────────────
📡 **ꜱᴏᴜʀᴄᴇ:** ✅ ʟᴇꜰᴛ
📤 **ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {left_count}/{total_forward} ʟᴇꜰᴛ
📊 **ꜱᴛᴀᴛᴜꜱ:** 🔴 ᴀʟʟ ᴅɪꜱᴄᴏɴɴᴇᴄᴛᴇᴅ
────────────────────

🎵 **ᴇᴠᴇʀʏᴛʜɪɴɢ ʜᴀꜱ ʙᴇᴇɴ ᴄʟᴇᴀɴᴇᴅ ᴜᴘ!**
"""
    await status_msg.edit_text(leaveall_msg)
    logger.info("ʟᴇꜰᴛ ᴀʟʟ ᴄʜᴀᴛꜱ")

# ===== JOINLINK COMMAND - JOIN ONLY (NO AUTO-FORWARD) =====

@bot_app.on_message(pyro_filters.command("joinlink") & authorized_only())
async def cmd_joinlink(client, message):
    """
    ᴊᴏɪɴ ᴀ ᴘʀɪᴠᴀᴛᴇ ɢʀᴏᴜᴘ/ᴄʜᴀɴɴᴇʟ ᴠɪᴀ ɪɴᴠɪᴛᴇ ʟɪɴᴋ
    ᴏɴʟʏ ᴊᴏɪɴꜱ - ᴅᴏᴇꜱ ɴᴏᴛ ꜱᴛᴀʀᴛ ꜰᴏʀᴡᴀʀᴅɪɴɢ
    """
    parts = message.text.split()
    
    if len(parts) < 2:
        help_text = """
❌ **ᴜꜱᴀɢᴇ:** `/joinlink <ɪɴᴠɪᴛᴇ_ʟɪɴᴋ>`

────────────────────
📌 **ᴇxᴀᴍᴘʟᴇꜱ:**
`/joinlink https://t.me/joinchat/ABC123xyz`
`/joinlink https://t.me/+ABC123xyz`

🔗 **ꜱᴜᴘᴘᴏʀᴛᴇᴅ ʟɪɴᴋ ꜰᴏʀᴍᴀᴛꜱ:**
• `https://t.me/joinchat/...`
• `https://t.me/+...`
• `t.me/joinchat/...`
• `t.me/+...`

📋 **ʟɪɴᴋ ᴛʏᴘᴇꜱ:**
• **ᴅɪʀᴇᴄᴛ** - ɪɴꜱᴛᴀɴᴛ ᴊᴏɪɴ (ɴᴏ ᴀᴘᴘʀᴏᴠᴀʟ ɴᴇᴇᴅᴇᴅ)
• **ʀᴇQᴜᴇꜱᴛ** - ꜱᴇɴᴅꜱ ᴊᴏɪɴ ʀᴇQᴜᴇꜱᴛ (ᴀᴡᴀɪᴛꜱ ᴀᴅᴍɪɴ ᴀᴘᴘʀᴏᴠᴀʟ)

────────────────────
⚠️ **ɴᴏᴛᴇ:**
• ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ᴏɴʟʏ ᴊᴏɪɴꜱ ᴛʜᴇ ɢʀᴏᴜᴘ/ᴄʜᴀɴɴᴇʟ
• ᴜꜱᴇ `/ᴊᴏɪɴ <ɪᴅ>` ꜱᴇᴘᴀʀᴀᴛᴇʟʏ ᴛᴏ ꜱᴛᴀʀᴛ ꜰᴏʀᴡᴀʀᴅɪɴɢ
• ᴛʜᴇ ʙᴏᴛ ᴜꜱᴇʀ ᴀᴄᴄᴏᴜɴᴛ ᴍᴜꜱᴛ ʜᴀᴠᴇ ᴀᴄᴄᴇꜱꜱ
"""
        await message.reply(help_text)
        return
    
    invite_link = parts[1].strip()
    invite_link = re.sub(r'[<>]', '', invite_link)
    
    # Validate link format
    if not any(pattern in invite_link for pattern in ['t.me/joinchat', 't.me/+', 'telegram.me/joinchat', 'telegram.me/+']):
        await message.reply(
            f"❌ **ɪɴᴠᴀʟɪᴅ ɪɴᴠɪᴛᴇ ʟɪɴᴋ ꜰᴏʀᴍᴀᴛ!**\n\n"
            f"📌 **ʏᴏᴜ ᴇɴᴛᴇʀᴇᴅ:** `{invite_link}`\n\n"
            f"💡 **ᴇxᴘᴇᴄᴛᴇᴅ ꜰᴏʀᴍᴀᴛ:**\n"
            f"• `https://t.me/joinchat/...`\n"
            f"• `https://t.me/+...`"
        )
        return
    
    status_msg = await message.reply(
        f"🔄 **ᴘʀᴏᴄᴇꜱꜱɪɴɢ ɪɴᴠɪᴛᴇ ʟɪɴᴋ...**\n\n"
        f"🔗 `{invite_link}`\n\n"
        "📡 ᴀᴛᴛᴇᴍᴘᴛɪɴɢ ᴛᴏ ᴊᴏɪɴ..."
    )
    
    try:
        # ===== JOIN VIA INVITE LINK =====
        joined_chat = await user_app.join_chat(invite_link)
        chat_id = joined_chat.id
        chat_title = getattr(joined_chat, 'title', str(chat_id))
        
        # Check chat type
        chat_type = "ɢʀᴏᴜᴘ" if hasattr(joined_chat, 'title') else "ᴄʜᴀɴɴᴇʟ"
        
        # Get username if available
        try:
            chat = await user_app.get_chat(chat_id)
            if hasattr(chat, 'username') and chat.username:
                username = f"@{chat.username}"
            else:
                username = "ᴘʀɪᴠᴀᴛᴇ"
        except:
            username = "ᴘʀɪᴠᴀᴛᴇ"
        
        # ===== SUCCESSFULLY JOINED =====
        join_msg = f"""
✅ **ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴊᴏɪɴᴇᴅ!**

────────────────────
📌 **ɴᴀᴍᴇ:** {chat_title}
📋 **ᴛʏᴘᴇ:** {chat_type}
🔗 **ʟɪɴᴋ:** `{invite_link}`
🎯 **ɪᴅ:** `{chat_id}`
👤 **ᴜꜱᴇʀɴᴀᴍᴇ:** {username}

────────────────────
💡 **ɴᴇxᴛ ꜱᴛᴇᴘꜱ:**
• ᴛᴏ ꜱᴛᴀʀᴛ ꜰᴏʀᴡᴀʀᴅɪɴɢ: `/ᴊᴏɪɴ {chat_id}`
• ᴛᴏ ᴄʜᴇᴄᴋ ᴀʟʟ ꜰᴏʀᴡᴀʀᴅꜱ: `/ʟɪꜱᴛ`
• ᴛᴏ ꜱᴛᴏᴘ ꜰᴏʀᴡᴀʀᴅɪɴɢ: `/ʟᴇᴀᴠᴇ {chat_id}`

────────────────────
📊 **ᴄᴜʀʀᴇɴᴛ ꜱᴛᴀᴛᴜꜱ:**
• **ʀᴇᴄᴏʀᴅɪɴɢ:** {'🟢 ᴀᴄᴛɪᴠᴇ' if is_recording else '🔴 ɪɴᴀᴄᴛɪᴠᴇ'}
• **ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {len(forward_chats)} ᴄʜᴀᴛꜱ
• **ꜱᴏᴜʀᴄᴇ:** `{RECORD_SOURCE}`
"""
        await status_msg.edit_text(join_msg)
        logger.info(f"ᴊᴏɪɴᴇᴅ ᴠɪᴀ ʟɪɴᴋ: {chat_id} - {chat_title} (ɴᴏ ᴀᴜᴛᴏ-ꜰᴏʀᴡᴀʀᴅ)")
        
    except Exception as e:
        error_str = str(e).lower()
        logger.error(f"ᴊᴏɪɴʟɪɴᴋ ᴇʀʀᴏʀ: {error_str}")
        
        # ===== HANDLE JOIN REQUEST LINKS =====
        if any(keyword in error_str for keyword in ['request', 'approval', 'wait', 'pending']):
            await status_msg.edit_text(
                f"📨 **ᴊᴏɪɴ ʀᴇQᴜᴇꜱᴛ ꜱᴇɴᴛ!**\n\n"
                f"🔗 `{invite_link}`\n"
                f"📋 **ᴛʏᴘᴇ:** 🔵 ʀᴇQᴜᴇꜱᴛ ʟɪɴᴋ (ɴᴇᴇᴅꜱ ᴀᴅᴍɪɴ ᴀᴘᴘʀᴏᴠᴀʟ)\n\n"
                f"────────────────────\n"
                f"⏳ **ꜱᴛᴀᴛᴜꜱ:** ᴘᴇɴᴅɪɴɢ ᴀᴘᴘʀᴏᴠᴀʟ\n\n"
                f"💡 **ɴᴇxᴛ ꜱᴛᴇᴘꜱ:**\n"
                f"• ᴡᴀɪᴛ ꜰᴏʀ ᴀᴅᴍɪɴ ᴛᴏ ᴀᴘᴘʀᴏᴠᴇ ʏᴏᴜʀ ʀᴇQᴜᴇꜱᴛ\n"
                f"• ᴀꜰᴛᴇʀ ᴀᴘᴘʀᴏᴠᴀʟ, ᴜꜱᴇ: `/ᴊᴏɪɴ <ᴄʜᴀᴛ_ɪᴅ>`\n"
                f"• ᴛᴏ ɢᴇᴛ ᴄʜᴀᴛ ɪᴅ, ꜰᴏʀᴡᴀʀᴅ ᴀ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ @ꜱᴛᴀᴛᴜꜱʀᴏʙᴏᴛ"
            )
            return
        
        # ===== HANDLE OTHER ERRORS =====
        if "invite" in error_str and "expired" in error_str:
            error_msg = "❌ **ɪɴᴠɪᴛᴇ ʟɪɴᴋ ʜᴀꜱ ᴇxᴘɪʀᴇᴅ!**\n\nᴘʟᴇᴀꜱᴇ ᴀꜱᴋ ꜰᴏʀ ᴀ ɴᴇᴡ ɪɴᴠɪᴛᴇ ʟɪɴᴋ."
        elif "invalid" in error_str and "hash" in error_str:
            error_msg = f"❌ **ɪɴᴠᴀʟɪᴅ ɪɴᴠɪᴛᴇ ʟɪɴᴋ!**\n\n📌 **ʟɪɴᴋ:** `{invite_link}`\n\nᴘʟᴇᴀꜱᴇ ᴄʜᴇᴄᴋ ᴛʜᴇ ʟɪɴᴋ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ."
        elif "flood" in error_str:
            error_msg = "⚠️ **ꜰʟᴏᴏᴅ ᴄᴏɴᴛʀᴏʟ!**\n\nᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ᴀ ꜰᴇᴡ ᴍɪɴᴜᴛᴇꜱ ʙᴇꜰᴏʀᴇ ᴛʀʏɪɴɢ ᴀɢᴀɪɴ."
        elif "not found" in error_str or ("chat" in error_str and "not" in error_str):
            error_msg = f"❌ **ᴄʜᴀᴛ ɴᴏᴛ ꜰᴏᴜɴᴅ!**\n\n📌 **ʟɪɴᴋ:** `{invite_link}`\n\nᴛʜᴇ ɢʀᴏᴜᴘ ᴍᴀʏ ʜᴀᴠᴇ ʙᴇᴇɴ ᴅᴇʟᴇᴛᴇᴅ ᴏʀ ɪꜱ ᴘʀɪᴠᴀᴛᴇ."
        elif "user" in error_str and "deactivated" in error_str:
            error_msg = "❌ **ᴜꜱᴇʀ ᴀᴄᴄᴏᴜɴᴛ ɪꜱꜱᴜᴇ!**\n\nᴛʜᴇ ʙᴏᴛ ᴜꜱᴇʀ ᴀᴄᴄᴏᴜɴᴛ ᴍᴀʏ ʜᴀᴠᴇ ʙᴇᴇɴ ʟᴏɢɢᴇᴅ ᴏᴜᴛ."
        else:
            error_msg = f"❌ **ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!**\n\n⚠️ `{str(e)[:200]}`"
        
        await status_msg.edit_text(error_msg)
        
# ===== JOIN GROUP COMMAND (PUBLIC + PRIVATE) =====

@bot_app.on_message(pyro_filters.command("joingroup") & authorized_only())
async def cmd_joingroup(client, message):
    """
    ᴊᴏɪɴ ᴀ ᴘᴜʙʟɪᴄ ᴏʀ ᴘʀɪᴠᴀᴛᴇ ɢʀᴏᴜᴘ/ᴄʜᴀɴɴᴇʟ
    - ᴘᴜʙʟɪᴄ: ᴜꜱᴇ ᴜꜱᴇʀɴᴀᴍᴇ ᴏʀ ᴄʜᴀᴛ ɪᴅ
    - ᴘʀɪᴠᴀᴛᴇ: ᴜꜱᴇ ɪɴᴠɪᴛᴇ ʟɪɴᴋ (ꜱᴇɴᴅꜱ ʀᴇQᴜᴇꜱᴛ ɪꜰ ɴᴇᴇᴅᴇᴅ)
    - ᴏɴʟʏ ᴊᴏɪɴꜱ - ᴅᴏᴇꜱ ɴᴏᴛ ꜱᴛᴀʀᴛ ꜰᴏʀᴡᴀʀᴅɪɴɢ
    """
    parts = message.text.split()
    
    if len(parts) < 2:
        help_text = """
❌ **ᴜꜱᴀɢᴇ:** `/joingroup <ᴜꜱᴇʀɴᴀᴍᴇ/ɪɴᴠɪᴛᴇ_ʟɪɴᴋ/ᴄʜᴀᴛ_ɪᴅ>`

────────────────────
📌 **ᴇxᴀᴍᴘʟᴇꜱ:**

**ᴘᴜʙʟɪᴄ ɢʀᴏᴜᴘ/ᴄʜᴀɴɴᴇʟ:**
`/joingroup @ᴘᴜʙʟɪᴄᴄʜᴀᴛ`
`/joingroup -1001234567890`

**ᴘʀɪᴠᴀᴛᴇ ɢʀᴏᴜᴘ/ᴄʜᴀɴɴᴇʟ:**
`/joingroup https://t.me/joinchat/ABC123xyz`
`/joingroup https://t.me/+ABC123xyz`

────────────────────
📋 **ʟɪɴᴋ ᴛʏᴘᴇꜱ:**
• **ᴅɪʀᴇᴄᴛ** - ɪɴꜱᴛᴀɴᴛ ᴊᴏɪɴ (ɴᴏ ᴀᴘᴘʀᴏᴠᴀʟ ɴᴇᴇᴅᴇᴅ)
• **ʀᴇQᴜᴇꜱᴛ** - ꜱᴇɴᴅꜱ ᴊᴏɪɴ ʀᴇQᴜᴇꜱᴛ (ᴀᴡᴀɪᴛꜱ ᴀᴅᴍɪɴ ᴀᴘᴘʀᴏᴠᴀʟ)

────────────────────
⚠️ **ɴᴏᴛᴇ:**
• ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ ᴏɴʟʏ ᴊᴏɪɴꜱ - ɴᴏ ᴀᴜᴛᴏ-ꜰᴏʀᴡᴀʀᴅɪɴɢ
• ᴜꜱᴇ `/ᴊᴏɪɴ <ɪᴅ>` ꜱᴇᴘᴀʀᴀᴛᴇʟʏ ᴛᴏ ꜱᴛᴀʀᴛ ꜰᴏʀᴡᴀʀᴅɪɴɢ
"""
        await message.reply(help_text)
        return
    
    input_value = parts[1].strip()
    input_value = re.sub(r'[<>]', '', input_value)
    
    status_msg = await message.reply(
        f"🔄 **ᴘʀᴏᴄᴇꜱꜱɪɴɢ ᴊᴏɪɴ ʀᴇQᴜᴇꜱᴛ...**\n\n"
        f"📌 **ᴛᴀʀɢᴇᴛ:** `{input_value}`\n\n"
        "📡 ᴀᴛᴛᴇᴍᴘᴛɪɴɢ ᴛᴏ ᴊᴏɪɴ..."
    )
    
    try:
        chat_id = None
        chat_title = None
        chat_type = "ᴜɴᴋɴᴏᴡɴ"
        username = None
        join_method = "ᴜɴᴋɴᴏᴡɴ"
        
        # ===== DETECT INPUT TYPE =====
        
        # Check if it's an invite link (private group)
        if any(pattern in input_value for pattern in ['t.me/joinchat', 't.me/+', 'telegram.me/joinchat', 'telegram.me/+']):
            join_method = "ɪɴᴠɪᴛᴇ ʟɪɴᴋ (ᴘʀɪᴠᴀᴛᴇ)"
            
            # Try to join via invite link
            try:
                joined_chat = await user_app.join_chat(input_value)
                chat_id = joined_chat.id
                chat_title = getattr(joined_chat, 'title', str(chat_id))
                chat_type = "ɢʀᴏᴜᴘ" if hasattr(joined_chat, 'title') else "ᴄʜᴀɴɴᴇʟ"
                
                try:
                    chat = await user_app.get_chat(chat_id)
                    if hasattr(chat, 'username') and chat.username:
                        username = f"@{chat.username}"
                    else:
                        username = "ᴘʀɪᴠᴀᴛᴇ"
                except:
                    username = "ᴘʀɪᴠᴀᴛᴇ"
                    
            except Exception as e:
                error_str = str(e).lower()
                
                # Handle join request links
                if any(keyword in error_str for keyword in ['request', 'approval', 'wait', 'pending']):
                    await status_msg.edit_text(
                        f"📨 **ᴊᴏɪɴ ʀᴇQᴜᴇꜱᴛ ꜱᴇɴᴛ!**\n\n"
                        f"🔗 `{input_value}`\n"
                        f"📋 **ᴛʏᴘᴇ:** 🔵 ʀᴇQᴜᴇꜱᴛ ʟɪɴᴋ (ɴᴇᴇᴅꜱ ᴀᴅᴍɪɴ ᴀᴘᴘʀᴏᴠᴀʟ)\n\n"
                        f"────────────────────\n"
                        f"⏳ **ꜱᴛᴀᴛᴜꜱ:** ᴘᴇɴᴅɪɴɢ ᴀᴘᴘʀᴏᴠᴀʟ\n\n"
                        f"💡 **ɴᴇxᴛ ꜱᴛᴇᴘꜱ:**\n"
                        f"• ᴡᴀɪᴛ ꜰᴏʀ ᴀᴅᴍɪɴ ᴛᴏ ᴀᴘᴘʀᴏᴠᴇ ʏᴏᴜʀ ʀᴇQᴜᴇꜱᴛ\n"
                        f"• ᴀꜰᴛᴇʀ ᴀᴘᴘʀᴏᴠᴀʟ, ᴜꜱᴇ: `/ᴊᴏɪɴ <ᴄʜᴀᴛ_ɪᴅ>`\n"
                        f"• ᴛᴏ ɢᴇᴛ ᴄʜᴀᴛ ɪᴅ, ꜰᴏʀᴡᴀʀᴅ ᴀ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ @ꜱᴛᴀᴛᴜꜱʀᴏʙᴏᴛ"
                    )
                    return
                else:
                    raise e
        
        # Check if it's a username (public chat)
        elif input_value.startswith('@'):
            join_method = "ᴜꜱᴇʀɴᴀᴍᴇ (ᴘᴜʙʟɪᴄ)"
            username_input = input_value[1:]  # Remove @
            
            try:
                # Try to get chat by username
                chat = await user_app.get_chat(username_input)
                chat_id = chat.id
                chat_title = getattr(chat, 'title', str(chat_id))
                chat_type = "ɢʀᴏᴜᴘ" if hasattr(chat, 'title') else "ᴄʜᴀɴɴᴇʟ"
                username = f"@{username_input}"
                
                # Try to join (if not already joined)
                try:
                    joined_chat = await user_app.join_chat(username_input)
                    # If we get here, we successfully joined
                except Exception as e:
                    error_str = str(e).lower()
                    if "already" in error_str and "participant" in error_str:
                        # Already joined, that's fine
                        pass
                    elif "invite" in error_str or "private" in error_str:
                        # Private chat - can't join by username
                        raise Exception("ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ - ᴜꜱᴇ ɪɴᴠɪᴛᴇ ʟɪɴᴋ ɪɴꜱᴛᴇᴀᴅ")
                    else:
                        raise e
                        
            except Exception as e:
                error_str = str(e).lower()
                if "not found" in error_str:
                    raise Exception(f"ᴜꜱᴇʀɴᴀᴍᴇ `{input_value}` ɴᴏᴛ ꜰᴏᴜɴᴅ")
                elif "private" in error_str:
                    raise Exception(f"`{input_value}` ɪꜱ ᴀ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ - ᴜꜱᴇ ɪɴᴠɪᴛᴇ ʟɪɴᴋ")
                else:
                    raise e
        
        # Check if it's a numeric chat ID
        elif input_value.lstrip('-').isdigit():
            join_method = "ᴄʜᴀᴛ ɪᴅ (ᴅɪʀᴇᴄᴛ)"
            chat_id = int(input_value)
            
            try:
                # Try to get chat info
                chat = await user_app.get_chat(chat_id)
                chat_title = getattr(chat, 'title', str(chat_id))
                chat_type = "ɢʀᴏᴜᴘ" if hasattr(chat, 'title') else "ᴄʜᴀɴɴᴇʟ"
                
                if hasattr(chat, 'username') and chat.username:
                    username = f"@{chat.username}"
                else:
                    username = "ᴘʀɪᴠᴀᴛᴇ"
                    
                # Try to join by username if available
                if hasattr(chat, 'username') and chat.username:
                    try:
                        await user_app.join_chat(chat.username)
                    except Exception as e:
                        error_str = str(e).lower()
                        if "already" in error_str and "participant" in error_str:
                            pass
                        else:
                            raise e
                else:
                    # Private chat - try to join by ID (may not work)
                    try:
                        await user_app.join_chat(chat_id)
                    except Exception as e:
                        error_str = str(e).lower()
                        if "already" in error_str and "participant" in error_str:
                            pass
                        else:
                            raise Exception("ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ - ᴜꜱᴇ ɪɴᴠɪᴛᴇ ʟɪɴᴋ ᴛᴏ ᴊᴏɪɴ")
                            
            except Exception as e:
                error_str = str(e).lower()
                if "not found" in error_str:
                    raise Exception(f"ᴄʜᴀᴛ `{chat_id}` ɴᴏᴛ ꜰᴏᴜɴᴅ")
                else:
                    raise e
        
        else:
            await status_msg.edit_text(
                f"❌ **ɪɴᴠᴀʟɪᴅ ɪɴᴘᴜᴛ ꜰᴏʀᴍᴀᴛ!**\n\n"
                f"📌 **ʏᴏᴜ ᴇɴᴛᴇʀᴇᴅ:** `{input_value}`\n\n"
                f"💡 **ꜱᴜᴘᴘᴏʀᴛᴇᴅ ꜰᴏʀᴍᴀᴛꜱ:**\n"
                f"• ᴜꜱᴇʀɴᴀᴍᴇ: `@ᴘᴜʙʟɪᴄᴄʜᴀᴛ`\n"
                f"• ᴄʜᴀᴛ ɪᴅ: `-1001234567890`\n"
                f"• ɪɴᴠɪᴛᴇ ʟɪɴᴋ: `https://t.me/joinchat/...`"
            )
            return
        
        # ===== SUCCESSFULLY JOINED =====
        join_msg = f"""
✅ **ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ ᴊᴏɪɴᴇᴅ!**

────────────────────
📌 **ɴᴀᴍᴇ:** {chat_title}
📋 **ᴛʏᴘᴇ:** {chat_type}
🔗 **ᴊᴏɪɴ ᴍᴇᴛʜᴏᴅ:** {join_method}
🎯 **ɪᴅ:** `{chat_id}`
👤 **ᴜꜱᴇʀɴᴀᴍᴇ:** {username}

────────────────────
💡 **ɴᴇxᴛ ꜱᴛᴇᴘꜱ:**
• ᴛᴏ ꜱᴛᴀʀᴛ ꜰᴏʀᴡᴀʀᴅɪɴɢ: `/ᴊᴏɪɴ {chat_id}`
• ᴛᴏ ᴄʜᴇᴄᴋ ᴀʟʟ ꜰᴏʀᴡᴀʀᴅꜱ: `/ʟɪꜱᴛ`
• ᴛᴏ ꜱᴛᴏᴘ ꜰᴏʀᴡᴀʀᴅɪɴɢ: `/ʟᴇᴀᴠᴇ {chat_id}`

────────────────────
📊 **ᴄᴜʀʀᴇɴᴛ ꜱᴛᴀᴛᴜꜱ:**
• ʀᴇᴄᴏʀᴅɪɴɢ: {'🟢 ᴀᴄᴛɪᴠᴇ' if is_recording else '🔴 ɪɴᴀᴄᴛɪᴠᴇ'}
• ꜰᴏʀᴡᴀʀᴅɪɴɢ: {len(forward_chats)} ᴄʜᴀᴛꜱ
• ꜱᴏᴜʀᴄᴇ: `{RECORD_SOURCE}`
"""
        await status_msg.edit_text(join_msg)
        logger.info(f"ᴊᴏɪɴᴇᴅ ᴠɪᴀ {join_method}: {chat_id} - {chat_title} (ɴᴏ ᴀᴜᴛᴏ-ꜰᴏʀᴡᴀʀᴅ)")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"ᴊᴏɪɴɢʀᴏᴜᴘ ᴇʀʀᴏʀ: {error_msg}")
        
        # ===== HANDLE SPECIFIC ERRORS =====
        error_str = error_msg.lower()
        
        if "invite" in error_str and "expired" in error_str:
            response = "❌ **ɪɴᴠɪᴛᴇ ʟɪɴᴋ ʜᴀꜱ ᴇxᴘɪʀᴇᴅ!**\n\nᴘʟᴇᴀꜱᴇ ᴀꜱᴋ ꜰᴏʀ ᴀ ɴᴇᴡ ɪɴᴠɪᴛᴇ ʟɪɴᴋ."
        elif "invalid" in error_str and "hash" in error_str:
            response = f"❌ **ɪɴᴠᴀʟɪᴅ ɪɴᴠɪᴛᴇ ʟɪɴᴋ!**\n\n📌 `{input_value}`\n\nᴘʟᴇᴀꜱᴇ ᴄʜᴇᴄᴋ ᴛʜᴇ ʟɪɴᴋ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ."
        elif "flood" in error_str:
            response = "⚠️ **ꜰʟᴏᴏᴅ ᴄᴏɴᴛʀᴏʟ!**\n\nᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ᴀ ꜰᴇᴡ ᴍɪɴᴜᴛᴇꜱ ʙᴇꜰᴏʀᴇ ᴛʀʏɪɴɢ ᴀɢᴀɪɴ."
        elif "not found" in error_str:
            response = f"❌ **ᴄʜᴀᴛ ɴᴏᴛ ꜰᴏᴜɴᴅ!**\n\n📌 `{input_value}`\n\nᴛʜᴇ ᴄʜᴀᴛ ᴍᴀʏ ɴᴏᴛ ᴇxɪꜱᴛ ᴏʀ ʏᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀᴄᴄᴇꜱꜱ."
        elif "private" in error_str:
            response = f"❌ **ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ!**\n\n📌 `{input_value}`\n\nᴜꜱᴇ ᴀɴ ɪɴᴠɪᴛᴇ ʟɪɴᴋ ᴛᴏ ᴊᴏɪɴ ᴛʜɪꜱ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛ."
        elif "user" in error_str and "deactivated" in error_str:
            response = "❌ **ᴜꜱᴇʀ ᴀᴄᴄᴏᴜɴᴛ ɪꜱꜱᴜᴇ!**\n\nᴛʜᴇ ʙᴏᴛ ᴜꜱᴇʀ ᴀᴄᴄᴏᴜɴᴛ ᴍᴀʏ ʜᴀᴠᴇ ʙᴇᴇɴ ʟᴏɢɢᴇᴅ ᴏᴜᴛ."
        elif "already" in error_str and "participant" in error_str:
            response = f"ℹ️ **ᴀʟʀᴇᴀᴅʏ ᴀ ᴘᴀʀᴛɪᴄɪᴘᴀɴᴛ!**\n\n📌 `{input_value}`\n\nʏᴏᴜ ᴀʀᴇ ᴀʟʀᴇᴀᴅʏ ɪɴ ᴛʜɪꜱ ᴄʜᴀᴛ."
        else:
            response = f"❌ **ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!**\n\n⚠️ `{error_msg[:200]}`"
        
        await status_msg.edit_text(response)        
        
# ===== ᴍᴜᴛᴇ/ᴜɴᴍᴜᴛᴇ ᴄᴏᴍᴍᴀɴᴅꜱ =====

@bot_app.on_message(pyro_filters.command("mute") & authorized_only())
async def cmd_mute(client, message):
    """ᴍᴜᴛᴇ ᴀᴜᴅɪᴏ ꜰᴏʀᴡᴀʀᴅɪɴɢ - ᴏɴʟʏ ꜰᴏʀᴡᴀʀᴅ ᴄʜᴀᴛꜱ"""
    global is_muted
    
    if is_muted:
        await message.reply(
            "🔇 **ᴀʟʀᴇᴀᴅʏ ᴍᴜᴛᴇᴅ!**\n\n"
            f"📤 **ᴀᴄᴛɪᴠᴇ ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {len(forward_chats)}\n"
            "💡 ᴜꜱᴇ `/ᴜɴᴍᴜᴛᴇ` ᴛᴏ ʀᴇꜱᴜᴍᴇ"
        )
        return
    
    # Sirf forward chats ko pause karo (Source ko mat chhedo)
    paused_count = 0
    for chat_id in list(forward_chats):
        try:
            await call_py.mute(chat_id)
            paused_count += 1
        except Exception as e:
            logger.debug(f"ᴄᴏᴜʟᴅ ɴᴏᴛ ᴘᴀᴜꜱᴇ {chat_id}: {e}")
    
    is_muted = True
    save_state()
    
    mute_msg = f"""
🔇 **ᴀᴜᴅɪᴏ ꜰᴏʀᴡᴀʀᴅɪɴɢ ᴍᴜᴛᴇᴅ!**

────────────────────
📊 **ꜱᴛᴀᴛᴜꜱ:** 🔇 ᴘᴀᴜꜱᴇᴅ
📤 **ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {len(forward_chats)} ᴄʜᴀᴛꜱ
⏸️ **ᴘᴀᴜꜱᴇᴅ:** {paused_count} ꜱᴛʀᴇᴀᴍꜱ
📡 **ꜱᴏᴜʀᴄᴇ:** 🟢 ᴀᴄᴛɪᴠᴇ (ɴᴏᴛ ᴘᴀᴜꜱᴇᴅ)
🎙️ **ᴍɪᴄ:** 🔇 ᴘᴀᴜꜱᴇᴅ
────────────────────

💡 ᴜꜱᴇ `/ᴜɴᴍᴜᴛᴇ` ᴛᴏ ʀᴇꜱᴜᴍᴇ ꜰᴏʀᴡᴀʀᴅɪɴɢ
"""
    await message.reply(mute_msg)
    logger.info(f"ᴀᴜᴅɪᴏ ᴍᴜᴛᴇᴅ - ᴘᴀᴜꜱᴇᴅ {paused_count} ꜰᴏʀᴡᴀʀᴅ ꜱᴛʀᴇᴀᴍꜱ")


@bot_app.on_message(pyro_filters.command("unmute") & authorized_only())
async def cmd_unmute(client, message):
    """ᴜɴᴍᴜᴛᴇ ᴀᴜᴅɪᴏ ꜰᴏʀᴡᴀʀᴅɪɴɢ - ᴏɴʟʏ ꜰᴏʀᴡᴀʀᴅ ᴄʜᴀᴛꜱ"""
    global is_muted
    
    if not is_muted:
        await message.reply(
            "🔊 **ɴᴏᴛ ᴍᴜᴛᴇᴅ!**\n\n"
            f"📤 **ᴀᴄᴛɪᴠᴇ ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {len(forward_chats)}\n"
            "💡 ᴀᴜᴅɪᴏ ɪꜱ ᴀʟʀᴇᴀᴅʏ ꜰʟᴏᴡɪɴɢ"
        )
        return
    
    # Sirf forward chats ko resume karo (Source ko mat chhedo)
    resumed_count = 0
    for chat_id in list(forward_chats):
        try:
            await call_py.unmute(chat_id)
            resumed_count += 1
        except Exception as e:
            logger.debug(f"ᴄᴏᴜʟᴅ ɴᴏᴛ ʀᴇꜱᴜᴍᴇ {chat_id}: {e}")
    
    is_muted = False
    save_state()
    
    unmute_msg = f"""
🔊 **ᴀᴜᴅɪᴏ ꜰᴏʀᴡᴀʀᴅɪɴɢ ʀᴇꜱᴜᴍᴇᴅ!**

────────────────────
📊 **ꜱᴛᴀᴛᴜꜱ:** 🟢 ʟɪᴠᴇ
📤 **ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {len(forward_chats)} ᴄʜᴀᴛꜱ
▶️ **ʀᴇꜱᴜᴍᴇᴅ:** {resumed_count} ꜱᴛʀᴇᴀᴍꜱ
📡 **ꜱᴏᴜʀᴄᴇ:** 🟢 ᴀᴄᴛɪᴠᴇ
🎙️ **ᴍɪᴄ:** 🔊 ᴀᴄᴛɪᴠᴇ
────────────────────

🎵 **ᴀᴜᴅɪᴏ ɪꜱ ɴᴏᴡ ꜰʟᴏᴡɪɴɢ ᴛᴏ ᴀʟʟ ᴄʜᴀᴛꜱ!**
"""
    await message.reply(unmute_msg)
    logger.info(f"ᴀᴜᴅɪᴏ ᴜɴᴍᴜᴛᴇᴅ - ʀᴇꜱᴜᴍᴇᴅ {resumed_count} ꜰᴏʀᴡᴀʀᴅ ꜱᴛʀᴇᴀᴍꜱ")

# ===== ᴀᴜᴛᴏᴍᴜᴛᴇ ᴄᴏᴍᴍᴀɴᴅ =====

@bot_app.on_message(pyro_filters.command("automute") & authorized_only())
async def cmd_automute(client, message):
    """ᴀᴜᴛᴏᴍᴜᴛᴇ ᴏɴ/ᴏꜰꜰ - ɴᴇᴡ ᴊᴏɪɴꜱ ᴀᴜᴛᴏ ᴍᴜᴛᴇ"""
    global auto_mute_enabled, is_muted
    
    parts = message.text.split()
    
    # Agar sirf /automute likha hai toh status dikhao
    if len(parts) < 2:
        status_icon = "🟢" if auto_mute_enabled else "🔴"
        status_text = "ᴏɴ" if auto_mute_enabled else "ᴏꜰꜰ"
        await message.reply(
            f"🎛️ **ᴀᴜᴛᴏᴍᴜᴛᴇ ꜱᴛᴀᴛᴜꜱ:** {status_icon} {status_text}\n\n"
            f"📊 **ᴄᴜʀʀᴇɴᴛ ꜱᴛᴀᴛᴇ:** {'🔇 ᴍᴜᴛᴇᴅ' if is_muted else '🔊 ʟɪᴠᴇ'}\n\n"
            f"💡 `/automute on` - ɴᴇᴡ ᴊᴏɪɴꜱ ᴀᴜᴛᴏ ᴍᴜᴛᴇ\n"
            f"💡 `/automute off` - ɴᴇᴡ ᴊᴏɪɴꜱ ᴀᴜᴛᴏ ᴜɴᴍᴜᴛᴇ\n"
            f"💡 `/automute off` - ᴀʟʟ ᴄʜᴀᴛꜱ ᴜɴᴍᴜᴛᴇ"
        )
        return
    
    mode = parts[1].lower()
    
    if mode == "on":
        auto_mute_enabled = True
        
        # 🔥 FIX: SIRF NAYE JOINS KE LIYE - OLD CHATS KO MAT CHHEDO
        # Purane chats ko mute mat karo! Sirf naye join hone par mute honge
        save_state()
        
        await message.reply(
            "✅ **ᴀᴜᴛᴏᴍᴜᴛᴇ ᴇɴᴀʙʟᴇᴅ!**\n\n"
            f"📊 **ᴄᴜʀʀᴇɴᴛ ꜱᴛᴀᴛᴇ:** {'🔇 ᴍᴜᴛᴇᴅ' if is_muted else '🔊 ʟɪᴠᴇ'}\n"
            "🆕 Nᴇᴡ ᴊᴏɪɴꜱ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ-ᴍᴜᴛᴇᴅ\n"
            "📌 Exɪꜱᴛɪɴɢ ᴄʜᴀᴛꜱ ᴡɪʟʟ ʀᴇᴍᴀɪɴ ᴜɴᴄʜᴀɴɢᴇᴅ"
        )
    
    elif mode == "off":
        auto_mute_enabled = False
        
        # 🔥 FIX: OFF KARNE PAR SAB UNMUTE KARO
        unmuted_count = 0
        if forward_chats:
            for chat_id in list(forward_chats):
                try:
                    await call_py.unmute(chat_id)
                    unmuted_count += 1
                except Exception:
                    pass
            if unmuted_count > 0:
                is_muted = False
                save_state()
        
        await message.reply(
            "✅ **ᴀᴜᴛᴏᴍᴜᴛᴇ ᴅɪꜱᴀʙʟᴇᴅ!**\n\n"
            f"🔊 {unmuted_count} ᴄʜᴀᴛꜱ ᴜɴᴍᴜᴛᴇᴅ\n"
            f"📊 **ᴄᴜʀʀᴇɴᴛ ꜱᴛᴀᴛᴇ:** 🔊 ʟɪᴠᴇ\n"
            "🆕 Nᴇᴡ ᴊᴏɪɴꜱ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ-ᴜɴᴍᴜᴛᴇᴅ"
        )
    
    else:
        await message.reply("❌ **ɪɴᴠᴀʟɪᴅ!**\n\nᴜꜱᴇ `/automute on` ᴏʀ `/automute off`")
        
# ===== ᴇꜰꜰᴇᴄᴛꜱ ᴄᴏᴍᴍᴀɴᴅꜱ =====

@bot_app.on_message(pyro_filters.command("level") & authorized_only())
async def cmd_level(client, message):
    """ꜱᴇᴛ ᴠᴏʟᴜᴍᴇ ʟᴇᴠᴇʟ"""
    parts = message.text.split()
    current = audio_config['volume']
    if len(parts) < 2:
        bar = create_progress_bar(current, 400)
        await message.reply(
            f"🔊 **ᴠᴏʟᴜᴍᴇ ᴄᴏɴᴛʀᴏʟ**\n\n"
            f"📊 **ᴄᴜʀʀᴇɴᴛ:** `{current}%`\n"
            f"📈 {bar} `{current}%`\n"
            f"📌 **ꜱᴛᴀᴛᴜꜱ:** {get_effect_status(current, 400)}\n\n"
            f"💡 **ᴜꜱᴀɢᴇ:** `/level <0-400>`"
        )
        return
    try:
        level = int(parts[1])
        if 0 <= level <= 400:
            audio_config['volume'] = level
            save_state()
            bar = create_progress_bar(level, 400)
            await message.reply(
                f"✅ **ᴠᴏʟᴜᴍᴇ ᴜᴘᴅᴀᴛᴇᴅ!**\n\n"
                f"📊 **ɴᴇᴡ:** `{level}%`\n"
                f"📈 {bar} `{level}%`\n"
                f"📌 **ꜱᴛᴀᴛᴜꜱ:** {get_effect_status(level, 200)}\n\n"
                f"🎯 **ᴘʀᴇᴠɪᴏᴜꜱ:** `{current}%` → **ɴᴇᴡ:** `{level}%`"
            )
        else:
            await message.reply(
                f"❌ **ɪɴᴠᴀʟɪᴅ ʀᴀɴɢᴇ!**\n\n"
                f"📌 **ᴀʟʟᴏᴡᴇᴅ:** `0-400`\n"
                f"📊 **ʏᴏᴜ ᴇɴᴛᴇʀᴇᴅ:** `{level}`"
            )
    except ValueError:
        await message.reply(
            f"❌ **ɪɴᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ!**\n\n"
            f"📌 **ʏᴏᴜ ᴇɴᴛᴇʀᴇᴅ:** `{parts[1]}`\n"
            f"💡 ᴘʟᴇᴀꜱᴇ ᴇɴᴛᴇʀ ᴀ ɴᴜᴍᴇʀɪᴄ ᴠᴀʟᴜᴇ"
        )

@bot_app.on_message(pyro_filters.command("bass") & authorized_only())
async def cmd_bass(client, message):
    """ꜱᴇᴛ ʙᴀꜱꜱ ʙᴏᴏꜱᴛ"""
    parts = message.text.split()
    current = audio_config['bass']
    if len(parts) < 2:
        bar = create_progress_bar(current, 100)
        await message.reply(
            f"🎸 **ʙᴀꜱꜱ ʙᴏᴏꜱᴛ**\n\n"
            f"📊 **ᴄᴜʀʀᴇɴᴛ:** `{current}`\n"
            f"📈 {bar} `{current}/100`\n"
            f"📌 **ꜱᴛᴀᴛᴜꜱ:** {get_effect_status(current, 100)}\n"
            f"🔊 **ʜɪɢʜᴘᴀꜱꜱ:** {'✅ ᴏɴ' if audio_config['highpass'] else '❌ ᴏꜰꜰ'}\n\n"
            f"💡 **ᴜꜱᴀɢᴇ:** `/bass <0-100>`"
        )
        return
    try:
        level = int(parts[1])
        if 0 <= level <= 60:
            audio_config['bass'] = level
            audio_config['highpass'] = level > 0
            save_state()
            bar = create_progress_bar(level, 100)
            await message.reply(
                f"✅ **ʙᴀꜱꜱ ʙᴏᴏꜱᴛ ᴜᴘᴅᴀᴛᴇᴅ!**\n\n"
                f"📊 **ɴᴇᴡ:** `{level}`\n"
                f"📈 {bar} `{level}/60`\n"
                f"📌 **ꜱᴛᴀᴛᴜꜱ:** {get_effect_status(level, 100)}\n"
                f"🔊 **ʜɪɢʜᴘᴀꜱꜱ:** {'✅ ᴇɴᴀʙʟᴇᴅ' if level > 0 else '❌ ᴅɪꜱᴀʙʟᴇᴅ'}\n\n"
                f"🎯 **ᴘʀᴇᴠɪᴏᴜꜱ:** `{current}` → **ɴᴇᴡ:** `{level}`"
            )
        else:
            await message.reply(
                f"❌ **ɪɴᴠᴀʟɪᴅ ʀᴀɴɢᴇ!**\n\n"
                f"📌 **ᴀʟʟᴏᴡᴇᴅ:** `0-100`\n"
                f"📊 **ʏᴏᴜ ᴇɴᴛᴇʀᴇᴅ:** `{level}`"
            )
    except ValueError:
        await message.reply(
            f"❌ **ɪɴᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ!**\n\n"
            f"📌 **ʏᴏᴜ ᴇɴᴛᴇʀᴇᴅ:** `{parts[1]}`\n"
            f"💡 ᴘʟᴇᴀꜱᴇ ᴇɴᴛᴇʀ ᴀ ɴᴜᴍᴇʀɪᴄ ᴠᴀʟᴜᴇ"
        )

@bot_app.on_message(pyro_filters.command("treble") & authorized_only())
async def cmd_treble(client, message):
    """ꜱᴇᴛ ᴛʀᴇʙʟᴇ ʙᴏᴏꜱᴛ"""
    parts = message.text.split()
    current = audio_config['treble']
    if len(parts) < 2:
        bar = create_progress_bar(current, 100)
        await message.reply(
            f"🎵 **ᴛʀᴇʙʟᴇ ʙᴏᴏꜱᴛ**\n\n"
            f"📊 **ᴄᴜʀʀᴇɴᴛ:** `{current}`\n"
            f"📈 {bar} `{current}/100`\n"
            f"📌 **ꜱᴛᴀᴛᴜꜱ:** {get_effect_status(current, 100)}\n\n"
            f"💡 **ᴜꜱᴀɢᴇ:** `/treble <0-100>`"
        )
        return
    try:
        level = int(parts[1])
        if 0 <= level <= 100:
            audio_config['treble'] = level
            save_state()
            bar = create_progress_bar(level, 100)
            await message.reply(
                f"✅ **ᴛʀᴇʙʟᴇ ʙᴏᴏꜱᴛ ᴜᴘᴅᴀᴛᴇᴅ!**\n\n"
                f"📊 **ɴᴇᴡ:** `{level}`\n"
                f"📈 {bar} `{level}/100`\n"
                f"📌 **ꜱᴛᴀᴛᴜꜱ:** {get_effect_status(level, 100)}\n\n"
                f"🎯 **ᴘʀᴇᴠɪᴏᴜꜱ:** `{current}` → **ɴᴇᴡ:** `{level}`"
            )
        else:
            await message.reply(
                f"❌ **ɪɴᴠᴀʟɪᴅ ʀᴀɴɢᴇ!**\n\n"
                f"📌 **ᴀʟʟᴏᴡᴇᴅ:** `0-100`\n"
                f"📊 **ʏᴏᴜ ᴇɴᴛᴇʀᴇᴅ:** `{level}`"
            )
    except ValueError:
        await message.reply(
            f"❌ **ɪɴᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ!**\n\n"
            f"📌 **ʏᴏᴜ ᴇɴᴛᴇʀᴇᴅ:** `{parts[1]}`\n"
            f"💡 ᴘʟᴇᴀꜱᴇ ᴇɴᴛᴇʀ ᴀ ɴᴜᴍᴇʀɪᴄ ᴠᴀʟᴜᴇ"
        )


@bot_app.on_message(pyro_filters.command("gain") & authorized_only())
async def cmd_gain(client, message):
    """ꜱᴇᴛ ɢᴀɪɴ"""
    parts = message.text.split()
    current = audio_config['gain']
    if len(parts) < 2:
        bar = create_progress_bar(current, 100)
        await message.reply(
            f"📈 **ꜱᴏꜰᴛ ɢᴀɪɴ**\n\n"
            f"📊 **ᴄᴜʀʀᴇɴᴛ:** `{current}`\n"
            f"📈 {bar} `{current}/100`\n"
            f"📌 **ꜱᴛᴀᴛᴜꜱ:** {get_effect_status(current, 100)}\n\n"
            f"💡 **ᴜꜱᴀɢᴇ:** `/gain <0-100>`"
        )
        return
    try:
        level = int(parts[1])
        if 0 <= level <= 100:
            audio_config['gain'] = level
            save_state()
            bar = create_progress_bar(level, 100)
            await message.reply(
                f"✅ **ꜱᴏꜰᴛ ɢᴀɪɴ ᴜᴘᴅᴀᴛᴇᴅ!**\n\n"
                f"📊 **ɴᴇᴡ:** `{level}`\n"
                f"📈 {bar} `{level}/100`\n"
                f"📌 **ꜱᴛᴀᴛᴜꜱ:** {get_effect_status(level, 100)}\n\n"
                f"🎯 **ᴘʀᴇᴠɪᴏᴜꜱ:** `{current}` → **ɴᴇᴡ:** `{level}`"
            )
        else:
            await message.reply(
                f"❌ **ɪɴᴠᴀʟɪᴅ ʀᴀɴɢᴇ!**\n\n"
                f"📌 **ᴀʟʟᴏᴡᴇᴅ:** `0-100`\n"
                f"📊 **ʏᴏᴜ ᴇɴᴛᴇʀᴇᴅ:** `{level}`"
            )
    except ValueError:
        await message.reply(
            f"❌ **ɪɴᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ!**\n\n"
            f"📌 **ʏᴏᴜ ᴇɴᴛᴇʀᴇᴅ:** `{parts[1]}`\n"
            f"💡 ᴘʟᴇᴀꜱᴇ ᴇɴᴛᴇʀ ᴀ ɴᴜᴍᴇʀɪᴄ ᴠᴀʟᴜᴇ"
        )

        
@bot_app.on_message(pyro_filters.command("reset") & authorized_only())
async def cmd_reset(client, message):
    """ʀᴇꜱᴇᴛ ᴀʟʟ ᴀᴜᴅɪᴏ ᴇꜰꜰᴇᴄᴛꜱ"""
    global audio_config
    
    # Save old configs for comparison
    old_config = audio_config.copy()
    
    # Reset basic audio config
    audio_config = {
        'volume': 100,
        'bass': 0,
        'treble': 0,
        'gain': 0,
        'compressor': True,
        'limiter': True,
        'highpass': False,
        'lowpass': False
    }
    
    save_state()
    
    reset_msg = f"""
✅ **ᴀʟʟ ᴀᴜᴅɪᴏ ᴇꜰꜰᴇᴄᴛꜱ ʀᴇꜱᴇᴛ!**

────────────────────
🔊 **ᴠᴏʟᴜᴍᴇ:** `{old_config['volume']}%` → `{audio_config['volume']}%` ✅
🎸 **ʙᴀꜱꜱ:** `{old_config['bass']}` → `{audio_config['bass']}` ✅
🎵 **ᴛʀᴇʙʟᴇ:** `{old_config['treble']}` → `{audio_config['treble']}` ✅
📈 **ɢᴀɪɴ:** `{old_config['gain']}` → `{audio_config['gain']}` ✅

────────────────────
⚙️ **ꜰᴇᴀᴛᴜʀᴇꜱ**
• ᴄᴏᴍᴘʀᴇꜱꜱᴏʀ: {'✅ ᴇɴᴀʙʟᴇᴅ' if audio_config['compressor'] else '❌ ᴅɪꜱᴀʙʟᴇᴅ'}
• ʟɪᴍɪᴛᴇʀ: {'✅ ᴇɴᴀʙʟᴇᴅ' if audio_config['limiter'] else '❌ ᴅɪꜱᴀʙʟᴇᴅ'}
• ʜɪɢʜᴘᴀꜱꜱ: {'✅ ᴇɴᴀʙʟᴇᴅ' if audio_config['highpass'] else '❌ ᴅɪꜱᴀʙʟᴇᴅ'}
• ʟᴏᴡᴘᴀꜱꜱ: {'✅ ᴇɴᴀʙʟᴇᴅ' if audio_config['lowpass'] else '❌ ᴅɪꜱᴀʙʟᴇᴅ'}

────────────────────
📊 **ꜱᴛᴀᴛᴜꜱ:** 🟢 ꜰᴀᴄᴛᴏʀʏ ᴅᴇꜰᴀᴜʟᴛ ʀᴇꜱᴛᴏʀᴇᴅ
🎯 **ᴇꜰꜰᴇᴄᴛꜱ:** ᴀʟʟ ʙᴀꜱɪᴄ ᴇꜰꜰᴇᴄᴛꜱ ᴄʟᴇᴀʀᴇᴅ
"""
    await message.reply(reset_msg)
    logger.info("ᴀʟʟ ᴀᴜᴅɪᴏ ᴇꜰꜰᴇᴄᴛꜱ ʀᴇꜱᴇᴛ ᴛᴏ ᴅᴇꜰᴀᴜʟᴛ")


@bot_app.on_message(pyro_filters.command("effects") & authorized_only())
async def cmd_effects(client, message):
    """ꜱʜᴏᴡ ᴄᴜʀʀᴇɴᴛ ᴀᴜᴅɪᴏ ᴇꜰꜰᴇᴄᴛꜱ"""
    config = audio_config
    scipy_status = "✅ ᴀᴅᴠᴀɴᴄᴇᴅ ᴀᴠᴀɪʟᴀʙʟᴇ" if SCIPY_AVAILABLE else "❌ ʙᴀꜱɪᴄ ᴏɴʟʏ"
    
    vol_bar = create_progress_bar(config['volume'], 400)
    bass_bar = create_progress_bar(config['bass'], 100)
    treble_bar = create_progress_bar(config['treble'], 100)
    gain_bar = create_progress_bar(config['gain'], 100)
    
    effects_msg = f"""
🎛️ **ᴀᴜᴅɪᴏ ᴇꜰꜰᴇᴄᴛꜱ ᴅᴀꜱʜʙᴏᴀʀᴅ**

────────────────────
🔊 **ᴠᴏʟᴜᴍᴇ:** `{config['volume']}%`
{vol_bar} `{config['volume']}%`

🎸 **ʙᴀꜱꜱ:** `{config['bass']}/100`
{bass_bar} `{config['bass']}/100`

🎵 **ᴛʀᴇʙʟᴇ:** `{config['treble']}/100`
{treble_bar} `{config['treble']}/100`

📈 **ɢᴀɪɴ:** `{config['gain']}/100`
{gain_bar} `{config['gain']}/100`

────────────────────
⚙️ **ꜰᴇᴀᴛᴜʀᴇꜱ**
• ᴄᴏᴍᴘʀᴇꜱꜱᴏʀ: {'✅ ᴇɴᴀʙʟᴇᴅ' if config['compressor'] else '❌ ᴅɪꜱᴀʙʟᴇᴅ'}
• ʟɪᴍɪᴛᴇʀ: {'✅ ᴇɴᴀʙʟᴇᴅ' if config['limiter'] else '❌ ᴅɪꜱᴀʙʟᴇᴅ'}
• ʜɪɢʜᴘᴀꜱꜱ: {'✅ ᴇɴᴀʙʟᴇᴅ' if config['highpass'] else '❌ ᴅɪꜱᴀʙʟᴇᴅ'}
• ʟᴏᴡᴘᴀꜱꜱ: {'✅ ᴇɴᴀʙʟᴇᴅ' if config['lowpass'] else '❌ ᴅɪꜱᴀʙʟᴇᴅ'}

📦 **ꜱᴄɪᴘʏ:** {scipy_status}
"""
    await message.reply(effects_msg)

@bot_app.on_message(pyro_filters.command("status") & authorized_only())
async def cmd_status(client, message):
    """ꜱʜᴏᴡ ᴄᴏᴍᴘʟᴇᴛᴇ ʙᴏᴛ ꜱᴛᴀᴛᴜꜱ"""
    recording_status = "🟢 ᴀᴄᴛɪᴠᴇ" if is_recording else "🔴 ɪɴᴀᴄᴛɪᴠᴇ"
    audio_status = "🔇 ᴍᴜᴛᴇᴅ" if is_muted else "🔊 ʟɪᴠᴇ"
    forward_count = len(forward_chats)
    forward_list = ""
    if forward_chats:
        forward_list = "\n".join(f"• `{c}`" for c in list(forward_chats)[:10])
        if len(forward_chats) > 10:
            forward_list += f"\n• ... ᴀɴᴅ {len(forward_chats)-10} ᴍᴏʀᴇ"
    else:
        forward_list = "• ɴᴏɴᴇ"
    status_msg = f"""
📊 **ʙᴏᴛ ꜱᴛᴀᴛᴜꜱ ᴅᴀꜱʜʙᴏᴀʀᴅ**

────────────────────
🔴 **ʀᴇᴄᴏʀᴅɪɴɢ:** {recording_status}
📡 **ꜱᴏᴜʀᴄᴇ:** `{RECORD_SOURCE}`
🔊 **ᴀᴜᴅɪᴏ:** {audio_status}
📤 **ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {forward_count} ᴄʜᴀᴛꜱ
⏱️ **ᴜᴘᴛɪᴍᴇ:** `{get_uptime()}`
────────────────────

📤 **ᴀᴄᴛɪᴠᴇ ꜰᴏʀᴡᴀʀᴅɪɴɢ:**
{forward_list}

────────────────────
🎵 **ᴀᴄᴛɪᴠᴇ ᴇꜰꜰᴇᴄᴛꜱ:**
• ᴠᴏʟᴜᴍᴇ: `{audio_config['volume']}%`
• ʙᴀꜱꜱ: `{audio_config['bass']}`
• ᴛʀᴇʙʟᴇ: `{audio_config['treble']}`
• ɢᴀɪɴ: `{audio_config['gain']}`

📊 **ꜱʏꜱᴛᴇᴍ:** {'🟢 ꜱᴛᴀʙʟᴇ' if is_recording else '🟡 ꜱᴛᴀɴᴅʙʏ'}
"""
    await message.reply(status_msg)

@bot_app.on_message(pyro_filters.command("list") & authorized_only())
async def cmd_list(client, message):
    """ꜱʜᴏᴡ ʟɪꜱᴛ ᴏꜰ ꜰᴏʀᴡᴀʀᴅᴇᴅ ᴄʜᴀᴛꜱ"""
    if not forward_chats:
        await message.reply(
            "📭 **ɴᴏ ᴀᴄᴛɪᴠᴇ ꜰᴏʀᴡᴀʀᴅɪɴɢ**\n\n"
            "💡 ᴜꜱᴇ `/ᴊᴏɪɴ <ᴄʜᴀᴛ_ɪᴅ>` ᴛᴏ ꜱᴛᴀʀᴛ\n"
            "📌 ᴇxᴀᴍᴘʟᴇ: `/ᴊᴏɪɴ -1003929100976`"
        )
        return
    chat_list = []
    for idx, cid in enumerate(forward_chats, 1):
        chat_list.append(f"`{idx}.` `{cid}`")
    list_msg = f"""
📤 **ꜰᴏʀᴡᴀʀᴅɪɴɢ ᴄʜᴀᴛꜱ ʟɪꜱᴛ**

────────────────────
📊 **ᴛᴏᴛᴀʟ:** {len(forward_chats)} ᴄʜᴀᴛꜱ
────────────────────

{chr(10).join(chat_list)}

────────────────────
💡 **ᴛɪᴘꜱ:**
• ᴜꜱᴇ `/ʟᴇᴀᴠᴇ <ɪᴅ>` ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴀ ᴄʜᴀᴛ
• ᴜꜱᴇ `/ʟᴇᴀᴠᴇᴀʟʟ` ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴀʟʟ
"""
    await message.reply(list_msg)

# ===== ꜱᴇᴛ ʀᴇᴄᴏʀᴅ ɢʀᴏᴜᴘ ᴄᴏᴍᴍᴀɴᴅ =====

@bot_app.on_message(pyro_filters.command("setrecordgroup") & pyro_filters.user(OWNER_ID))
async def cmd_setrecordgroup(client, message):
    """ꜱᴇᴛ ᴛʜᴇ ꜱᴏᴜʀᴄᴇ ʀᴇᴄᴏʀᴅɪɴɢ ɢʀᴏᴜᴘ (OWNER ONLY)"""
    global RECORD_SOURCE, is_recording
    
    parts = message.text.split()
    
    if len(parts) < 2:
        await message.reply(
            f"❌ **ᴜꜱᴀɢᴇ:** `/setrecordgroup <ᴄʜᴀᴛ_ɪᴅ>`\n\n"
            f"📌 **ᴇxᴀᴍᴘʟᴇ:** `/setrecordgroup -1003970175858`\n\n"
            f"📊 **ᴄᴜʀʀᴇɴᴛ ꜱᴏᴜʀᴄᴇ:** `{RECORD_SOURCE}`"
        )
        return
    
    chat_id_str = re.sub(r'[^\d-]', '', parts[1])
    
    try:
        new_source = int(chat_id_str)
        old_source = RECORD_SOURCE
        
        if new_source == old_source:
            await message.reply(f"ℹ️ **ᴛʜɪꜱ ɪꜱ ᴀʟʀᴇᴀᴅʏ ᴛʜᴇ ᴄᴜʀʀᴇɴᴛ ꜱᴏᴜʀᴄᴇ ɢʀᴏᴜᴘ!**\n\n📡 **ᴄᴜʀʀᴇɴᴛ ꜱᴏᴜʀᴄᴇ:** `{new_source}`")
            return
        
        status_msg = await message.reply(f"🔄 **ᴄʜᴀɴɢɪɴɢ ꜱᴏᴜʀᴄᴇ ꜰʀᴏᴍ `{old_source}` ᴛᴏ `{new_source}`...**")
        
        # Agar recording active hai toh stop karein
        if is_recording:
            try:
                await call_py.leave_call(old_source)
                is_recording = False
                logger.info(f"ʟᴇꜰᴛ ᴏʟᴅ ꜱᴏᴜʀᴄᴇ: {old_source}")
            except Exception as e:
                logger.warning(f"ᴄᴏᴜʟᴅ ɴᴏᴛ ʟᴇᴀᴠᴇ ᴏʟᴅ ꜱᴏᴜʀᴄᴇ: {e}")
        
        # Update source
        RECORD_SOURCE = new_source
        save_state()
        
        # Agar recording active thi toh naye source mein join karein
        if is_recording:
            success, error = await join_call_safe(new_source)
            if success:
                await call_py.record(new_source, RecordStream(True, AUDIO_PARAMETERS))
                is_recording = True
                await status_msg.edit_text(
                    f"✅ **ꜱᴏᴜʀᴄᴇ ᴄʜᴀɴɢᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!**\n\n"
                    f"📡 **ᴏʟᴅ:** `{old_source}`\n"
                    f"🎯 **ɴᴇᴡ:** `{new_source}`\n"
                    f"📊 **ꜱᴛᴀᴛᴜꜱ:** 🟢 ʀᴇᴄᴏʀᴅɪɴɢ"
                )
            else:
                is_recording = False
                await status_msg.edit_text(
                    f"⚠️ **ꜱᴏᴜʀᴄᴇ ᴄʜᴀɴɢᴇᴅ ʙᴜᴛ ꜰᴀɪʟᴇᴅ ᴛᴏ ᴊᴏɪɴ!**\n\n"
                    f"📡 **ɴᴇᴡ ꜱᴏᴜʀᴄᴇ:** `{new_source}`\n"
                    f"⚠️ **ᴇʀʀᴏʀ:** `{error}`\n"
                    f"💡 ᴜꜱᴇ `/ʀᴇᴄᴏʀᴅ` ᴛᴏ ᴛʀʏ ᴀɢᴀɪɴ"
                )
        else:
            await status_msg.edit_text(
                f"✅ **ꜱᴏᴜʀᴄᴇ ᴄʜᴀɴɢᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!**\n\n"
                f"📡 **ᴏʟᴅ:** `{old_source}`\n"
                f"🎯 **ɴᴇᴡ:** `{new_source}`\n"
                f"📊 **ꜱᴛᴀᴛᴜꜱ:** 🔴 ꜱᴛᴀɴᴅʙʏ\n\n"
                f"💡 ᴜꜱᴇ `/ʀᴇᴄᴏʀᴅ` ᴛᴏ ꜱᴛᴀʀᴛ"
            )
        
        logger.info(f"ꜱᴏᴜʀᴄᴇ ᴄʜᴀɴɢᴇᴅ ꜰʀᴏᴍ {old_source} ᴛᴏ {new_source} ʙʏ ᴏᴡɴᴇʀ")
        
    except ValueError:
        await message.reply(f"❌ **ɪɴᴠᴀʟɪᴅ ᴄʜᴀᴛ ɪᴅ!**\n\n📌 **ʏᴏᴜ ᴇɴᴛᴇʀᴇᴅ:** `{parts[1]}`")
    except Exception as e:
        await message.reply(f"❌ **ᴇʀʀᴏʀ:** `{str(e)}`")
        
# ==================== ꜱᴇᴛ ꜱᴇꜱꜱɪᴏɴ ᴄᴏᴍᴍᴀɴᴅ ====================

@bot_app.on_message(pyro_filters.command("setsession") & pyro_filters.user(OWNER_ID))
async def cmd_setsession(client, message):
    """
    ꜱᴇᴛ ᴜᴘᴅᴀᴛᴇ ꜱᴛʀɪɴɢ ꜱᴇꜱꜱɪᴏɴ ᴀɴᴅ ʀᴇꜱᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ
    /setsession <STRING_SESSION>
    """
    parts = message.text.split()
    
    if len(parts) < 2:
        await message.reply(
            "❌ **ᴜꜱᴀɢᴇ:** `/setsession <ꜱᴛʀɪɴɢ_ꜱᴇꜱꜱɪᴏɴ>`\n\n"
            "**ᴇxᴀᴍᴘʟᴇ:**\n"
            "`/setsession BQG9NeoAKgnwMUVxrdLuZqchTSFQaiKJpPuSYhmG29j15hA7BHwFt5-BlIbFOhO4aY6NHKSgdeqp6FmGtIk0_6Aao11efgSUBx23sbDiFj-1Wq2YyZnnUteWe7ao5tienj13NGwYnrxb3pbQpFMeQFwGhtfUzXbVTgiVT4KD3xks7bFfeA_bpkuM50WEs_4yB9KFzsLQZ99oirkxmUXe8r9DDiXKvpkppPKO50Np6gArSQ_MUI7f5sxW9RMNl6YwJYfI837hkPIjFL9ZkgqG2KXV-wCai93e5bR2K_zPS6vh6rZ8RCv_mfjtjaf0hDpsx4Eh7FDgWmWk2VNGcGUdz3ODozAE4QAAAAIJm0jrAA`\n\n"
            "⚠️ **ᴛʜᴇ ʙᴏᴛ ᴡɪʟʟ ʀᴇꜱᴛᴀʀᴛ ᴀꜰᴛᴇʀ ᴜᴘᴅᴀᴛɪɴɢ ᴛʜᴇ ꜱᴇꜱꜱɪᴏɴ!**"
        )
        return
    
    new_session = " ".join(parts[1:]).strip()
    
    # Validate session string length (basic check)
    if len(new_session) < 50:
        await message.reply(
            "❌ **ɪɴᴠᴀʟɪᴅ ꜱᴇꜱꜱɪᴏɴ ꜱᴛʀɪɴɢ!**\n\n"
            "ᴛʜᴇ ꜱᴇꜱꜱɪᴏɴ ꜱᴛʀɪɴɢ ꜱᴇᴇᴍꜱ ᴛᴏᴏ ꜱʜᴏʀᴛ. "
            "ᴘʟᴇᴀꜱᴇ ᴍᴀᴋᴇ ꜱᴜʀᴇ ʏᴏᴜ ᴘᴀꜱᴛᴇ ᴛʜᴇ ᴄᴏᴍᴘʟᴇᴛᴇ ꜱᴛʀɪɴɢ."
        )
        return
    
    # Check if session format looks valid (contains typical pyrogram session pattern)
    if not any(char in new_session for char in ['A', 'B', 'Q', 'G', 'M', 'E', '=']) and len(new_session) < 100:
        await message.reply(
            "⚠️ **ᴜɴᴜꜱᴜᴀʟ ꜱᴇꜱꜱɪᴏɴ ꜰᴏʀᴍᴀᴛ!**\n\n"
            "ᴛʜɪꜱ ᴅᴏᴇꜱɴ'ᴛ ʟᴏᴏᴋ ʟɪᴋᴇ ᴀ ᴛʏᴘɪᴄᴀʟ ᴘʏʀᴏɢʀᴀᴍ ꜱᴇꜱꜱɪᴏɴ ꜱᴛʀɪɴɢ.\n"
            "ᴀʀᴇ ʏᴏᴜ ꜱᴜʀᴇ ɪᴛ'ꜱ ᴄᴏʀʀᴇᴄᴛ? (ʏᴇꜱ/ɴᴏ)"
        )
        return
    
    status_msg = await message.reply(
        "🔄 **ᴜᴘᴅᴀᴛɪɴɢ ꜱᴇꜱꜱɪᴏɴ...**\n\n"
        "⏳ ᴛʜɪꜱ ᴡɪʟʟ ᴛᴀᴋᴇ ᴀ ꜰᴇᴡ ᴍᴏᴍᴇɴᴛꜱ.\n"
        "📱 ᴛʜᴇ ʙᴏᴛ ᴡɪʟʹ ʀᴇꜱᴛᴀʀᴛ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ."
    )
    
    try:
        # ===== 1. VALIDATE SESSION BY TESTING IT =====
        # Try to create a temporary client to test the session
        test_client = Client(
            "test_session",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=new_session
        )
        
        try:
            await test_client.start()
            await test_client.stop()
            logger.info("✅ ᴛᴇꜱᴛ ꜱᴇꜱꜱɪᴏɴ ᴠᴀʟɪᴅᴀᴛɪᴏɴ ᴘᴀꜱꜱᴇᴅ")
        except Exception as e:
            error_str = str(e).lower()
            if "invalid" in error_str or "unauthorized" in error_str:
                await status_msg.edit_text(
                    "❌ **ɪɴᴠᴀʟɪᴅ ꜱᴇꜱꜱɪᴏɴ ꜱᴛʀɪɴɢ!**\n\n"
                    "ᴛʜᴇ ꜱᴇꜱꜱɪᴏɴ ꜱᴛʀɪɴɢ ɪꜱ ɴᴏᴛ ᴠᴀʟɪᴅ ᴏʀ ᴇxᴘɪʀᴇᴅ.\n"
                    "ᴘʟᴇᴀꜱᴇ ɢᴇɴᴇʀᴀᴛᴇ ᴀ ɴᴇᴡ ꜱᴇꜱꜱɪᴏɴ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ."
                )
                return
            else:
                logger.warning(f"ᴛᴇꜱᴛ ꜱᴇꜱꜱɪᴏɴ ᴇʀʀᴏʀ: {e}")
                # Continue anyway, might be a network issue
        
        # ===== 2. SAVE NEW SESSION TO STATE =====
        global STRING_SESSION
        STRING_SESSION = new_session
        save_state()
        
        logger.info(f"🔄 ꜱᴇꜱꜱɪᴏɴ ᴜᴘᴅᴀᴛᴇᴅ ʙʏ ᴏᴡɴᴇʀ {message.from_user.id}")
        
        # ===== 3. SEND CONFIRMATION =====
        await status_msg.edit_text(
            "✅ **ꜱᴇꜱꜱɪᴏɴ ᴜᴘᴅᴀᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!**\n\n"
            "🔄 **ʀᴇꜱᴛᴀʀᴛɪɴɢ ᴛʜᴇ ʙᴏᴛ...**\n"
            "⏳ ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ ꜰᴏʀ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄᴏᴍᴇ ʙᴀᴄᴋ ᴏɴʟɪɴᴇ."
        )
        
        # ===== 4. TRIGGER RESTART =====
        # Small delay to let the message send
        await asyncio.sleep(1)
        
        # Use the existing restart logic
        await cmd_restart(client, message)
        
    except Exception as e:
        logger.error(f"ꜱᴇꜱꜱɪᴏɴ ᴜᴘᴅᴀᴛᴇ ᴇʀʀᴏʀ: {e}")
        await status_msg.edit_text(
            f"❌ **ꜰᴀɪʟᴇᴅ ᴛᴏ ᴜᴘᴅᴀᴛᴇ ꜱᴇꜱꜱɪᴏɴ!**\n\n"
            f"⚠️ **ᴇʀʀᴏʀ:** `{str(e)[:200]}`\n\n"
            "ᴘʟᴇᴀꜱᴇ ᴄʜᴇᴄᴋ ᴛʜᴇ ꜱᴇꜱꜱɪᴏɴ ꜱᴛʀɪɴɢ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ."
        )
        
# ==================== ʀᴇꜱᴛᴀʀᴛ ᴄᴏᴍᴍᴀɴᴅ ====================

@bot_app.on_message(pyro_filters.command("restart") & authorized_only())
async def cmd_restart(client, message):
    """ʀᴇꜱᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ - ᴄʟᴇᴀɴ ᴀɴᴅ ʀᴇᴄᴏɴɴᴇᴄᴛ ᴡɪᴛʜ ꜱᴇꜱꜱɪᴏɴ ʀᴇʟᴏᴀᴅ"""
    global is_recording, is_muted, call_py, forward_chats, RECORD_SOURCE, STRING_SESSION
    
    try:
        status_msg = await message.reply(
            "🔄 **ʀᴇꜱᴛᴀʀᴛɪɴɢ ʙᴏᴛ...**\n\n"
            "📡 ᴄʟᴇᴀɴɪɴɢ ᴜᴘ ᴀʟʟ ᴄᴏɴɴᴇᴄᴛɪᴏɴꜱ..."
        )
        
        # ===== 1. SAVE STATE =====
        save_state()
        logger.info("💾 ꜱᴛᴀᴛᴇ ꜱᴀᴠᴇᴅ")
        
        # ===== 2. LEAVE ALL CALLS =====
        left_count = 0
        failed_count = 0
        
        # Leave source
        try:
            await call_py.leave_call(RECORD_SOURCE)
            left_count += 1
            logger.info(f"ʟᴇꜰᴛ ꜱᴏᴜʀᴄᴇ: {RECORD_SOURCE}")
        except Exception as e:
            failed_count += 1
            logger.debug(f"ᴄᴏᴜʟᴅ ɴᴏᴛ ʟᴇᴀᴠᴇ ꜱᴏᴜʀᴄᴇ: {e}")
        
        # Leave all forward chats
        saved_forwards = list(forward_chats)
        for chat_id in saved_forwards:
            try:
                await call_py.leave_call(chat_id)
                left_count += 1
                logger.info(f"ʟᴇꜰᴛ ꜰᴏʀᴡᴀʀᴅ ᴄʜᴀᴛ: {chat_id}")
            except Exception as e:
                failed_count += 1
                logger.debug(f"ᴄᴏᴜʟᴅ ɴᴏᴛ ʟᴇᴀᴠᴇ {chat_id}: {e}")
        
        # ===== 3. REMEMBER STATE =====
        was_recording = is_recording
        was_muted = is_muted
        is_recording = False
        is_muted = False
        forward_chats.clear()
        logger.info("🧹 ʀᴜɴᴛɪᴍᴇ ꜱᴛᴀᴛᴇ ᴄʟᴇᴀʀᴇᴅ")
        
        # ===== 4. STOP PYTGCALLS =====
        stop_success = False
        try:
            await call_py.stop()
            stop_success = True
            logger.info("🛑 ᴘʏᴛɢᴄᴀʟʟꜱ ꜱᴛᴏᴘᴘᴇᴅ")
        except Exception as e:
            logger.debug(f"ᴘʏᴛɢᴄᴀʟʟꜱ ꜱᴛᴏᴘ ᴇʀʀᴏʀ: {e}")
        
        # ===== 5. WAIT FOR CLEANUP =====
        await asyncio.sleep(2)
        
        # ===== 6. RELOAD SESSION FROM STATE =====
        session_reloaded = False
        try:
            with open(STATE_FILE, "r") as f:
                state_data = json.load(f)
                saved_session = state_data.get("string_session")
                if saved_session and isinstance(saved_session, str) and len(saved_session) > 50:
                    STRING_SESSION = saved_session
                    session_reloaded = True
                    logger.info(f"🔄 ꜱᴇꜱꜱɪᴏɴ ʀᴇʟᴏᴀᴅᴇᴅ ᴀꜰᴛᴇʀ ʀᴇꜱᴛᴀʀᴛ (ʟᴇɴɢᴛʜ: {len(STRING_SESSION)})")
                else:
                    logger.info("ℹ️ ɴᴏ ᴠᴀʟɪᴅ ꜱᴇꜱꜱɪᴏɴ ɪɴ ꜱᴛᴀᴛᴇ, ᴜꜱɪɴɢ ʜᴀʀᴅᴄᴏᴅᴇᴅ ᴏɴᴇ")
        except Exception as e:
            logger.debug(f"ᴄᴏᴜʟᴅɴ'ᴛ ʀᴇʟᴏᴀᴅ ꜱᴇꜱꜱɪᴏɴ ᴀꜰᴛᴇʀ ʀᴇꜱᴛᴀʀᴛ: {e}")
        
        # ===== 7. UPDATE USER_APP WITH NEW SESSION IF RELOADED =====
        if session_reloaded:
            try:
                # Recreate user_app with new session
                global user_app
                user_app = Client(
                    "user_session_v5",
                    api_id=API_ID,
                    api_hash=API_HASH,
                    session_string=STRING_SESSION
                )
                await user_app.start()
                logger.info("✅ ᴜꜱᴇʀ ᴀᴘᴘ ʀᴇᴄʀᴇᴀᴛᴇᴅ ᴡɪᴛʜ ɴᴇᴡ ꜱᴇꜱꜱɪᴏɴ")
            except Exception as e:
                logger.error(f"❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ʀᴇᴄʀᴇᴀᴛᴇ ᴜꜱᴇʀ ᴀᴘᴘ: {e}")
        
        # ===== 8. RESTART PYTGCALLS =====
        restart_success = False
        try:
            # Create new PyTgCalls instance with updated user_app
            call_py = PyTgCalls(user_app)
            
            # Re-register the microphone stream handler
            @call_py.on_update(pytg_filters.stream_frame(Direction.INCOMING, Device.MICROPHONE))
            async def audio_forwarder_handler(_, update: StreamFrames):
                """registered audio handler"""
                await _forward_incoming_frames(update)
            
            # Start PyTgCalls
            await call_py.start()
            logger.info("🔄 ᴘʏᴛɢᴄᴀʟʟꜱ ʀᴇꜱᴛᴀʀᴛᴇᴅ")

            # Rejoin source first
            if was_recording:
                ok, error = await join_call_safe(RECORD_SOURCE)
                if ok:
                    await call_py.record(RECORD_SOURCE, RecordStream(True, AUDIO_PARAMETERS))
                    is_recording = True
                    logger.info(f"✅ ʀᴇꜱᴛᴀʀᴛᴇᴅ ʀᴇᴄᴏʀᴅɪɴɢ ꜰʀᴏᴍ {RECORD_SOURCE}")
                else:
                    is_recording = False
                    logger.error(f"❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ʀᴇꜱᴛᴀʀᴛ ʀᴇᴄᴏʀᴅɪɴɢ: {error}")
            
            # Rejoin all forward chats
            rejoined_count = 0
            for _cid in saved_forwards:
                try:
                    ok, error = await join_call_safe(_cid)
                    if ok:
                        forward_chats.add(_cid)
                        rejoined_count += 1
                        logger.info(f"✅ ʀᴇᴊᴏɪɴᴇᴅ ꜰᴏʀᴡᴀʀᴅ ᴄʜᴀᴛ: {_cid}")
                    else:
                        logger.error(f"❌ ꜰᴀɪʟᴇᴅ ᴛᴏ ʀᴇᴊᴏɪɴ {_cid}: {error}")
                        # Remove failed chats from forward list
                        forward_chats.discard(_cid)
                except Exception as e:
                    logger.error(f"❌ ᴇʀʀᴏʀ ʀᴇᴊᴏɪɴɪɴɢ {_cid}: {e}")
                    forward_chats.discard(_cid)
            
            # Restore mute state if it was muted before
            if was_muted and forward_chats:
                paused = 0
                for chat_id in list(forward_chats):
                    try:
                        await call_py.mute(chat_id)
                        paused += 1
                    except Exception:
                        pass
                if paused:
                    is_muted = True
                    logger.info(f"🔇 ʀᴇꜱᴛᴏʀᴇᴅ ᴍᴜᴛᴇ ꜰᴏʀ {paused} ᴄʜᴀᴛꜱ")
            
            save_state()
            restart_success = True
            logger.info(f"🔄 ʀᴇꜱᴛᴀʀᴛ ᴄᴏᴍᴘʟᴇᴛᴇ: ʀᴇᴄᴏʀᴅɪɴɢ={is_recording}, ꜰᴏʀᴡᴀʀᴅꜱ={len(forward_chats)}, ᴍᴜᴛᴇᴅ={is_muted}")
            
        except Exception as e:
            logger.error(f"ʀᴇꜱᴛᴀʀᴛ ᴘʏᴛɢᴄᴀʟʟꜱ ꜰᴀɪʟᴇᴅ: {e}")
            restart_success = False
        
        # ===== 9. UPDATE STATUS =====
        session_status = "✅ ʀᴇʟᴏᴀᴅᴇᴅ" if session_reloaded else "ℹ️ ᴜꜱɪɴɢ ʜᴀʀᴅᴄᴏᴅᴇᴅ"
        
        if restart_success:
            await status_msg.edit_text(
                f"✅ **ʙᴏᴛ ʀᴇꜱᴛᴀʀᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ!**\n\n"
                f"📊 **ᴄʟᴇᴀɴᴇᴅ:** {left_count} ᴄʜᴀᴛꜱ\n"
                f"⚠️ **ꜰᴀɪʟᴇᴅ:** {failed_count} ᴄʜᴀᴛꜱ\n"
                f"📡 **ꜱᴏᴜʀᴄᴇ:** `{RECORD_SOURCE}`\n"
                f"📤 **ᴀᴄᴛɪᴠᴇ ꜰᴏʀᴡᴀʀᴅꜱ:** {len(forward_chats)}\n"
                f"🔊 **ᴀᴜᴅɪᴏ:** {'🔇 ᴍᴜᴛᴇᴅ' if is_muted else '🔊 ʟɪᴠᴇ'}\n"
                f"🔑 **ꜱᴇꜱꜱɪᴏɴ:** {session_status}\n"
                f"📊 **ꜱᴛᴀᴛᴜꜱ:** 🟢 ʀᴇᴀᴅʏ\n\n"
                f"💡 **ᴜꜱᴇ `/ʀᴇᴄᴏʀᴅ` ᴛᴏ ꜱᴛᴀʀᴛ ᴀɢᴀɪɴ**"
            )
        else:
            await status_msg.edit_text(
                f"⚠️ **ᴘᴀʀᴛɪᴀʟ ʀᴇꜱᴛᴀʀᴛ - ᴄʜᴇᴄᴋ ʟᴏɢꜱ!**\n\n"
                f"📊 **ᴄʟᴇᴀɴᴇᴅ:** {left_count} ᴄʜᴀᴛꜱ\n"
                f"⚠️ **ꜰᴀɪʟᴇᴅ:** {failed_count} ᴄʜᴀᴛꜱ\n"
                f"🛑 **ᴘʏᴛɢᴄᴀʟʟꜱ:** {'✅ ꜱᴛᴏᴘᴘᴇᴅ' if stop_success else '❌ ꜰᴀɪʟᴇᴅ'}\n"
                f"🔄 **ʀᴇꜱᴛᴀʀᴛ:** {'✅ ꜱᴜᴄᴄᴇꜱꜱ' if restart_success else '❌ ꜰᴀɪʟᴇᴅ'}\n"
                f"🔑 **ꜱᴇꜱꜱɪᴏɴ:** {session_status}\n\n"
                f"💡 ᴍᴀɴᴜᴀʟʟʏ ᴄʜᴇᴄᴋ ᴛʜᴇ ʙᴏᴛ ꜱᴛᴀᴛᴜꜱ"
            )
        
        logger.info("✅ ʀᴇꜱᴛᴀʀᴛ ᴄᴏᴍᴍᴀɴᴅ ᴄᴏᴍᴘʟᴇᴛᴇᴅ")
        
    except Exception as e:
        logger.error(f"ʀᴇꜱᴛᴀʀᴛ ᴇʀʀᴏʀ: {e}")
        try:
            await message.reply(
                f"❌ **ʀᴇꜱᴛᴀʀᴛ ꜰᴀɪʟᴇᴅ!**\n\n"
                f"⚠️ **ᴇʀʀᴏʀ:** `{str(e)[:200]}`\n\n"
                f"💡 ᴍᴀɴᴜᴀʟʟʏ ʀᴇꜱᴛᴀʀᴛ ᴛʜᴇ ʙᴏᴛ"
            )
        except Exception:
            logger.error("ᴄᴏᴜʟᴅ ɴᴏᴛ ꜱᴇɴᴅ ᴇʀʀᴏʀ ᴍᴇꜱꜱᴀɢᴇ")

# ==================== ʀᴇꜱᴛᴀʀᴛ ᴄᴏᴍᴍᴀɴᴅ ᴇɴᴅꜱ ====================


# ==================== ᴘᴀɴᴇʟ ᴄᴏᴍᴍᴀɴᴅ ====================

@bot_app.on_message(pyro_filters.command("panel") & authorized_only())
async def cmd_panel(client, message):
    """ꜱʜᴏᴡ ᴄᴏᴍᴘʟᴇᴛᴇ ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ ᴡɪᴛʜ ʙᴜᴛᴛᴏɴꜱ"""
    
    # Get current stats
    recording_status = "🟢 ᴀᴄᴛɪᴠᴇ" if is_recording else "🔴 ɪɴᴀᴄᴛɪᴠᴇ"
    audio_status = "🔇 ᴍᴜᴛᴇᴅ" if is_muted else "🔊 ʟɪᴠᴇ"
    forward_count = len(forward_chats)
    uptime = get_uptime()
    
    # Create status bar
    vol_bar = create_progress_bar(audio_config['volume'], 400)
    bass_bar = create_progress_bar(audio_config['bass'], 100)
    treble_bar = create_progress_bar(audio_config['treble'], 100)
    gain_bar = create_progress_bar(audio_config['gain'], 100)
    
    panel_text = f"""
🎛️ **ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ**

────────────────────
📊 **ꜱʏꜱᴛᴇᴍ ꜱᴛᴀᴛᴜꜱ**
• **ʀᴇᴄᴏʀᴅɪɴɢ:** {recording_status}
• **ᴀᴜᴅɪᴏ:** {audio_status}
• **ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {forward_count} ᴄʜᴀᴛꜱ
• **ᴜᴘᴛɪᴍᴇ:** {uptime}
• **ꜱᴏᴜʀᴄᴇ:** `{RECORD_SOURCE}`

────────────────────
🎵 **ᴀᴜᴅɪᴏ ᴇꜰꜰᴇᴄᴛꜱ**
• **ᴠᴏʟᴜᴍᴇ:** `{audio_config['volume']}%` {vol_bar}
• **ʙᴀꜱꜱ:** `{audio_config['bass']}/100` {bass_bar}
• **ᴛʀᴇʙʟᴇ:** `{audio_config['treble']}/100` {treble_bar}
• **ɢᴀɪɴ:** `{audio_config['gain']}/100` {gain_bar}

────────────────────
📌 **ᴜꜱᴇ ʙᴜᴛᴛᴏɴꜱ ʙᴇʟᴏᴡ ᴛᴏ ᴄᴏɴᴛʀᴏʟ**
"""
    
    # ===== BUILD KEYBOARD WITH ONLY 3 AVAILABLE STYLES =====
    keyboard = build_keyboard([
        # Row 1: Audio Controls
        ("🔇 ᴍᴜᴛᴇ", "panel_mute", ButtonStyle.DANGER),   # Red
        ("🔊 ᴜɴᴍᴜᴛᴇ", "panel_unmute", ButtonStyle.DANGER), # red
        
        # Row 2: Volume Controls
        ("🔉 ᴠᴏʟᴜᴍᴇ -", "panel_vol_down", ButtonStyle.SUCCESS),  # Dark Blue
        ("🔊 ᴠᴏʟᴜᴍᴇ +", "panel_vol_up", ButtonStyle.SUCCESS),    # Dark Blue
        
        # Row 3: Bass Controls
        ("⬇️ ʙᴀꜱꜱ -", "panel_bass_down", ButtonStyle.PRIMARY),  # Dark Blue
        ("⬆️ ʙᴀꜱꜱ +", "panel_bass_up", ButtonStyle.PRIMARY),    # Dark Blue
        
        # Row 4: Treble Controls
        ("⬇️ ᴛʀᴇʙʟᴇ -", "panel_treble_down", ButtonStyle.DANGER), # Dark Blue
        ("⬆️ ᴛʀᴇʙʟᴇ +", "panel_treble_up", ButtonStyle.DANGER),   # Dark Blue
        
        # Row 5: Gain Controls
        ("⬇️ ɢᴀɪɴ -", "panel_gain_down", ButtonStyle.SUCCESS),  # Dark Blue
        ("⬆️ ɢᴀɪɴ +", "panel_gain_up", ButtonStyle.SUCCESS),    # Dark Blue
        
        # Row 6: Utility
        ("🔄 ʀᴇꜱᴇᴛ", "panel_reset", ButtonStyle.DANGER),  # Red
        ("📋 ʟɪꜱᴛ", "panel_list", ButtonStyle.DANGER),   # Dark Blue
        
        # Row 7: Close
        ("❌ ᴄʟᴏꜱᴇ", "panel_close", ButtonStyle.DANGER),  # Red
    ], row_width=2)
    
    await message.reply(
        panel_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )


# ==================== ᴘᴀɴᴇʟ ᴄᴀʟʟʙᴀᴄᴋ ʜᴀɴᴅʟᴇʀꜱ ====================

@bot_app.on_callback_query(pyro_filters.regex(r"^panel_"))
async def panel_callbacks(client, callback_query: CallbackQuery):
    """ʜᴀɴᴅʟᴇ ᴀʟʟ panel_* ᴄᴀʟʟʙᴀᴄᴋ Qᴜᴇʀɪᴇꜱ ꜰʀᴏᴍ /panel"""
    global is_muted, audio_config, RECORD_SOURCE  
    
    data = callback_query.data
    user_id = callback_query.from_user.id
    
    # Check authorization
    if user_id != OWNER_ID and user_id not in approved_users:
        await callback_query.answer("⛔ ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ!", show_alert=True)
        return
    
    await callback_query.answer()
    
    # ===== PANEL MUTE =====
    if data == "panel_mute":
        if is_muted:
            await callback_query.answer("🔇 ᴀʟʀᴇᴀᴅʏ ᴍᴜᴛᴇᴅ!", show_alert=True)
            return
        
        paused_count = 0
        for chat_id in list(forward_chats):
            try:
                await call_py.mute(chat_id)
                paused_count += 1
            except Exception as e:
                logger.debug(f"ᴄᴏᴜʟᴅ ɴᴏᴛ ᴘᴀᴜꜱᴇ {chat_id}: {e}")
        
        is_muted = True
        await callback_query.answer(f"🔇 {paused_count} ᴄʜᴀᴛꜱ ᴍᴜᴛᴇᴅ!", show_alert=True)
        await refresh_panel(client, callback_query)
    
    # ===== PANEL UNMUTE =====
    elif data == "panel_unmute":
        if not is_muted:
            await callback_query.answer("🔊 ᴀʟʀᴇᴀᴅʏ ᴜɴᴍᴜᴛᴇᴅ!", show_alert=True)
            return
        
        resumed_count = 0
        for chat_id in list(forward_chats):
            try:
                await call_py.unmute(chat_id)
                resumed_count += 1
            except Exception as e:
                logger.debug(f"ᴄᴏᴜʟᴅ ɴᴏᴛ ʀᴇꜱᴜᴍᴇ {chat_id}: {e}")
        
        is_muted = False
        await callback_query.answer(f"🔊 {resumed_count} ᴄʜᴀᴛꜱ ᴜɴᴍᴜᴛᴇᴅ!", show_alert=True)
        await refresh_panel(client, callback_query)
    
    # ===== VOLUME CONTROLS =====
    elif data == "panel_vol_up":
        audio_config['volume'] = min(200, audio_config['volume'] + 50)
        save_state()
        await callback_query.answer(f"🔊 ᴠᴏʟᴜᴍᴇ: {audio_config['volume']}%", show_alert=True)
        await refresh_panel(client, callback_query)
    
    elif data == "panel_vol_down":
        audio_config['volume'] = max(0, audio_config['volume'] - 50)
        save_state()
        await callback_query.answer(f"🔉 ᴠᴏʟᴜᴍᴇ: {audio_config['volume']}%", show_alert=True)
        await refresh_panel(client, callback_query)
    
    # ===== BASS CONTROLS =====
    elif data == "panel_bass_up":
        audio_config['bass'] = min(60, audio_config['bass'] + 60)
        audio_config['highpass'] = audio_config['bass'] > 0
        save_state()
        await callback_query.answer(f"🎸 ʙᴀꜱꜱ: {audio_config['bass']}/60", show_alert=True)
        await refresh_panel(client, callback_query)
    
    elif data == "panel_bass_down":
        audio_config['bass'] = max(0, audio_config['bass'] - 30)
        audio_config['highpass'] = audio_config['bass'] > 0
        save_state()
        await callback_query.answer(f"🎸 ʙᴀꜱꜱ: {audio_config['bass']}/60", show_alert=True)
        await refresh_panel(client, callback_query)
    
    # ===== TREBLE CONTROLS =====
    elif data == "panel_treble_up":
        audio_config['treble'] = min(60, audio_config['treble'] + 60)
        save_state()
        await callback_query.answer(f"🎵 ᴛʀᴇʙʟᴇ: {audio_config['treble']}/60", show_alert=True)
        await refresh_panel(client, callback_query)
    
    elif data == "panel_treble_down":
        audio_config['treble'] = max(0, audio_config['treble'] - 30)
        save_state()
        await callback_query.answer(f"🎵 ᴛʀᴇʙʟᴇ: {audio_config['treble']}/60", show_alert=True)
        await refresh_panel(client, callback_query)
    
    # ===== GAIN CONTROLS =====
    elif data == "panel_gain_up":
        audio_config['gain'] = min(60, audio_config['gain'] + 60)
        save_state()
        await callback_query.answer(f"📈 ɢᴀɪɴ: {audio_config['gain']}/60", show_alert=True)
        await refresh_panel(client, callback_query)
    
    elif data == "panel_gain_down":
        audio_config['gain'] = max(0, audio_config['gain'] - 30)
        save_state()
        await callback_query.answer(f"📈 ɢᴀɪɴ: {audio_config['gain']}/60", show_alert=True)
        await refresh_panel(client, callback_query)
    
    # ===== PANEL RESET (FIXED) =====
    elif data == "panel_reset":
        # ✅ FIX: Use .update() instead of reassigning
        audio_config.update({
            'volume': 200,
            'bass': 0,
            'treble': 0,
            'gain': 15,
            'compressor': True,
            'limiter': True,
            'highpass': False,
            'lowpass': False
        })
        save_state()
        await callback_query.answer("🔄 ᴀʟʟ ᴇꜰꜰᴇᴄᴛꜱ ʀᴇꜱᴇᴛ!", show_alert=True)
        await refresh_panel(client, callback_query)
    
    # ===== PANEL LIST =====
    elif data == "panel_list":
        if not forward_chats:
            list_text = "📭 **ɴᴏ ᴀᴄᴛɪᴠᴇ ꜰᴏʀᴡᴀʀᴅɪɴɢ**"
        else:
            chat_list = "\n".join(f"• `{c}`" for c in list(forward_chats)[:15])
            if len(forward_chats) > 15:
                chat_list += f"\n• ... ᴀɴᴅ {len(forward_chats)-15} ᴍᴏʀᴇ"
            list_text = f"""
📤 **ꜰᴏʀᴡᴀʀᴅɪɴɢ ᴄʜᴀᴛꜱ**

────────────────────
📊 **ᴛᴏᴛᴀʟ:** {len(forward_chats)}
────────────────────
{chat_list}
"""
        keyboard = build_keyboard([
            ("⬅️ ʙᴀᴄᴋ", "panel_back", ButtonStyle.PRIMARY)
        ], row_width=1)
        await callback_query.edit_message_text(
            list_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    
    # ===== PANEL BACK =====
    elif data == "panel_back":
        await refresh_panel(client, callback_query)
    
    # ===== PANEL CLOSE =====
    elif data == "panel_close":
        try:
            await callback_query.message.delete()
            await callback_query.answer("✅ ᴘᴀɴᴇʟ ᴄʟᴏꜱᴇᴅ!", show_alert=True)
        except Exception:
            await callback_query.answer("⚠️ ᴄᴏᴜʟᴅ ɴᴏᴛ ᴄʟᴏꜱᴇ", show_alert=True)


# ==================== ʀᴇꜰʀᴇꜱʜ ᴘᴀɴᴇʟ ꜰᴜɴᴄᴛɪᴏɴ ====================

async def refresh_panel(client, callback_query: CallbackQuery):
    """ʀᴇꜰʀᴇꜱʜ ᴛʜᴇ ᴘᴀɴᴇʟ ᴡɪᴛʜ ᴄᴜʀʀᴇɴᴛ ꜱᴛᴀᴛᴜꜱ"""
    
    # Get current stats
    recording_status = "🟢 ᴀᴄᴛɪᴠᴇ" if is_recording else "🔴 ɪɴᴀᴄᴛɪᴠᴇ"
    audio_status = "🔇 ᴍᴜᴛᴇᴅ" if is_muted else "🔊 ʟɪᴠᴇ"
    forward_count = len(forward_chats)
    uptime = get_uptime()
    
    # Create status bars
    vol_bar = create_progress_bar(audio_config['volume'], 200)
    bass_bar = create_progress_bar(audio_config['bass'], 60)
    treble_bar = create_progress_bar(audio_config['treble'], 60)
    gain_bar = create_progress_bar(audio_config['gain'], 60)
    
    panel_text = f"""
🎛️ **ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ** (🔄 ʀᴇꜰʀᴇꜱʜᴇᴅ)

────────────────────
📊 **ꜱʏꜱᴛᴇᴍ ꜱᴛᴀᴛᴜꜱ**
• **ʀᴇᴄᴏʀᴅɪɴɢ:** {recording_status}
• **ᴀᴜᴅɪᴏ:** {audio_status}
• **ꜰᴏʀᴡᴀʀᴅɪɴɢ:** {forward_count} ᴄʜᴀᴛꜱ
• **ᴜᴘᴛɪᴍᴇ:** {uptime}
• **ꜱᴏᴜʀᴄᴇ:** `{RECORD_SOURCE}`

────────────────────
🎵 **ᴀᴜᴅɪᴏ ᴇꜰꜰᴇᴄᴛꜱ**
• **ᴠᴏʟᴜᴍᴇ:** `{audio_config['volume']}%` {vol_bar}
• **ʙᴀꜱꜱ:** `{audio_config['bass']}/60` {bass_bar}
• **ᴛʀᴇʙʟᴇ:** `{audio_config['treble']}/60` {treble_bar}
• **ɢᴀɪɴ:** `{audio_config['gain']}/60` {gain_bar}

────────────────────
📌 **ᴜꜱᴇ ʙᴜᴛᴛᴏɴꜱ ʙᴇʟᴏᴡ ᴛᴏ ᴄᴏɴᴛʀᴏʟ**
"""
    
    # ===== BUILD KEYBOARD WITH ONLY 3 AVAILABLE STYLES =====
    keyboard = build_keyboard([
        # Row 1: Audio Controls
        ("🔇 ᴍᴜᴛᴇ", "panel_mute", ButtonStyle.DANGER),   # Red
        ("🔊 ᴜɴᴍᴜᴛᴇ", "panel_unmute", ButtonStyle.DANGER), # red
        
        # Row 2: Volume Controls
        ("🔉 ᴠᴏʟᴜᴍᴇ -", "panel_vol_down", ButtonStyle.SUCCESS),  # green
        ("🔊 ᴠᴏʟᴜᴍᴇ +", "panel_vol_up", ButtonStyle.SUCCESS),    # Green
        
        # Row 3: Bass Controls
        ("⬇️ ʙᴀꜱꜱ -", "panel_bass_down", ButtonStyle.PRIMARY),  # Dark Blue
        ("⬆️ ʙᴀꜱꜱ +", "panel_bass_up", ButtonStyle.PRIMARY),    # Dark Blue
        
        # Row 4: Treble Controls
        ("⬇️ ᴛʀᴇʙʟᴇ -", "panel_treble_down", ButtonStyle.DANGER), # red
        ("⬆️ ᴛʀᴇʙʟᴇ +", "panel_treble_up", ButtonStyle.DANGER),   # red
        
        # Row 5: Gain Controls
        ("⬇️ ɢᴀɪɴ -", "panel_gain_down", ButtonStyle.SUCCESS),  # Green 
        ("⬆️ ɢᴀɪɴ +", "panel_gain_up", ButtonStyle.SUCCESS),    # green
        
        # Row 6: Utility
        ("🔄 ʀᴇꜱᴇᴛ", "panel_reset", ButtonStyle.DANGER),  # Red
        ("📋 ʟɪꜱᴛ", "panel_list", ButtonStyle.DANGER),   # red
        
        # Row 7: Close
        ("❌ ᴄʟᴏꜱᴇ", "panel_close", ButtonStyle.DANGER),  # Red
    ], row_width=2)
    
    try:
        await callback_query.edit_message_text(
            panel_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.debug(f"ʀᴇꜰʀᴇꜱʜ_ᴘᴀɴᴇʟ ᴇᴅɪᴛ ꜰᴀɪʟᴇᴅ, ʀᴇꜱᴇɴᴅɪɴɢ: {e}")
        try:
            await callback_query.message.delete()
            await callback_query.message.reply_text(
                panel_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
        except Exception:
            pass

# ==================== ᴘᴀɴᴇʟ ᴄᴏᴍᴍᴀɴᴅ ᴇɴᴅꜱ ====================
        
# ==================== MAIN ====================

if __name__ == "__main__":
    # Load initial state
    load_state()
    
    # Print startup banner
    print("🎵 ᴀᴜᴅɪᴏ ꜰᴏʀᴡᴀʀᴅᴇʀ ᴠ5 - ᴄᴏᴍᴘʟᴇᴛᴇ ꜰɪxᴇᴅ ᴠᴇʀꜱɪᴏɴ")
    print("✅ ᴄᴀᴄʜᴇ-ꜰɪʀꜱᴛ ᴀᴘᴘʀᴏᴀᴄʜ ᴡɪᴛʜ ᴇʀʀᴏʀ ʜᴀɴᴅʟɪɴɢ")
    print("✅ ꜰᴜʟʟ ᴀᴜᴅɪᴏ ᴇꜰꜰᴇᴄᴛꜱ ꜱᴜᴘᴘᴏʀᴛ")
    print("✅ ᴜꜱᴇʀ ᴀᴘᴘʀᴏᴠᴀʟ ꜱʏꜱᴛᴇᴍ - ꜱɪʟᴇɴᴛ ɪɢɴᴏʀᴇ ꜰᴏʀ ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜꜱᴇʀꜱ")
    print()
    
    # Check SciPy availability
    if SCIPY_AVAILABLE:
        print("✅ ꜱᴄɪᴘʏ ᴀᴠᴀɪʟᴀʙʟᴇ - ꜰᴜʟʟ ᴀᴜᴅɪᴏ ᴘʀᴏᴄᴇꜱꜱɪɴɢ")
    else:
        print("⚠️ ꜱᴄɪᴘʏ ɴᴏᴛ ᴀᴠᴀɪʟᴀʙʟᴇ - ʙᴀꜱɪᴄ ᴀᴜᴅɪᴏ ᴘʀᴏᴄᴇꜱꜱɪɴɢ ᴏɴʟʏ")
        print("   ɪɴꜱᴛᴀʟʟ ᴡɪᴛʜ: ᴘɪᴘ ɪɴꜱᴛᴀʟʟ ꜱᴄɪᴘʏ\n")
    
    try:
        # Start bot
        bot_app.start()
        print("✅ ʙᴏᴛ ꜱᴛᴀʀᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ")
        
        # Start PyTgCalls (with fallback)
        try:
            call_py.start()
            print("✅ ᴘʏᴛɢᴄᴀʟʟꜱ ꜱᴛᴀʀᴛᴇᴅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟʟʏ")
        except Exception as e:
            print(f"⚠️ ᴘʏᴛɢᴄᴀʟʟꜱ ꜱᴛᴀʀᴛ ꜰᴀɪʟᴇᴅ (User session error): {e}")
            print("   ʙᴏᴛ ᴡɪʟʟ ꜱᴛɪʟʟ ʀᴜɴ ꜰᴏʀ ʙᴏᴛ ᴄᴏᴍᴍᴀɴᴅꜱ!\n")
        
        # Print help/status
        print("\n✅ ᴏɴʟɪɴᴇ! ᴜꜱᴇ /ʀᴇᴄᴏʀᴅ ᴛʜᴇɴ /ᴊᴏɪɴ")
        print("📌 ᴏᴡɴᴇʀ ᴄᴏᴍᴍᴀɴᴅꜱ: /ᴀᴘᴘʀᴏᴠᴇ, /ᴅɪꜱᴀᴘᴘʀᴏᴠᴇ, /ᴜꜱᴇʀʟɪꜱᴛ, /ʀᴇꜱᴛᴀʀᴛ")
        print("📌 ᴀᴜᴅɪᴏ ᴄᴏᴍᴍᴀɴᴅꜱ: /ʟᴇᴠᴇʟ, /ʙᴀꜱꜱ, /ᴛʀᴇʙʟᴇ, /ɢᴀɪɴ, /ᴇꜰꜰᴇᴄᴛꜱ")
        print("📌 ᴇxᴛʀᴀ ᴄᴏᴍᴍᴀɴᴅꜱ: /ᴘɪɴɢ, /ꜱᴛᴀᴛꜱ, /panel")
        print("⚠️ ᴜɴᴀᴜᴛʜᴏʀɪᴢᴇᴅ ᴜꜱᴇʀꜱ ɢᴇᴛ ɴᴏ ʀᴇꜱᴘᴏɴꜱᴇ (ꜱɪʟᴇɴᴛ ɪɢɴᴏʀᴇ)\n")
        
        # Idle (blocks until interrupted)
        idle()
        
    except KeyboardInterrupt:
        print("\n🛑 ꜱʜᴜᴛᴛɪɴɢ ᴅᴏᴡɴ...")
    except Exception as e:
        print(f"❌ ꜰᴀᴛᴀʟ ᴇʀʀᴏʀ: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # ==================== CLEANUP ====================
        print("\n🧹 ᴄʟᴇᴀɴɪɴɢ ᴜᴘ...")
        
        # Leave all forward chats
        for chat in list(forward_chats):
            try:
                call_py.leave_call(chat)
                print(f"    ʟᴇꜰᴛ ᴄʜᴀᴛ: {chat}")
            except Exception as e:
                print(f"    ᴄᴏᴜʟᴅɴ'ᴛ ʟᴇᴀᴠᴇ {chat}: {e}")
        
        # Leave source chat
        try:
            call_py.leave_call(RECORD_SOURCE)
            print(f"    ʟᴇꜰᴛ ꜱᴏᴜʀᴄᴇ: {RECORD_SOURCE}")
        except Exception as e:
            print(f"    ᴄᴏᴜʟᴅɴ'ᴛ ʟᴇᴀᴠᴇ ꜱᴏᴜʀᴄᴇ: {e}")
        
        # Stop PyTgCalls
        try:
            call_py.stop()
            print("    ᴘʏᴛɢᴄᴀʟʟꜱ ꜱᴛᴏᴘᴘᴇᴅ")
        except Exception as e:
            print(f"    ᴘʏᴛɢᴄᴀʟʟꜱ ꜱᴛᴏᴘ ᴇʀʀᴏʀ: {e}")
        
        # Stop bot
        try:
            bot_app.stop()
            print("    ʙᴏᴛ ꜱᴛᴏᴘᴘᴇᴅ")
        except Exception as e:
            print(f"    ʙᴏᴛ ꜱᴛᴏᴘ ᴇʀʀᴏʀ: {e}")
        
        # Save state
        try:
            save_state()
            print("    ꜱᴛᴀᴛᴇ ꜱᴀᴠᴇᴅ")
        except Exception as e:
            print(f"    ꜱᴛᴀᴛᴇ ꜱᴀᴠᴇ ᴇʀʀᴏR: {e}")
        
        print("✅ ᴄʟᴇᴀɴᴜᴘ ᴄᴏᴍᴘʟᴇᴛᴇ")