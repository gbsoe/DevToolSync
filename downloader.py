import logging
import os
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YoutubeDownloader:
    def __init__(self):
        self.base_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            # Use default browser cookies - this is the key change
            # Using this approach means we don't need a separate cookie manager
            'cookiesfrombrowser': ('chrome', ),  # Try Chrome first
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
            
            # Create a copy of base options and add any specific options
            opts = self.base_opts.copy()
            
            # Try multiple browser cookie sources if available
            browser_options = [
                ('chrome', ),
                ('firefox', ),
                ('edge', ),
                ('brave', ),
                ('opera', ),
                ('safari', ),
                # No browser cookies - anonymous access
                None
            ]
            
            info = None
            error_messages = []
            
            # Try different browser cookies until one works
            for browser_opt in browser_options:
                try:
                    if browser_opt:
                        logger.info(f"Trying to get video info with {browser_opt[0]} cookies")
                        opts['cookiesfrombrowser'] = browser_opt
                    else:
                        # Use anonymous access
                        logger.info("Trying anonymous access without browser cookies")
                        if 'cookiesfrombrowser' in opts:
                            del opts['cookiesfrombrowser']
                    
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        
                        # If we got here without an error, break the loop
                        if info:
                            logger.info(f"Successfully retrieved video info using {'anonymous' if not browser_opt else browser_opt[0]}")
                            break
                            
                except Exception as e:
                    error_message = str(e)
                    error_messages.append(f"Error with {browser_opt}: {error_message}")
                    logger.warning(f"Failed to get video info using {'anonymous' if not browser_opt else browser_opt[0]}: {error_message}")
                    # Continue to try the next option
            
            # If we didn't get any info after trying all options, raise an error
            if not info:
                raise Exception(f"Failed to get video info with any browser cookies or anonymously. Errors: {'; '.join(error_messages)}")
            
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
            
            # Base options with browser cookies
            options = {
                'cookiesfrombrowser': ('chrome', ),  # Default to Chrome
                'format': format_id,
                'progress_hooks': [combined_progress_hook],
                'outtmpl': '%(title)s.%(ext)s',
                'verbose': True
            }
            
            if output_path:
                options['outtmpl'] = os.path.join(output_path, options['outtmpl'])
            
            # Try multiple browser cookie sources if available
            browser_options = [
                ('chrome', ),
                ('firefox', ),
                ('edge', ),
                ('brave', ),
                ('opera', ),
                ('safari', ),
                None  # Try without cookies as a last resort
            ]
            
            error_messages = []
            downloaded_file = None
            
            # Try different browser cookies until one works
            for browser_opt in browser_options:
                try:
                    download_options = options.copy()
                    
                    if browser_opt:
                        logger.info(f"Trying to download with {browser_opt[0]} cookies")
                        download_options['cookiesfrombrowser'] = browser_opt
                    else:
                        # Use anonymous access
                        logger.info("Trying anonymous download without browser cookies")
                        if 'cookiesfrombrowser' in download_options:
                            del download_options['cookiesfrombrowser']
                    
                    with yt_dlp.YoutubeDL(download_options) as ydl:
                        info = ydl.extract_info(url, download=True)
                        if info:
                            downloaded_file = os.path.join(output_path if output_path else '.', ydl.prepare_filename(info))
                            logger.info(f"Successfully downloaded video to {downloaded_file}")
                            return downloaded_file
                            
                except Exception as e:
                    error_message = str(e)
                    error_messages.append(f"Error with {browser_opt}: {error_message}")
                    logger.warning(f"Failed to download using {'anonymous' if not browser_opt else browser_opt[0]}: {error_message}")
                    # Continue to try the next option
            
            # If we didn't successfully download with any method, raise an error
            if not downloaded_file:
                raise Exception(f"Failed to download video with any browser cookies or anonymously. Errors: {'; '.join(error_messages)}")
                
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise

    def download_audio(self, url, output_path=None, progress_hook=None, playlist=False):
        try:
            logger.info(f"Starting audio download for URL: {url}")
            
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
                'cookiesfrombrowser': ('chrome', ),  # Default to Chrome
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'progress_hooks': [combined_progress_hook],
                'outtmpl': '%(title)s.%(ext)s',
                'verbose': True
            }
            
            if output_path:
                options['outtmpl'] = os.path.join(output_path, options['outtmpl'])
            
            # Try multiple browser cookie sources if available
            browser_options = [
                ('chrome', ),
                ('firefox', ),
                ('edge', ),
                ('brave', ),
                ('opera', ),
                ('safari', ),
                None  # Try without cookies as a last resort
            ]
            
            error_messages = []
            downloaded_file = None
            
            # Try different browser cookies until one works
            for browser_opt in browser_options:
                try:
                    download_options = options.copy()
                    
                    if browser_opt:
                        logger.info(f"Trying to download audio with {browser_opt[0]} cookies")
                        download_options['cookiesfrombrowser'] = browser_opt
                    else:
                        # Use anonymous access
                        logger.info("Trying anonymous audio download without browser cookies")
                        if 'cookiesfrombrowser' in download_options:
                            del download_options['cookiesfrombrowser']
                    
                    with yt_dlp.YoutubeDL(download_options) as ydl:
                        info = ydl.extract_info(url, download=True)
                        if info:
                            downloaded_file = os.path.join(output_path if output_path else '.', ydl.prepare_filename(info))
                            logger.info(f"Successfully downloaded audio to {downloaded_file}")
                            return downloaded_file
                            
                except Exception as e:
                    error_message = str(e)
                    error_messages.append(f"Error with {browser_opt}: {error_message}")
                    logger.warning(f"Failed to download audio using {'anonymous' if not browser_opt else browser_opt[0]}: {error_message}")
                    # Continue to try the next option
            
            # If we didn't successfully download with any method, raise an error
            if not downloaded_file:
                raise Exception(f"Failed to download audio with any browser cookies or anonymously. Errors: {'; '.join(error_messages)}")
                
        except Exception as e:
            logger.error(f"Error downloading audio: {str(e)}")
            raise