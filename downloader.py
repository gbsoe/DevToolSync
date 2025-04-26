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
            logger.info(f"Starting download process for URL: {url} with format: {format_id}")
            if not ensure_fresh_cookies():
                raise Exception("Failed to refresh YouTube cookies")
            logger.info("Cookies validated successfully")
            
            def combined_progress_hook(d):
                logger.info(f"Download progress: {d}")
                if d['status'] == 'downloading':
                    try:
                        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                        downloaded = d.get('downloaded_bytes', 0)
                        if total > 0:
                            percent = (downloaded / total) * 100
                            speed = d.get('speed', 0)
                            if speed:
                                eta = d.get('eta', 0)
                                d['_percent_str'] = f'{percent:.1f}%'
                                d['_speed_str'] = f'{speed/1024/1024:.1f} MB/s'
                                d['_eta_str'] = f'{eta} seconds'
                            # Ensure we always call the progress hook with percentage
                            if progress_hook:
                                d['progress'] = percent
                                progress_hook(d)
                    except Exception as e:
                        logger.error(f"Error calculating progress: {e}")
                elif d['status'] == 'finished':
                    if progress_hook:
                        d['progress'] = 100
                        progress_hook(d)
                elif d['status'] == 'error':
                    logger.error(f"Download error: {d.get('error')}")
                    if progress_hook:
                        progress_hook(d)
                    
            options = {
                'format': format_id,
                'progress_hooks': [combined_progress_hook],
                'outtmpl': '%(title)s.%(ext)s',
                'cookiefile': 'cookies.txt',
                'quiet': False,
                'no_warnings': False,
                'verbose': True,
                'noprogress': False,
                'postprocessor_hooks': [combined_progress_hook]
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