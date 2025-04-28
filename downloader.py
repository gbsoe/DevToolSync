import os
import logging
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
            'cookiefile': 'cookies.txt',
            'format_sort': [
                'res:1080p',
                'res:720p',
                'res:480p',
                'res:360p',
                'res:240p',
                'res:144p'
            ],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
                'Referer': 'https://www.youtube.com/'
            },
            'geo_bypass': True,
            'nocheckcertificate': True
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
            opts['ignoreerrors'] = True
            opts['skip_download'] = True
            opts['quiet'] = False  # Enable more detailed logging

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
                        alt_opts['ignoreerrors'] = True
                        alt_opts['skip_download'] = True
                        alt_opts['quiet'] = False
                        alt_opts['http_headers']['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
                        alt_opts['http_headers']['Referer'] = 'https://www.youtube.com/feed/trending'

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

    def download_video(self, url, output_path, format_id='18'):
        try:
            ensure_fresh_cookies()

            options = {
                **self.base_opts,
                'format': format_id,
                'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s')
            }

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = os.path.join(output_path, ydl.prepare_filename(info))
                logger.info(f"Successfully downloaded video to {downloaded_file}")
                return downloaded_file

        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise

    def get_direct_url(self, url, format_id, download_type='video'):
        try:
            ensure_fresh_cookies()

            format_string = format_id
            if download_type == 'audio':
                format_string = f"{format_id}/bestaudio"
            elif download_type == 'video':
                format_string = f"{format_id}/best[height<=720]/best"

            options = {
                **self.base_opts,
                'format': format_string,
                'skip_download': True,
            }

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise Exception("Could not retrieve video information")

                if 'url' in info:
                    logger.info(f"Found direct URL in info: {url[:30]}...")
                    return info['url']
                elif 'formats' in info:
                    logger.info(f"Available formats: {[f.get('format_id') for f in info['formats']]}")

                    for fmt in info['formats']:
                        if fmt.get('format_id') == format_id and 'url' in fmt:
                            logger.info(f"Found exact format match for {format_id}")
                            return fmt['url']

                    logger.warning(f"Format {format_id} not found, using best match")
                    return info['formats'][-1]['url']

                raise Exception("No suitable format found")

        except Exception as e:
            logger.error(f"Error getting direct URL: {str(e)}")
            raise

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