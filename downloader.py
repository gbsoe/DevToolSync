
import logging
import os
import yt_dlp

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

from cookie_manager import CookieManager

class YoutubeDownloader:
    def __init__(self):
        self.cookie_manager = CookieManager()
        self.base_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True
        }
        # Add proxy if configured
        if os.environ.get('USE_PROXY'):
            self.base_opts['proxy'] = os.environ.get('PROXY_URL')

    def get_video_info(self, url):
        try:
            self.cookie_manager.ensure_fresh_cookies()
            opts = {**self.base_opts, 'cookiefile': self.cookie_manager.cookie_file}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            raise

    def download_video(self, url, format_id='best', output_path=None, progress_hook=None, playlist=False):
        try:
            options = {
                'format': format_id,
                'progress_hooks': [progress_hook] if progress_hook else [],
                'outtmpl': '%(title)s.%(ext)s'
            }
            if output_path:
                options['outtmpl'] = os.path.join(output_path, options['outtmpl'])
            
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                return os.path.join(output_path, ydl.prepare_filename(info))
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise

    def download_audio(self, url, output_path=None, progress_hook=None, playlist=False):
        try:
            options = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'progress_hooks': [progress_hook] if progress_hook else [],
                'outtmpl': '%(title)s.%(ext)s'
            }
            if output_path:
                options['outtmpl'] = os.path.join(output_path, options['outtmpl'])

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                return os.path.join(output_path, ydl.prepare_filename(info))
        except Exception as e:
            logger.error(f"Error downloading audio: {str(e)}")
            raise
