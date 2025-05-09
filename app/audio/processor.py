import os
import time
import logging
import requests
import subprocess
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Handles downloading and transcribing audio segments."""
    def __init__(self, audio_dir='data/audio', transcript_dir='data/transcripts'):
        self.audio_dir = audio_dir
        self.transcript_dir = transcript_dir
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.transcript_dir, exist_ok=True)

    def download_audio(self, unixtime, duration=90):
        import random
        url = f"https://scanrad.io/download/30/{unixtime}?t={duration}"
        logger.info(f"API URL used for download: {url}")
        audio_path = os.path.join(self.audio_dir, f"audio_{unixtime}.mp3")
        max_retries = 5
        base_delay = 2  # seconds
        attempt = 0
        while attempt < max_retries:
            try:
                response = requests.get(url)
                logger.info(f"Download response headers: {response.headers}")
                if response.status_code == 500:
                    attempt += 1
                    if attempt == max_retries:
                        logger.error(f"Failed to download audio after {max_retries} attempts (500 errors) for url: {url}")
                        return None
                    delay = base_delay * (2 ** (attempt - 1)) * random.uniform(0.8, 1.2)
                    logger.warning(f"HTTP 500 error on attempt {attempt}/{max_retries}. Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                    continue
                elif response.status_code != 200:
                    logger.error(f"Failed to download audio: {response.status_code} {response.reason} for url: {url}")
                    return None
                content_type = response.headers.get("Content-Type", "")
                content = response.content
                # Check content type
                if not content_type.startswith("audio/"):
                    logger.error(f"Download did not return audio! Content-Type: {content_type}.")
                    logger.error(f"First 200 bytes: {content[:200]!r}")
                    return None
                # Check for HTML error page masquerading as audio
                html_signatures = [b'<html', b'<!doctype', b'<head', b'<body', b'no video with supported format']
                first_512 = content[:512].lower()
                if any(sig in first_512 for sig in html_signatures):
                    logger.error(f"Downloaded file appears to be HTML, not audio. Skipping segment. First 200 bytes: {content[:200]!r}")
                    return None
                # Check file size
                if len(content) < 2048:
                    logger.error(f"Downloaded audio file is too small ({len(content)} bytes).")
                    logger.error(f"First 200 bytes: {content[:200]!r}")
                    return None
                # Check MP3 magic bytes (should start with 'ID3' or 0xFF 0xFB)
                if not (content[:3] == b'ID3' or (len(content) > 2 and content[0] == 0xFF and (content[1] & 0xE0) == 0xE0)):
                    logger.error(f"Downloaded file does not appear to be a valid MP3 (bad magic bytes).")
                    logger.error(f"First 200 bytes: {content[:200]!r}")
                    return None
                with open(audio_path, "wb") as f:
                    f.write(content)
                logger.info(f"Downloaded audio to {audio_path} ({len(content)} bytes)")
                return audio_path
            except requests.RequestException as e:
                attempt += 1
                if attempt == max_retries:
                    logger.error(f"Failed to download audio after {max_retries} attempts due to network error: {e}")
                    return None
                delay = base_delay * (2 ** (attempt - 1)) * random.uniform(0.8, 1.2)
                logger.warning(f"Network error on attempt {attempt}/{max_retries}: {e}. Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
        return None

    def transcribe_audio(self, audio_path):
        base = os.path.splitext(os.path.basename(audio_path))[0]
        json_path = os.path.join(self.transcript_dir, f"{base}.json")
        cmd = [
            "whisper-ctranslate2", audio_path, "--model", "medium", "--language", "en", "--output_format", "json",
            "--output_dir", self.transcript_dir
        ]
        try:
            logger.info(f"Running transcription command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"whisper-ctranslate2 failed (returncode={result.returncode}):\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
                logger.error(f"Audio file kept for debugging: {audio_path}")
                return False
            if not os.path.exists(json_path):
                logger.error(f"Transcript file {json_path} not found after transcription.\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}")
                logger.error(f"Audio file kept for debugging: {audio_path}")
                return False
            logger.info(f"Transcription completed and saved to {json_path}")
            return True
        except Exception as e:
            logger.error(f"Transcription failed: {e}\nAudio file kept for debugging: {audio_path}")
            return False

    def run_monitoring_loop(self, start_day=None):
        """
        Hybrid monitoring loop:
        1. On startup, sweep through all possible segments for the current day to catch up on missed segments.
        2. After sweep, enter a polling loop that requests https://scanrad.io/latest/30 every 5s, and only processes new segments as they become available.
        3. Periodically deletes orphaned .mp3 files in the background.
        """
        import threading
        import time
        from collections import deque

        # Adaptive backoff parameters
        import os
        backoff_seconds = 300  # Start at 5 min
        min_backoff = 180      # Minimum 3 min
        max_backoff = int(os.environ.get('MAX_BACKOFF_SECONDS', 900))  # Maximum, env override
        logger.info(f"[AdaptiveBackoff] max_backoff set to {max_backoff//60}m ({max_backoff}s) via environment or default.")
        window_size = 10
        recent_results = deque(maxlen=window_size)

        def log_backoff_change(new_backoff, reason, window):
            logger.info(f"[AdaptiveBackoff] Backoff now {new_backoff//60}m ({new_backoff}s) due to {reason}. Window: {list(window)}")

        def update_backoff():
            nonlocal backoff_seconds
            invalid_count = recent_results.count('invalid')
            if invalid_count > 2 and backoff_seconds < max_backoff:
                backoff_seconds = min(backoff_seconds + 60, max_backoff)
                log_backoff_change(backoff_seconds, f"{invalid_count} invalid in last {window_size}", recent_results)
            elif invalid_count == 0 and len(recent_results) == window_size and backoff_seconds > min_backoff:
                backoff_seconds = max(backoff_seconds - 30, min_backoff)
                log_backoff_change(backoff_seconds, "all valid in window", recent_results)

        def record_result(result, unixtime, age, reason=None):
            recent_results.append(result)
            if result == 'valid':
                logger.info(f"[AdaptiveBackoff] Segment {unixtime} (age: {int(age)}s): valid")
            else:
                logger.info(f"[AdaptiveBackoff] Segment {unixtime} (age: {int(age)}s): invalid ({reason})")
            update_backoff()

        def periodic_cleanup():
            try:
                from scripts.cleanup_orphaned_audio import main as cleanup_orphaned_audio
            except ImportError:
                # fallback to subprocess if import fails
                import subprocess
                import os
                def cleanup_orphaned_audio():
                    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts/cleanup_orphaned_audio.py'))
                    subprocess.run(["python3", script_path])
            while True:
                cleanup_orphaned_audio()
                time.sleep(3600)  # every hour
        threading.Thread(target=periodic_cleanup, daemon=True).start()

        segment_duration = 90  # seconds (1.5 minutes)
        if start_day:
            try:
                current_start_dt = datetime.strptime(start_day, "%Y-%m-%d")
            except ValueError:
                logger.error("AUDIO_DAY must be in YYYY-MM-DD format.")
                return
        else:
            current_start_dt = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        start_dt = current_start_dt
        end_dt = start_dt + timedelta(days=1)
        logger.info(f"Starting monitoring for day: {start_dt.date()}")
        processed = set()

        # --- Sweep: process all missing segments for the day so far ---
        # Configurable max segment age for sweep (default: 1 hour)
        max_segment_age = int(os.environ.get('MAX_SEGMENT_AGE_SECONDS', 3600))
        sweep_fail_count = 0
        for dt in self.daterange(start_dt, datetime.utcnow(), timedelta(seconds=segment_duration)):
            unixtime = int(dt.timestamp())
            json_path = os.path.join(self.transcript_dir, f"audio_{unixtime}.json")
            if os.path.exists(json_path):
                processed.add(unixtime)
                continue
            segment_age = time.time() - unixtime
            now_dt = datetime.utcfromtimestamp(time.time())
            lag_seconds = int(time.time() - unixtime)
            lag_minutes = lag_seconds // 60
            logger.info(f"[Sweep] Segment {dt.isoformat()} (unixtime {unixtime}) | Now: {now_dt.isoformat()} | Lag: {lag_seconds}s ({lag_minutes}m)")
            # Skip segments older than max_segment_age
            if segment_age > max_segment_age:
                logger.info(f"[Sweep] Segment {unixtime} is too old (age: {int(segment_age)}s), skipping (max allowed: {max_segment_age}s)")
                continue
            if segment_age < backoff_seconds:
                logger.info(f"[Sweep] Segment {unixtime} is too recent (age: {int(segment_age)}s), waiting at least {backoff_seconds//60} minutes before processing.")
                continue
            logger.info(f"[Sweep] Processing segment at {dt.isoformat()} (unixtime {unixtime})")
            audio_path = self.download_audio(unixtime, duration=segment_duration)
            if not audio_path:
                record_result('invalid', unixtime, segment_age, reason='download failed or invalid audio')
                sweep_fail_count += 1
                if sweep_fail_count % 10 == 1:
                    logger.warning(f"[Sweep] Failed to download segment at {dt.isoformat()} (failure #{sweep_fail_count})")
                processed.add(unixtime)
                continue
            success = self.transcribe_audio(audio_path)
            if success:
                print(f"[Sweep] Transcript (json) written for: {audio_path}")
                processed.add(unixtime)
                record_result('valid', unixtime, segment_age)
                # --- Alert logic ---
                try:
                    import json
                    from app.alerts.alert_manager import AlertManager
                    from app.users import user_store
                    base = os.path.splitext(os.path.basename(audio_path))[0]
                    json_path = os.path.join(self.transcript_dir, f"{base}.json")
                    with open(json_path, "r") as f:
                        transcript_data = json.load(f)
                    transcript_text = transcript_data.get("text", "")
                    users = user_store.load_users()
                    alert_manager = AlertManager()
                    for user in users:
                        logger.info(f"[Alert Debug] Checking alerts for user: {user.get('email')}")
                        logger.info(f"[Alert Debug] User zones: {user.get('zones', [])}, keywords: {user.get('keywords', [])}")
                        logger.info(f"[Alert Debug] Transcript snippet: {transcript_text[:120]}")
                        alert_manager.check_and_trigger(transcript_text, user, alert_type="email", event_unixtime=unixtime)
                except Exception as e:
                    logger.warning(f"Error during alert check: {e}")
                try:
                    os.remove(audio_path)
                    logger.info(f"Deleted audio file {audio_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete audio file {audio_path}: {e}")
            else:
                logger.warning(f"[Sweep] Transcription failed for: {audio_path}. Deleting audio file anyway.")
                try:
                    os.remove(audio_path)
                    logger.info(f"Deleted audio file {audio_path} after failed transcription.")
                except Exception as e:
                    logger.warning(f"Failed to delete audio file {audio_path} after failed transcription: {e}")

        # --- Polling: monitor for new segments in real time ---
        logger.info("[POLLING] Initial sweep complete. Entering polling mode for new segments.")
        print("[POLLING] Initial sweep complete. Entering polling mode for new segments.")
        try:
            last_heartbeat = time.time()
            heartbeat_interval = 300  # 5 minutes in seconds
            while True:
                try:
                    response = requests.get("https://scanrad.io/latest/30", timeout=10)
                    if response.status_code == 200:
                        latest_info = response.json()
                        if isinstance(latest_info, dict):
                            latest_unixtime = int(latest_info.get("unixtime") or latest_info.get("timestamp") or 0)
                        elif isinstance(latest_info, int):
                            latest_unixtime = latest_info
                        else:
                            logger.warning(f"[Polling] Unexpected response type: {type(latest_info)} - {latest_info}")
                            latest_unixtime = 0
                        if latest_unixtime and latest_unixtime not in processed:
                            import time
                            age = time.time() - latest_unixtime
                            if age < backoff_seconds:
                                logger.info(f"[Polling] Segment {latest_unixtime} is too recent (age: {int(age)}s), waiting at least {backoff_seconds//60} minutes before processing.")
                                time.sleep(30)  # Sleep 30s to reduce log spam and unnecessary polling
                                continue
                            logger.info(f"[Polling] New segment detected: unixtime {latest_unixtime}")
                            audio_path = self.download_audio(latest_unixtime, duration=segment_duration)
                            if not audio_path:
                                record_result('invalid', latest_unixtime, age, reason='download failed or invalid audio')
                                logger.warning(f"[Polling] Failed to download segment: {latest_unixtime}")
                                processed.add(latest_unixtime)
                                continue
                            try:
                                from mutagen.mp3 import MP3
                                audio = MP3(audio_path)
                                if audio.info.length <= 3.0:
                                    logger.info(f"[Skip] Audio segment {latest_unixtime} is {audio.info.length:.2f}s (open key event?), skipping transcription.")
                                    continue
                            except Exception as e:
                                logger.warning(f"[Polling] Failed to check audio duration for {audio_path}: {e}")
                            success = self.transcribe_audio(audio_path)
                            if success:
                                print(f"[Polling] Transcript (json) written for: {audio_path}")
                                processed.add(latest_unixtime)
                                record_result('valid', latest_unixtime, age)
                                # --- Alert logic ---
                                try:
                                    import json
                                    from app.alerts.alert_manager import AlertManager
                                    from app.users import user_store
                                    base = os.path.splitext(os.path.basename(audio_path))[0]
                                    json_path = os.path.join(self.transcript_dir, f"{base}.json")
                                    with open(json_path, "r") as f:
                                        transcript_data = json.load(f)
                                    transcript_text = transcript_data.get("text", "")
                                    users = user_store.load_users()
                                    alert_manager = AlertManager()
                                    for user in users:
                                        logger.info(f"[Alert Debug] Checking alerts for user: {user.get('email')}")
                                        logger.info(f"[Alert Debug] User zones: {user.get('zones', [])}, keywords: {user.get('keywords', [])}")
                                        logger.info(f"[Alert Debug] Transcript snippet: {transcript_text[:120]}")
                                        alert_manager.check_and_trigger(transcript_text, user, alert_type="email", event_unixtime=latest_unixtime)
                                except Exception as e:
                                    logger.warning(f"Error during alert check: {e}")
                                try:
                                    os.remove(audio_path)
                                    logger.info(f"Deleted audio file {audio_path}")
                                except Exception as e:
                                    logger.warning(f"Failed to delete audio file {audio_path}: {e}")
                            else:
                                logger.warning(f"[Polling] Transcription failed for: {audio_path}. Audio file kept for debugging.")
                                logger.warning(f"You can manually inspect or retry transcription for: {audio_path}")
                    else:
                        logger.warning(f"[Polling] Failed to get latest segment info: {response.status_code} {response.reason}")
                except Exception as e:
                    logger.warning(f"[Polling] Exception during latest segment polling: {e}")
                # --- Heartbeat log ---
                now = time.time()
                if now - last_heartbeat > heartbeat_interval:
                    logger.info("[POLLING] Still active, waiting for new segments...")
                    print("[POLLING] Still active, waiting for new segments...")
                    last_heartbeat = now
                time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Polling loop interrupted by user. Exiting.")

    @staticmethod
    def daterange(start_dt, end_dt, delta):
        dt = start_dt
        while dt < end_dt:
            yield dt
            dt += delta
