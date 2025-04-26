import logging
import os
import yt_dlp

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

from cookie_manager import ensure_fresh_cookies

class YoutubeDownloader:
    def __init__(self):
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
            if not ensure_fresh_cookies():
                raise Exception("Failed to refresh YouTube cookies")
            opts = {
                **self.base_opts,
                'cookiefile': 'cookies.txt',
                'format_sort': [
                    'res:1080p',
                    'res:720p',
                    'res:480p',
                    'res:360p',
                    'res:240p',
                    'res:144p'
                ]
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                # Filter formats to only include standard resolutions
                if 'formats' in info:
                    info['formats'] = [f for f in info['formats'] if 
                        f.get('format_note', '').replace('p60', 'p') in ['1080p', '720p', '480p', '360p', '240p', '144p'] and
                        not f.get('format_note', '').startswith('storyboard') and
                        f.get('vcodec', 'none') != 'none']
                return info
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            raise

    def download_video(self, url, format_id='best', output_path=None, progress_hook=None, playlist=False):
        try:
            if not ensure_fresh_cookies():
                raise Exception("Failed to refresh YouTube cookies")
                
            options = {
                'format': format_id,
                'progress_hooks': [progress_hook] if progress_hook else [],
                'outtmpl': '%(title)s.%(ext)s',
                'cookiefile': 'cookies.txt',
                'quiet': False,
                'no_warnings': False,
                'verbose': True
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
            if not ensure_fresh_cookies():
                raise Exception("Failed to refresh YouTube cookies")
                
            options = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'progress_hooks': [progress_hook] if progress_hook else [],
                'outtmpl': '%(title)s.%(ext)s',
                'cookiefile': 'cookies.txt'  # Use the cookies file
            }
            if output_path:
                options['outtmpl'] = os.path.join(output_path, options['outtmpl'])

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                return os.path.join(output_path, ydl.prepare_filename(info))
        except Exception as e:
            logger.error(f"Error downloading audio: {str(e)}")
            raise