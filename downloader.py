import logging
import os
import yt_dlp

from cookie_manager import ensure_fresh_cookies

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YoutubeDownloader:
    def __init__(self):
        self.base_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': False,
            'format_sort': [
                'res:1080p',
                'res:720p',
                'res:480p',
                'res:360p',
                'res:240p',
                'res:144p'
            ]
        }
        
        # Add proxy if configured
        if os.environ.get('USE_PROXY'):
            self.base_opts['proxy'] = os.environ.get('PROXY_URL')

    def get_video_info(self, url):
        try:
            logger.info(f"Getting video info for: {url}")
            
            # Ensure we have fresh cookies
            if not ensure_fresh_cookies():
                logger.warning("Could not refresh cookies, will try to continue without them")
            
            # Create a copy of base options and add any specific options
            opts = self.base_opts.copy()
            opts['cookiefile'] = 'cookies.txt'
            
            # Try to get video info with cookies
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    logger.info("Successfully retrieved video info using cookies")
            except Exception as e:
                logger.warning(f"Failed to get video info with cookies: {str(e)}")
                logger.info("Trying without cookies (anonymous access)")
                
                # Try one more time without cookies
                try:
                    opts.pop('cookiefile', None)
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        logger.info("Successfully retrieved video info anonymously")
                except Exception as anonymous_error:
                    raise Exception(f"Failed to get video info: {str(anonymous_error)}")
            
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
            logger.info(f"Starting video download for URL: {url} with format: {format_id}")
            
            # Ensure we have fresh cookies
            if not ensure_fresh_cookies():
                logger.warning("Could not refresh cookies, will try to continue without them")
            
            def combined_progress_hook(d):
                if d['status'] == 'downloading':
                    try:
                        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                        downloaded = d.get('downloaded_bytes', 0)
                        if total > 0:
                            percent = (downloaded / total) * 100
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
            
            # Base options with cookies
            options = {
                'format': format_id,
                'progress_hooks': [combined_progress_hook],
                'outtmpl': '%(title)s.%(ext)s',
                'verbose': True,
                'cookiefile': 'cookies.txt'
            }
            
            if output_path:
                options['outtmpl'] = os.path.join(output_path, options['outtmpl'])
            
            # Try to download with cookies first
            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(url, download=True)
                    downloaded_file = os.path.join(output_path if output_path else '.', ydl.prepare_filename(info))
                    logger.info(f"Successfully downloaded video to {downloaded_file}")
                    return downloaded_file
            except Exception as cookie_error:
                logger.warning(f"Failed to download with cookies: {str(cookie_error)}")
                logger.info("Trying without cookies (anonymous access)")
                
                # Try one more time without cookies
                try:
                    options.pop('cookiefile', None)
                    with yt_dlp.YoutubeDL(options) as ydl:
                        info = ydl.extract_info(url, download=True)
                        downloaded_file = os.path.join(output_path if output_path else '.', ydl.prepare_filename(info))
                        logger.info(f"Successfully downloaded video anonymously to {downloaded_file}")
                        return downloaded_file
                except Exception as anonymous_error:
                    raise Exception(f"Failed to download video: {str(anonymous_error)}")
                
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise

    def download_audio(self, url, output_path=None, progress_hook=None, playlist=False):
        try:
            logger.info(f"Starting audio download for URL: {url}")
            
            # Ensure we have fresh cookies
            if not ensure_fresh_cookies():
                logger.warning("Could not refresh cookies, will try to continue without them")
            
            def combined_progress_hook(d):
                if d['status'] == 'downloading':
                    try:
                        total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                        downloaded = d.get('downloaded_bytes', 0)
                        if total > 0:
                            percent = (downloaded / total) * 100
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
            
            # Base options with audio extraction
            options = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'progress_hooks': [combined_progress_hook],
                'outtmpl': '%(title)s.%(ext)s',
                'verbose': True,
                'cookiefile': 'cookies.txt'
            }
            
            if output_path:
                options['outtmpl'] = os.path.join(output_path, options['outtmpl'])
            
            # Try to download with cookies first
            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(url, download=True)
                    downloaded_file = os.path.join(output_path if output_path else '.', ydl.prepare_filename(info))
                    logger.info(f"Successfully downloaded audio to {downloaded_file}")
                    return downloaded_file
            except Exception as cookie_error:
                logger.warning(f"Failed to download audio with cookies: {str(cookie_error)}")
                logger.info("Trying without cookies (anonymous access)")
                
                # Try one more time without cookies
                try:
                    options.pop('cookiefile', None)
                    with yt_dlp.YoutubeDL(options) as ydl:
                        info = ydl.extract_info(url, download=True)
                        downloaded_file = os.path.join(output_path if output_path else '.', ydl.prepare_filename(info))
                        logger.info(f"Successfully downloaded audio anonymously to {downloaded_file}")
                        return downloaded_file
                except Exception as anonymous_error:
                    raise Exception(f"Failed to download audio: {str(anonymous_error)}")
                
        except Exception as e:
            logger.error(f"Error downloading audio: {str(e)}")
            raise