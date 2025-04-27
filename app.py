import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash
import pytube
from urllib.parse import quote

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "youtube_downloader_secret")

@app.context_processor
def inject_seo_metadata():
    """Inject SEO metadata for templates"""
    return {
        'default_title': 'YouTube Downloader - Free Online Tool to Download Videos',
        'default_description': 'Download YouTube videos and audio with our free online tool. No registration required.',
        'current_year': 2025  # Updated each year
    }

@app.route('/')
def index():
    """Main page with the video download form"""
    return render_template('index.html')

@app.route('/info', methods=['POST'])
def get_video_info():
    """Get information about a YouTube video using pytube"""
    url = request.form.get('url', '')
    
    if not url:
        flash('Please enter a valid YouTube URL')
        return redirect(url_for('index'))
    
    try:
        # Create a PyTube object
        yt = pytube.YouTube(url)
        
        # Get video title
        title = yt.title
        
        # Get all progressive streams (combined audio and video)
        streams = yt.streams.filter(progressive=True).order_by('resolution').desc()
        
        # Format streams for template
        formatted_streams = []
        for stream in streams:
            formatted_streams.append({
                'itag': stream.itag,
                'mime_type': stream.mime_type,
                'resolution': stream.resolution,
                'file_size': f"{stream.filesize_mb:.1f} MB"
            })
        
        return render_template('streams.html', 
                               title=title, 
                               streams=formatted_streams, 
                               original_url=url)
    
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}")
        flash(f"Error: {str(e)}")
        return redirect(url_for('index'))

@app.route('/download')
def download():
    """Redirect to direct video URL"""
    url = request.args.get('url', '')
    itag = request.args.get('itag', '')
    
    if not url or not itag:
        flash('Missing URL or format selection')
        return redirect(url_for('index'))
    
    try:
        # Create a PyTube object
        yt = pytube.YouTube(url)
        
        # Get the specific stream by itag
        stream = yt.streams.get_by_itag(int(itag))
        
        if not stream:
            flash('Selected format is not available')
            return redirect(url_for('index'))
        
        # Get the direct URL to the video
        direct_url = stream.url
        
        # Redirect to the direct URL
        return redirect(direct_url)
    
    except Exception as e:
        logger.error(f"Error downloading video: {str(e)}")
        flash(f"Error: {str(e)}")
        return redirect(url_for('index'))

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"Server error: {str(e)}")
    return render_template('error.html', error='Server error occurred'), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)