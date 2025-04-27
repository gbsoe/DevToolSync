import os
import logging
import datetime
import time
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory, send_file, make_response, Response
from werkzeug.utils import secure_filename
import urllib.parse
from sqlalchemy import func

# Import our modules
from youtube_link_utils import get_video_info as get_yt_info, generate_clipto_url, generate_download_file_url, get_video_id
from downloader import YoutubeDownloader
from cache_manager import CacheManager
from models import db, Download, Statistics

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "youtube_downloader_secret")

# Configure database
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
logger.debug(f"Database URL configured: {database_url is not None}")

# Initialize the database
db.init_app(app)

# Create database tables if they don't exist
with app.app_context():
    db.create_all()
    logger.debug("Database tables created")

# Initialize the cache manager
cache_manager = CacheManager(max_size=50)  # Store info for up to 50 videos

@app.route('/')
def index():
    """Main page with the video download form"""
    # Record site visit for statistics
    Statistics.record_visit()
    return render_template('index.html')

@app.route('/direct-url-process')
def direct_url_process():
    """Process a YouTube URL directly and redirect to watch page (2-page workflow)"""
    # Get parameters from the form
    url = request.args.get('url', '')
    format_id = request.args.get('format', '22')  # Default to 720p
    
    # Set download type based on format (140 is audio format)
    download_type = 'audio' if format_id == '140' else 'video'
    
    if not url:
        flash('Please enter a valid YouTube URL', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Extract video ID
        video_id = get_video_id(url)
        if not video_id:
            flash('Invalid YouTube URL. Please check and try again.', 'danger')
            return redirect(url_for('index'))
        
        # Log the direct processing
        logger.info(f"Direct URL processing: {url}, format: {format_id}, type: {download_type}")
        
        # Redirect directly to the watch page (this creates the 2-page experience)
        return redirect(url_for('watch_video', v=video_id, format=format_id, type=download_type))
    except Exception as e:
        logger.error(f"Error processing URL: {str(e)}")
        flash(f"Error processing URL: {str(e)}", 'danger')
        return redirect(url_for('index'))
    
@app.route('/direct-download')
def direct_download():
    """Show download page with direct download button"""
    video_id = request.args.get('v', '')
    format_id = request.args.get('format', '18')  # Default to medium quality
    download_type = request.args.get('type', 'video')  # Default to video
    timestamp = request.args.get('_t', '')  # Timestamp to avoid caching
    skip_redirect = request.args.get('skip_redirect', 'false') == 'true'  # Skip the redirection to direct URL
    
    if not video_id:
        flash("No video ID provided", 'danger')
        return redirect('/')
    
    try:
        # Create a YouTube URL from the video ID
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Log download attempt for debugging
        logger.info(f"Attempting direct download for video: {video_id}, format: {format_id}, type: {download_type}")
        
        # Initialize the YouTube downloader
        downloader = YoutubeDownloader()
        
        # Get video info to help set the filename before attempting to get direct URL
        # This ensures we have a good title even if the format is changed
        try:
            video_info = get_yt_info(url)
            title = video_info.get('title', f'youtube_{video_id}')
        except Exception as info_error:
            logger.warning(f"Error getting video info: {str(info_error)}")
            title = f'youtube_{video_id}'
        
        # Clean up the title for use as a filename
        safe_title = secure_filename(title).replace(' ', '_')
        
        # Try to get the direct download URL with retries for different formats
        direct_url = None
        error_message = None
        
        try:
            # First try with the requested format
            direct_url = downloader.get_direct_url(url, format_id, download_type)
            logger.info(f"Got direct URL with requested format: {format_id}")
        except Exception as format_error:
            logger.warning(f"Error getting direct URL with format {format_id}: {str(format_error)}")
            error_message = str(format_error)
            
            # Try with fallback formats
            try:
                if download_type == 'video':
                    # For video, try common fallback formats
                    fallback_formats = ['18', '22', '135', '136', 'best']
                else:
                    # For audio, try common fallback formats
                    fallback_formats = ['140', '251', '250', 'bestaudio']
                
                for fallback_format in fallback_formats:
                    if fallback_format != format_id:  # Skip the one we already tried
                        try:
                            logger.info(f"Trying fallback format: {fallback_format}")
                            direct_url = downloader.get_direct_url(url, fallback_format, download_type)
                            if direct_url:
                                logger.info(f"Got direct URL with fallback format: {fallback_format}")
                                break
                        except Exception as fallback_error:
                            logger.warning(f"Error with fallback format {fallback_format}: {str(fallback_error)}")
            except Exception as fallbacks_error:
                logger.error(f"Error trying fallback formats: {str(fallbacks_error)}")
        
        # If we couldn't get a direct URL, show an error
        if not direct_url:
            logger.error(f"Failed to get direct URL for video {video_id}: {error_message}")
            flash(f"Error: The requested format is not available. {error_message}", 'danger')
            return redirect(f'/watch?v={video_id}')
        
        # Set the appropriate extension
        extension = 'mp4' if download_type == 'video' else 'mp3'
        
        # If we're skipping the redirect, return the direct URL as JSON
        if skip_redirect:
            return jsonify({
                'direct_url': direct_url,
                'filename': f"{safe_title}.{extension}",
                'format': format_id,
                'type': download_type
            })
        
        # Get the correct format label
        format_label = ''
        if download_type == 'video':
            if format_id == '22':
                format_label = '720p HD Video (MP4)'
            elif format_id == '18':
                format_label = '360p Video (MP4)'
            else:
                format_label = 'Video'
        else:
            if format_id == '140':
                format_label = 'Audio (128kbps M4A)'
            elif format_id == '251':
                format_label = 'Audio (160kbps OPUS)'
            else:
                format_label = 'Audio'
        
        # Record download statistics
        Statistics.record_download(download_type)
        
        # Create download record with anonymized IP
        ip_address = request.remote_addr
        if ip_address:
            # Anonymize IP by removing last octet
            ip_parts = ip_address.split('.')
            if len(ip_parts) == 4:  # IPv4
                ip_address = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0"
            else:
                ip_address = "0.0.0.0"  # Fallback
        
        # Add download record
        Download.add_download(
            url=url,
            video_title=title,
            format_type=download_type,
            quality=format_id,
            status="completed",
            ip_address=ip_address
        )
        
        # Get video thumbnail
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        # Render the direct download page with the direct URL
        return render_template('direct_download.html',
                              title=title,
                              thumbnail=thumbnail_url,
                              direct_url=direct_url,
                              filename=f"{safe_title}.{extension}",
                              format=format_label,
                              download_type=download_type,
                              video_id=video_id)
        
    except Exception as e:
        logger.error(f"Error generating direct download: {str(e)}")
        flash(f"Error: Unable to download video. {str(e)}", 'danger')
        # Redirect to the watch page if we have the video ID, otherwise to home
        if video_id:
            return redirect(f'/watch?v={video_id}')
        else:
            return redirect('/')

@app.route('/faq')
def faq():
    """Frequently Asked Questions page"""
    return render_template('faq.html', 
                          title='YouTube Downloader FAQ - Answers to Common Questions About Downloading Videos',
                          description='Find answers to frequently asked questions about downloading YouTube videos and converting videos to MP3 using our free online tool.')

@app.route('/video_info', methods=['POST'])
def get_video_info():
    """Get information about a YouTube video"""
    # Log raw request data for debugging
    logger.info(f"Received video_info request. Form data: {request.form}")
    logger.info(f"Request content type: {request.content_type}")
    
    # Try to get URL from various sources in the request
    url = request.form.get('url', '')
    
    if not url:
        # If not in form data, try to get from JSON data
        if request.is_json:
            data = request.get_json()
            url = data.get('url', '')
        
        # If still not found, try to get from raw data
        if not url and request.data:
            try:
                # Try to parse as URL-encoded data
                from urllib.parse import parse_qs
                parsed = parse_qs(request.data.decode('utf-8'))
                url = parsed.get('url', [''])[0]
            except Exception as parse_error:
                logger.error(f"Error parsing request data: {str(parse_error)}")
    
    logger.info(f"Extracted URL: {url}")
    
    if not url:
        return jsonify({'error': 'Please enter a valid YouTube URL'}), 400
    
    try:
        # Check if this URL is in cache
        video_info = cache_manager.get_cache(url)
        
        if not video_info:
            # Not in cache, get the info
            video_info = get_yt_info(url)
            cache_manager.add_to_cache(url, video_info)
        
        # Make sure this is a JSON-serializable dictionary
        if not isinstance(video_info, dict):
            video_info = {
                'title': 'Unknown Video',
                'is_playlist': False,
                'video_formats': [
                    {'format_id': '18', 'format': '360p (mp4)', 'ext': 'mp4', 'resolution': '360p'}
                ],
                'audio_formats': [
                    {'format_id': '140', 'format': 'Audio (128kbps m4a)', 'ext': 'm4a', 'abr': '128kbps'}
                ]
            }
        
        # Log successful response
        logger.info(f"Successfully got video info for {url}")
        
        # Add additional headers to ensure content type is correct
        response = jsonify(video_info)
        response.headers['Content-Type'] = 'application/json'
        return response
    
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download_video():
    """Generate a direct download link for a YouTube video or audio"""
    url = request.form.get('url', '')
    format_id = request.form.get('format', 'best')
    download_type = request.form.get('type', 'video')
    playlist = request.form.get('playlist', 'false') == 'true'
    video_title = request.form.get('title', 'Unknown Video')
    
    logger.info(f"Received download request - URL: {url}, Format: {format_id}, Type: {download_type}")
    
    if not url:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Please enter a valid YouTube URL'}), 400
        else:
            flash('Please enter a valid YouTube URL', 'danger')
            return redirect(url_for('index'))
    
    try:
        # Extract video ID for redirection to watch page
        video_id = get_video_id(url)
        if not video_id:
            raise ValueError("Could not extract video ID from the URL")
            
        # Get client IP (anonymize it for privacy)
        ip_address = request.remote_addr
        if ip_address:
            # Anonymize IP by removing last octet
            ip_parts = ip_address.split('.')
            if len(ip_parts) == 4:  # IPv4
                ip_address = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0"
            else:
                ip_address = "0.0.0.0"  # Fallback
        
        # Create download record in the database
        download_record = Download.add_download(
            url=url,
            video_title=video_title,
            format_type=download_type,
            quality=format_id,
            status="completed",  # Mark as completed immediately since we're just generating a link
            ip_address=ip_address
        )
        
        # Record download in statistics
        Statistics.record_download(download_type)
        
        # Generate direct download URL for both cases
        direct_url = generate_clipto_url(url, format_id, download_type)
        watch_url = f'/watch?v={video_id}&format={format_id}&type={download_type}'
        
        # Check if this is an AJAX request based on multiple criteria
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            request.headers.get('Accept', '').startswith('application/json')
        )
        
        if is_ajax:
            # Return JSON response
            return jsonify({
                'status': 'complete',
                'download_url': direct_url,
                'message': 'Download link generated',
                'watch_url': watch_url
            })
        else:
            # Redirect to the custom download page
            return redirect(watch_url)
    
    except Exception as e:
        logger.error(f"Error generating download link: {str(e)}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': str(e)}), 500
        else:
            flash(f"Error: {str(e)}", 'danger')
            return redirect(url_for('index'))

@app.route('/watch')
def watch_video():
    """Display video download page similar to the screenshot"""
    video_id = request.args.get('v', '')
    url = request.args.get('url', '')
    format_id = request.args.get('format', '18')  # Default to medium quality
    download_type = request.args.get('type', 'video')  # Default to video
    
    # If we got a direct URL instead of video ID, extract the video ID
    if url and not video_id:
        try:
            video_id = get_video_id(url)
            logger.info(f"Extracted video ID from URL: {video_id}")
        except Exception as e:
            logger.error(f"Failed to extract video ID from URL: {str(e)}")
            flash("Invalid YouTube URL. Please check and try again.", "danger")
            return redirect('/')
    
    if not video_id:
        return redirect('/')
    
    # Reconstruct a YouTube URL
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        # Get video information with retry for rate limiting
        try:
            video_info = get_yt_info(url)
        except Exception as info_error:
            error_msg = str(info_error).lower()
            # Check if the error is related to rate limiting
            if "rate" in error_msg and ("exceeded" in error_msg or "limit" in error_msg):
                logger.warning("Rate limit detected, waiting before retry...")
                # Wait for a moment (give YouTube API a chance to reset)
                time.sleep(2)
                # Try again one more time
                video_info = get_yt_info(url)
            else:
                # Re-raise the original error if it's not a rate limit issue
                raise
        
        # Generate direct download URLs for all formats
        video_formats = []
        if video_info.get('video_formats'):
            for format in video_info['video_formats']:
                format_size = format.get('filesize', 0)
                size_str = format_readable_size(format_size)
                
                video_formats.append({
                    'format': format.get('format', f"Video {format.get('resolution', '360p')}"),
                    'format_id': format.get('format_id', '18'),
                    'size': size_str,
                    'download_url': generate_download_file_url(url, format.get('format_id', '18'))
                })
        
        audio_formats = []
        if video_info.get('audio_formats'):
            for format in video_info['audio_formats']:
                format_size = format.get('filesize', 0)
                size_str = format_readable_size(format_size)
                
                audio_formats.append({
                    'format': format.get('format', f"Audio {format.get('abr', '128kbps')}"),
                    'format_id': format.get('format_id', '140'),
                    'size': size_str,
                    'download_url': generate_download_file_url(url, format.get('format_id', '140'), 'audio')
                })
        
        # Format the video duration
        duration_str = "0:00"
        if video_info.get('duration'):
            minutes, seconds = divmod(video_info['duration'], 60)
            hours, minutes = divmod(minutes, 60)
            if hours > 0:
                duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration_str = f"{minutes}:{seconds:02d}"
        
        # Get the primary download URL for the requested format
        if download_type == 'audio':
            primary_download_url = generate_download_file_url(url, format_id, 'audio')
        else:
            primary_download_url = generate_download_file_url(url, format_id)
            
        # Create an embed URL (can't directly embed YouTube videos, but we'll use a workaround)
        embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1&controls=1&rel=0"
        
        return render_template('download.html',
                              title=video_info.get('title', 'YouTube Video'),
                              video_id=video_id,
                              embed_url=embed_url,
                              download_url=primary_download_url,
                              duration=duration_str,
                              video_formats=video_formats,
                              audio_formats=audio_formats)
                              
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Error preparing download page: {error_msg}")
        
        # Provide a more user-friendly message for rate limiting
        if "rate" in error_msg and ("exceeded" in error_msg or "limit" in error_msg):
            flash("YouTube rate limit exceeded. Please wait a moment and try again.", 'warning')
        else:
            flash(f"Error: {str(e)}", 'danger')
            
        return redirect('/')
        
def format_readable_size(size_bytes):
    """Convert bytes to a human-readable format"""
    if size_bytes is None or size_bytes == 0:
        return "Unknown size"
        
    # Define units and their thresholds
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    unit_index = 0
    
    # Convert to larger units as needed
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    # Format with appropriate precision
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"

@app.route('/error')
def error_page():
    """Display error page"""
    error = request.args.get('error', 'An unknown error occurred')
    return render_template('error.html', error=error)

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"Server error: {str(e)}")
    return render_template('error.html', error='Server error occurred'), 500

@app.route('/robots.txt')
def robots():
    """Serve robots.txt file"""
    return send_from_directory('static', 'robots.txt')

@app.route('/sitemap.xml')
def sitemap():
    """Serve sitemap.xml file"""
    return send_from_directory('static', 'sitemap.xml')
    
@app.route('/process-download')
def process_download():
    """Server-side handler for downloading YouTube videos"""
    url = request.args.get('url', '')
    filename = request.args.get('filename', 'youtube_video.mp4')
    
    if not url:
        flash("No URL provided for download", 'danger')
        return redirect('/')
        
    try:
        logger.info(f"Processing direct download for URL: {url[:50]}...")
        
        # If it's a YouTube direct URL, we need to fetch it through our downloader
        if 'youtube.com' in url or 'youtu.be' in url:
            # Initialize the YouTube downloader
            downloader = YoutubeDownloader()
            
            # Try to extract video ID and format from the URL
            video_id = get_video_id(url)
            if not video_id:
                # If we can't extract from URL, assume it's a direct streaming URL
                logger.info("URL appears to be a direct streaming URL, passing through")
            else:
                logger.info(f"Extracted video ID: {video_id}, attempting to get direct URL")
                # Determine if it's audio or video based on filename
                download_type = 'audio' if filename.lower().endswith(('.mp3', '.m4a', '.opus', '.ogg')) else 'video'
                
                # Try to pass through our downloader to get the real streaming URL
                url = downloader.get_direct_url(url, 'best', download_type)
        
        # Create a proxy request to the target URL
        logger.info(f"Fetching content from: {url[:50]}...")
        
        # Make a streaming request to the source
        response = requests.get(
            url, 
            stream=True, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.youtube.com/'
            }
        )
        
        # Get content type from response or guess from filename
        content_type = response.headers.get('Content-Type')
        if not content_type or 'text/html' in content_type:
            # Try to guess content type from filename
            if filename.lower().endswith('.mp4'):
                content_type = 'video/mp4'
            elif filename.lower().endswith('.mp3'):
                content_type = 'audio/mpeg'
            elif filename.lower().endswith('.m4a'):
                content_type = 'audio/mp4'
            elif filename.lower().endswith('.webm'):
                content_type = 'video/webm'
            else:
                content_type = 'application/octet-stream'
        
        # Create a flask response with streaming content
        flask_response = Response(
            response.iter_content(chunk_size=4096),
            content_type=content_type
        )
        
        # Add content-disposition header to force download with the specified filename
        flask_response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Pass through content length if available
        if 'Content-Length' in response.headers:
            flask_response.headers['Content-Length'] = response.headers['Content-Length']
        
        # Record download statistics
        Statistics.record_download('video' if content_type.startswith('video') else 'audio')
        
        logger.info(f"Sending file: {filename} with content type: {content_type}")
        return flask_response
        
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Error processing download: {error_msg}")
        
        # Provide a more user-friendly message for bot detection errors
        if "sign in to confirm you're not a bot" in error_msg or "bot" in error_msg:
            flash("YouTube has detected automated access. Please try again in a few moments as the system refreshes authentication.", 'warning')
            # Force refresh cookies on bot detection errors
            from cookie_manager import refresh_cookies
            refresh_cookies()
        elif "rate" in error_msg and ("exceeded" in error_msg or "limit" in error_msg):
            flash("YouTube rate limit exceeded. Please wait a moment and try again.", 'warning')
        else:
            flash(f"Error: {str(e)}", 'danger')
            
        return redirect('/')

@app.route('/google07df394c40c0da6f.html')
def google_verification():
    """Serve Google verification file"""
    return send_file('google07df394c40c0da6f.html')

@app.route('/sw.js')
def service_worker():
    """Serve the MonetAG service worker JavaScript file"""
    response = send_file('sw.js')
    # Set appropriate headers for a service worker
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response
    
@app.route('/download-file')
def download_file():
    """Direct file download endpoint - this serves the actual file content instead of HTML"""
    # Get parameters
    video_id = request.args.get('v', '')
    format_id = request.args.get('format', '18')  # Default to 360p video
    download_type = request.args.get('type', 'video')
    
    if not video_id:
        flash("No video ID provided", "danger")
        return redirect('/')
    
    # Create YouTube URL
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        # Initialize downloader
        downloader = YoutubeDownloader()
        
        # Get direct URL to the YouTube content
        logger.info(f"Getting direct URL for: {url} with format: {format_id}, type: {download_type}")
        direct_url = downloader.get_direct_url(url, format_id, download_type)
        
        if not direct_url:
            flash("Could not retrieve direct download URL", "danger")
            return redirect('/')
            
        # Try to get video info to set a good filename
        try:
            video_info = get_yt_info(url)
            title = video_info.get('title', f'youtube_{video_id}')
        except Exception as e:
            logger.warning(f"Error getting video info: {str(e)}")
            title = f'youtube_{video_id}'
        
        # Make the title safe for a filename
        safe_title = secure_filename(title).replace(' ', '_')
        
        # Set the appropriate extension and MIME type
        if download_type == 'audio':
            extension = '.mp3'
            mime_type = 'audio/mpeg'
        else:
            extension = '.mp4'
            mime_type = 'video/mp4'
            
        # Create proper filename
        filename = f"{safe_title}{extension}"
        
        logger.info(f"Making request to: {direct_url[:50]}...")
        
        # Create a streaming response with proper headers to force download
        response = requests.get(
            direct_url, 
            stream=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.youtube.com/'
            }
        )
        
        # Check if the request was successful
        if response.status_code != 200:
            flash(f"Error: Could not access video content (HTTP {response.status_code})", "danger")
            return redirect('/')
        
        # Get content type from response
        content_type = response.headers.get('Content-Type', mime_type)
        
        # Create Flask response object
        flask_response = Response(
            response.iter_content(chunk_size=8192),
            content_type=content_type
        )
        
        # Set headers to force download with the proper filename
        flask_response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Add content length if available
        if 'Content-Length' in response.headers:
            flask_response.headers['Content-Length'] = response.headers['Content-Length']
        
        # Record download statistics
        Statistics.record_download(download_type)
        
        # Return the streaming response
        logger.info(f"Streaming direct download for {filename}")
        return flask_response
        
    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Error in download_file: {error_msg}")
        
        # Provide a more user-friendly message for bot detection errors
        if "sign in to confirm you're not a bot" in error_msg or "bot" in error_msg:
            flash("YouTube has detected automated access. Please try again in a few moments as the system refreshes authentication.", 'warning')
            # Force refresh cookies on bot detection errors
            from cookie_manager import refresh_cookies
            refresh_cookies()
        elif "rate" in error_msg and ("exceeded" in error_msg or "limit" in error_msg):
            flash("YouTube rate limit exceeded. Please wait a moment and try again.", 'warning')
        else:
            flash(f"Error: {str(e)}", 'danger')
            
        return redirect(f'/watch?v={video_id}')

@app.route('/privacy')
def privacy_policy():
    """Privacy Policy page"""
    return render_template('privacy.html')

@app.route('/disclaimer')
def disclaimer():
    """Disclaimer and Terms of Service page"""
    return render_template('disclaimer.html')

@app.route('/donate')
def donate():
    """Donation page"""
    return render_template('donate.html')

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard with download statistics"""
    # This should have proper authentication in production
    
    # Get overall statistics
    current_date = datetime.datetime.utcnow().date()
    last_week = current_date - datetime.timedelta(days=7)
    
    # Get all stats data
    all_stats = Statistics.query.all()
    
    # Calculate total statistics
    total_visits = sum(stat.visits for stat in all_stats)
    total_downloads = sum(stat.downloads for stat in all_stats)
    video_downloads = sum(stat.video_downloads for stat in all_stats)
    audio_downloads = sum(stat.audio_downloads for stat in all_stats)
    
    # Prepare chart data for last 7 days
    last_7_days = []
    for i in range(6, -1, -1):
        day = current_date - datetime.timedelta(days=i)
        last_7_days.append(day)
    
    # Format dates and get data for chart
    date_labels = [day.strftime('%b %d') for day in last_7_days]
    visits_data = []
    downloads_data = []
    
    for day in last_7_days:
        stat = Statistics.query.filter_by(date=day).first()
        visits_data.append(stat.visits if stat else 0)
        downloads_data.append(stat.downloads if stat else 0)
    
    # Get popular downloads (using ORM instead of raw SQL)
    popular_downloads = []
    try:
        # Check if we have any completed downloads first
        if db.session.query(Download.id).filter_by(status='completed').first() is not None:
            # Use ORM to group and count downloads
            from sqlalchemy import func
            popular_downloads_query = (
                db.session.query(
                    Download.video_title,
                    Download.format_type,
                    Download.quality,
                    func.count(Download.id).label('count')
                )
                .filter(Download.status == 'completed')
                .group_by(Download.video_title, Download.format_type, Download.quality)
                .order_by(func.count(Download.id).desc())
                .limit(10)
            )
            popular_downloads = popular_downloads_query.all()
    except Exception as e:
        logger.error(f"Error getting popular downloads: {str(e)}")
        popular_downloads = []
    
    # Get recent downloads
    recent_downloads = []
    try:
        recent_downloads = Download.query.order_by(Download.created_at.desc()).limit(20).all()
    except Exception as e:
        logger.error(f"Error getting recent downloads: {str(e)}")
        recent_downloads = []
    
    return render_template(
        'admin.html',
        stats={
            'total_visits': total_visits,
            'total_downloads': total_downloads,
            'video_downloads': video_downloads,
            'audio_downloads': audio_downloads
        },
        chart_data={
            'labels': date_labels,
            'visits': visits_data,
            'downloads': downloads_data
        },
        popular_downloads=popular_downloads,
        recent_downloads=recent_downloads
    )

# SEO-optimized metadata for page titles and descriptions
@app.context_processor
def inject_seo_metadata():
    """Inject SEO metadata for templates"""
    return {
        'default_title': 'YouTube Downloader - Download Videos and Audio in High Quality | Free Online Tool',
        'default_description': 'Free YouTube video downloader that allows you to download YouTube videos and audio in multiple formats and qualities. Convert YouTube videos to MP3, MP4, and more.',
        'current_year': time.strftime("%Y")
    }

# No cleanup needed as we don't download files locally anymore
