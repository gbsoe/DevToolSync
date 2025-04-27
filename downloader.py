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
            
            # Always ensure we have fresh cookies for each request
            ensure_fresh_cookies()
            
            # Create a copy of base options with enhanced settings
            opts = self.base_opts.copy()
            opts['cookiefile'] = 'cookies.txt'
            opts['ignoreerrors'] = True
            opts['skip_download'] = True
            opts['quiet'] = False  # Enable more detailed logging
            
            # Add user agents to bypass restrictions
            opts['user_agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            opts['referer'] = 'https://www.youtube.com/'
            
            # Try to get video info with enhanced options and cookies
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        raise Exception("Could not retrieve video information")
                    logger.info("Successfully retrieved video info using cookies")
            except Exception as e:
                logger.warning(f"Failed to get video info with cookies: {str(e)}")
                logger.info("Trying with alternative settings")
                
                # Check for specific error patterns related to restrictions
                error_str = str(e).lower()
                if any(restriction in error_str for restriction in [
                    'sign in to confirm', 'age-restricted', 'private video', 
                    'this video is not available', 'video unavailable', 'video is private'
                ]):
                    # Try with different user agent and cookie configuration
                    try:
                        # Regenerate cookies with different user agent
                        ensure_fresh_cookies()
                        
                        # Try with alternative settings
                        alt_opts = self.base_opts.copy()
                        alt_opts['cookiefile'] = 'cookies.txt'
                        alt_opts['user_agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
                        alt_opts['referer'] = 'https://www.youtube.com/feed/trending'
                        
                        with yt_dlp.YoutubeDL(alt_opts) as ydl:
                            info = ydl.extract_info(url, download=False)
                            if not info:
                                raise Exception("Could not retrieve video information")
                            logger.info("Successfully retrieved video info with alternative settings")
                    except Exception as alt_error:
                        # Provide a user-friendly error message
                        raise Exception("This video has restrictions (age, privacy, or requires login) and cannot be downloaded publicly.")
                
                # If not restricted but failed for other reasons, try one more time without cookies
                else:
                    try:
                        opts.pop('cookiefile', None)
                        with yt_dlp.YoutubeDL(opts) as ydl:
                            info = ydl.extract_info(url, download=False)
                            if not info:
                                raise Exception("Could not retrieve video information")
                            logger.info("Successfully retrieved video info anonymously")
                    except Exception as anonymous_error:
                        # Check for specific error patterns in the second attempt as well
                        error_str = str(anonymous_error).lower()
                        if any(restriction in error_str for restriction in [
                            'sign in to confirm', 'age-restricted', 'private video', 
                            'this video is not available', 'video unavailable', 'video is private'
                        ]):
                            # Provide a user-friendly error message
                            raise Exception("This video has restrictions (age, privacy, or requires login) and cannot be downloaded publicly.")
                        else:
                            raise Exception(f"Failed to get video info: {str(anonymous_error)}")
            
            # Filter formats to only include standard resolutions
            if 'formats' in info:
                seen_qualities = set()
                filtered_formats = []
                
                # Sort formats by quality (higher resolution first)
                sorted_formats = sorted(info['formats'], 
                    key=lambda x: int(x.get('height', 0) or 0), 
                    reverse=True
                )
                
                for f in sorted_formats:
                    format_note = f.get('format_note', '').replace('p60', 'p')
                    if (format_note in ['1080p', '720p', '480p', '360p', '240p', '144p'] and
                        not f.get('format_note', '').startswith('storyboard') and
                        f.get('vcodec', 'none') != 'none' and
                        format_note not in seen_qualities):
                        
                        filtered_formats.append(f)
                        seen_qualities.add(format_note)
                
                info['formats'] = filtered_formats
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            raise

    def download_video(self, url, format_id='best', output_path=None, progress_hook=None, playlist=False):
        try:
            logger.info(f"Starting video download for URL: {url} with format: {format_id}")
            
            # Always ensure we have fresh cookies for each request
            ensure_fresh_cookies()
            
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
            
            # Enhanced options with better browser simulation
            options = {
                'format': format_id,
                'progress_hooks': [combined_progress_hook],
                'outtmpl': '%(title)s.%(ext)s',
                'verbose': True,
                'cookiefile': 'cookies.txt',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'referer': 'https://www.youtube.com/',
                'ignoreerrors': True
            }
            
            if output_path:
                options['outtmpl'] = os.path.join(output_path, options['outtmpl'])
            
            # Try to download with enhanced options and cookies
            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if not info:
                        raise Exception("Could not download video information")
                    downloaded_file = os.path.join(output_path if output_path else '.', ydl.prepare_filename(info))
                    logger.info(f"Successfully downloaded video to {downloaded_file}")
                    return downloaded_file
            except Exception as cookie_error:
                logger.warning(f"Failed to download with primary settings: {str(cookie_error)}")
                
                # Check for specific error patterns related to restrictions
                error_str = str(cookie_error).lower()
                if any(restriction in error_str for restriction in [
                    'sign in to confirm', 'age-restricted', 'private video', 
                    'this video is not available', 'video unavailable', 'video is private'
                ]):
                    # Try with a different approach for restricted videos
                    try:
                        # Regenerate cookies with different user agent
                        ensure_fresh_cookies()
                        
                        # Try with alternative settings
                        alt_options = options.copy()
                        alt_options['user_agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
                        alt_options['referer'] = 'https://www.youtube.com/feed/trending'
                        
                        with yt_dlp.YoutubeDL(alt_options) as ydl:
                            info = ydl.extract_info(url, download=True)
                            if not info:
                                raise Exception("Could not download video")
                            downloaded_file = os.path.join(output_path if output_path else '.', ydl.prepare_filename(info))
                            logger.info(f"Successfully downloaded restricted video with alternative settings to {downloaded_file}")
                            return downloaded_file
                    except Exception as restricted_error:
                        # Provide a user-friendly error message
                        raise Exception("This video has restrictions (age, privacy, or requires login) and cannot be downloaded publicly.")
                
                logger.info("Trying without cookies (anonymous access)")
                
                # Try one more time without cookies for non-restricted videos
                try:
                    options.pop('cookiefile', None)
                    with yt_dlp.YoutubeDL(options) as ydl:
                        info = ydl.extract_info(url, download=True)
                        if not info:
                            raise Exception("Could not download video")
                        downloaded_file = os.path.join(output_path if output_path else '.', ydl.prepare_filename(info))
                        logger.info(f"Successfully downloaded video anonymously to {downloaded_file}")
                        return downloaded_file
                except Exception as anonymous_error:
                    # Check for specific error patterns in the second attempt as well
                    error_str = str(anonymous_error).lower()
                    if any(restriction in error_str for restriction in [
                        'sign in to confirm', 'age-restricted', 'private video', 
                        'this video is not available', 'video unavailable', 'video is private'
                    ]):
                        # Provide a user-friendly error message
                        raise Exception("This video has restrictions (age, privacy, or requires login) and cannot be downloaded publicly.")
                    else:
                        raise Exception(f"Failed to download video: {str(anonymous_error)}")
                
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise

    def get_direct_url(self, url, format_id='best', download_type='video'):
        """Get a direct download URL for a video without actually downloading it"""
        try:
            logger.info(f"Getting direct URL for: {url} with format: {format_id}")
            
            # Always ensure we have fresh cookies for each request
            # This is critical for preventing YouTube's "sign in to confirm you're not a bot" errors
            ensure_fresh_cookies()
            
            # Set the appropriate format based on the download type
            if download_type == 'audio':
                # For audio, use the specific audio format or fallback to bestaudio
                format_spec = f"{format_id}/bestaudio/best"
            else:
                # For video, add fallbacks to the format specification
                # This allows yt-dlp to automatically select the next best format if the requested one isn't available
                format_spec = f"{format_id}/best[height<=720]/best"
            
            # Enhanced options with better browser simulation to bypass bot detection
            options = {
                'format': format_spec,
                'quiet': False,  # Enable output for debugging
                'skip_download': True,
                'cookiefile': 'cookies.txt',
                # Use a more recent Chrome user agent
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'referer': 'https://www.youtube.com/feed/trending',
                'ignoreerrors': False,  # Don't ignore errors to get better error messages
                'verbose': True,  # Enable verbose output
                # Additional anti-bot-detection parameters
                'nocheckcertificate': True,
                'geo_bypass': True,
                'extractor_args': {'youtube': {'player_client': 'web'}}
            }
            
            # Try to get info with enhanced options and cookies
            with yt_dlp.YoutubeDL(options) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        raise Exception("Could not retrieve video information")
                    
                    # Get the URL for the selected format
                    if 'url' in info:
                        logger.info(f"Found direct URL in info: {url[:30]}...")
                        return info['url']
                    elif 'formats' in info:
                        # Log available formats for debugging
                        logger.info(f"Available formats: {[f.get('format_id') for f in info['formats']]}")
                        
                        # First try to find the exact format
                        for fmt in info['formats']:
                            if fmt.get('format_id') == format_id and 'url' in fmt:
                                logger.info(f"Found exact format match for {format_id}")
                                return fmt.get('url')
                        
                        # If we couldn't find the exact format, find the best alternative
                        # For video: find the closest resolution
                        if download_type == 'video':
                            # Sort formats by resolution (height)
                            video_formats = [f for f in info['formats'] if f.get('vcodec', 'none') != 'none' and 'url' in f]
                            if video_formats:
                                # Sort by height (resolution)
                                best_video = sorted(video_formats, key=lambda x: x.get('height', 0), reverse=True)[0]
                                logger.info(f"Using best alternative video format: {best_video.get('format_id')} ({best_video.get('height')}p)")
                                return best_video.get('url')
                        
                        # For audio: find the best audio quality
                        else:
                            audio_formats = [f for f in info['formats'] if f.get('acodec', 'none') != 'none' and 'url' in f]
                            if audio_formats:
                                # Sort by audio bitrate
                                best_audio = sorted(audio_formats, key=lambda x: x.get('abr', 0), reverse=True)[0]
                                logger.info(f"Using best alternative audio format: {best_audio.get('format_id')} ({best_audio.get('abr')}kbps)")
                                return best_audio.get('url')
                        
                        # If we still couldn't find anything, use the first format with a URL
                        for fmt in info['formats']:
                            if 'url' in fmt:
                                logger.info(f"Using fallback format: {fmt.get('format_id')}")
                                return fmt.get('url')
                
                except Exception as inner_error:
                    logger.error(f"Error during yt-dlp extraction: {str(inner_error)}")
                    # Try with a more permissive format string as a last resort
                    logger.info("Trying with a more permissive format string")
                    options['format'] = 'best' if download_type == 'video' else 'bestaudio'
                    try:
                        info = ydl.extract_info(url, download=False)
                        if info and 'url' in info:
                            return info['url']
                    except:
                        pass
                    raise inner_error
            
            raise Exception("Could not find a direct download URL")
            
        except Exception as e:
            logger.error(f"Error getting direct URL: {str(e)}")
            raise Exception(f"Could not generate direct download URL: {str(e)}")
    
    def download_audio(self, url, output_path=None, progress_hook=None, playlist=False):
        try:
            logger.info(f"Starting audio download for URL: {url}")
            
            # Always ensure we have fresh cookies for each request
            ensure_fresh_cookies()
            
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
            
            # Enhanced options with better browser simulation for audio
            options = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                }],
                'progress_hooks': [combined_progress_hook],
                'outtmpl': '%(title)s.%(ext)s',
                'verbose': True,
                'cookiefile': 'cookies.txt',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'referer': 'https://www.youtube.com/',
                'ignoreerrors': True
            }
            
            if output_path:
                options['outtmpl'] = os.path.join(output_path, options['outtmpl'])
            
            # Try to download with enhanced options and cookies
            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if not info:
                        raise Exception("Could not download audio information")
                    downloaded_file = os.path.join(output_path if output_path else '.', ydl.prepare_filename(info))
                    # For audio files, the extension might be changed after post-processing
                    if not os.path.exists(downloaded_file) and downloaded_file.endswith('.webm'):
                        downloaded_file = downloaded_file.replace('.webm', '.mp3')
                    logger.info(f"Successfully downloaded audio to {downloaded_file}")
                    return downloaded_file
            except Exception as cookie_error:
                logger.warning(f"Failed to download audio with primary settings: {str(cookie_error)}")
                
                # Check for specific error patterns related to restrictions
                error_str = str(cookie_error).lower()
                if any(restriction in error_str for restriction in [
                    'sign in to confirm', 'age-restricted', 'private video', 
                    'this video is not available', 'video unavailable', 'video is private'
                ]):
                    # Try with a different approach for restricted videos
                    try:
                        # Regenerate cookies with different user agent
                        ensure_fresh_cookies()
                        
                        # Try with alternative settings
                        alt_options = options.copy()
                        alt_options['user_agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
                        alt_options['referer'] = 'https://www.youtube.com/feed/trending'
                        
                        with yt_dlp.YoutubeDL(alt_options) as ydl:
                            info = ydl.extract_info(url, download=True)
                            if not info:
                                raise Exception("Could not download audio")
                            downloaded_file = os.path.join(output_path if output_path else '.', ydl.prepare_filename(info))
                            # Handle potential extension change after audio processing
                            if not os.path.exists(downloaded_file) and downloaded_file.endswith('.webm'):
                                downloaded_file = downloaded_file.replace('.webm', '.mp3')
                            logger.info(f"Successfully downloaded restricted audio with alternative settings to {downloaded_file}")
                            return downloaded_file
                    except Exception as restricted_error:
                        # Provide a user-friendly error message
                        raise Exception("This video has restrictions (age, privacy, or requires login) and cannot be downloaded publicly.")
                
                logger.info("Trying without cookies (anonymous access)")
                
                # Try one more time without cookies for non-restricted videos
                try:
                    options.pop('cookiefile', None)
                    with yt_dlp.YoutubeDL(options) as ydl:
                        info = ydl.extract_info(url, download=True)
                        if not info:
                            raise Exception("Could not download audio")
                        downloaded_file = os.path.join(output_path if output_path else '.', ydl.prepare_filename(info))
                        # Handle potential extension change
                        if not os.path.exists(downloaded_file) and downloaded_file.endswith('.webm'):
                            downloaded_file = downloaded_file.replace('.webm', '.mp3')
                        logger.info(f"Successfully downloaded audio anonymously to {downloaded_file}")
                        return downloaded_file
                except Exception as anonymous_error:
                    # Check for specific error patterns in the second attempt as well
                    error_str = str(anonymous_error).lower()
                    if any(restriction in error_str for restriction in [
                        'sign in to confirm', 'age-restricted', 'private video', 
                        'this video is not available', 'video unavailable', 'video is private'
                    ]):
                        # Provide a user-friendly error message
                        raise Exception("This video has restrictions (age, privacy, or requires login) and cannot be downloaded publicly.")
                    else:
                        raise Exception(f"Failed to download audio: {str(anonymous_error)}")
                
        except Exception as e:
            logger.error(f"Error downloading audio: {str(e)}")
            raise