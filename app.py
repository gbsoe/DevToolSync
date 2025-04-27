import os
import logging
import datetime
import time
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory, send_file, make_response
from werkzeug.utils import secure_filename
import urllib.parse

# Import our modules
from youtube_link_utils import get_video_info as get_yt_info, generate_clipto_url, get_video_id
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
    
@app.route('/direct-download')
def direct_download():
    """Directly download a YouTube video or audio file"""
    video_id = request.args.get('v', '')
    format_id = request.args.get('format', '18')  # Default to medium quality
    download_type = request.args.get('type', 'video')  # Default to video
    timestamp = request.args.get('_t', '')  # Timestamp to avoid caching
    
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
        
        # Create appropriate headers for direct download
        # These headers will tell the browser this is a file download
        response = make_response(redirect(direct_url))
        response.headers['Content-Type'] = 'application/octet-stream'
        response.headers['Content-Disposition'] = f'attachment; filename="{safe_title}.{extension}"'
        
        # Log the success
        logger.info(f"Successfully generated direct download URL for {video_id}")
        
        # Return the response with proper headers to force download
        return response
        
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
    url = request.form.get('url', '')
    
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
    format_id = request.args.get('format', '18')  # Default to medium quality
    download_type = request.args.get('type', 'video')  # Default to video
    
    if not video_id:
        return redirect('/')
    
    # Reconstruct a YouTube URL
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        # Get video information
        video_info = get_yt_info(url)
        
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
                    'download_url': generate_clipto_url(url, format.get('format_id', '18'))
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
                    'download_url': generate_clipto_url(url, format.get('format_id', '140'), 'audio')
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
            primary_download_url = generate_clipto_url(url, format_id, 'audio')
        else:
            primary_download_url = generate_clipto_url(url, format_id)
            
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
        logger.error(f"Error preparing download page: {str(e)}")
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
