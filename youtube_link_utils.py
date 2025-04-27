import logging
import os
import re
import urllib.parse
from pytube import YouTube, Playlist

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_video_id(url):
    """Extract the YouTube video ID from a URL"""
    # Regular expressions to match YouTube URL patterns
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',  # Standard and shortened YouTube URLs
        r'(?:embed\/|v\/|youtu.be\/)([0-9A-Za-z_-]{11})',  # Embedded and youtu.be URLs
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})'  # Standard watch URL
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def is_playlist(url):
    """Check if the URL is a YouTube playlist"""
    return 'list=' in url or 'playlist' in url

def get_direct_video_url(video_id, itag):
    """Generate a direct download URL using YouTube's video ID and itag (format)"""
    base_url = "https://www.youtube.com/watch"
    params = {
        'v': video_id,
        'itag': itag
    }
    direct_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return direct_url

def get_video_info(url):
    """Get video information using pytube library"""
    try:
        logger.info(f"Getting video info for: {url}")
        
        # Check if it's a playlist
        if is_playlist(url):
            playlist = Playlist(url)
            # Get some sample videos from the playlist (up to first 5)
            videos = []
            for video_url in playlist.video_urls[:5]:
                try:
                    yt = YouTube(video_url)
                    videos.append({
                        'title': yt.title,
                        'thumbnail': yt.thumbnail_url,
                        'duration': yt.length
                    })
                except Exception as e:
                    logger.warning(f"Could not fetch info for playlist video: {str(e)}")
            
            return {
                'is_playlist': True,
                'playlist_title': playlist.title,
                'playlist_count': len(playlist.video_urls),
                'sample_videos': videos,
                'formats': get_default_formats(url, sample=True)
            }
        else:
            # Single video
            yt = YouTube(url)
            
            # Get available streams and formats
            streams = yt.streams.filter(progressive=True).order_by('resolution').desc()
            video_formats = []
            
            for stream in streams:
                if stream.includes_video_track and stream.includes_audio_track:
                    video_formats.append({
                        'format_id': stream.itag,
                        'format': f"{stream.resolution} ({stream.mime_type.split('/')[1]})",
                        'filesize': stream.filesize,
                        'ext': stream.mime_type.split('/')[1],
                        'resolution': stream.resolution
                    })
            
            # Audio formats
            audio_streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
            audio_formats = []
            
            for stream in audio_streams:
                audio_formats.append({
                    'format_id': stream.itag,
                    'format': f"Audio ({stream.abr} {stream.mime_type.split('/')[1]})",
                    'filesize': stream.filesize,
                    'ext': stream.mime_type.split('/')[1],
                    'abr': stream.abr
                })
            
            return {
                'is_playlist': False,
                'title': yt.title,
                'channel': yt.author,
                'thumbnail': yt.thumbnail_url,
                'duration': yt.length,
                'views': yt.views,
                'video_formats': video_formats,
                'audio_formats': audio_formats
            }
            
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}")
        raise Exception(f"Could not retrieve video information: {str(e)}")

def get_default_formats(url, sample=False):
    """Generate default format options for video or playlist"""
    # Create standard format options when we can't get actual formats
    video_formats = [
        {'format_id': '22', 'format': '720p (mp4)', 'ext': 'mp4', 'resolution': '720p'},
        {'format_id': '18', 'format': '360p (mp4)', 'ext': 'mp4', 'resolution': '360p'},
    ]
    
    audio_formats = [
        {'format_id': '140', 'format': 'Audio (128kbps m4a)', 'ext': 'm4a', 'abr': '128kbps'},
        {'format_id': '251', 'format': 'Audio (160kbps opus)', 'ext': 'opus', 'abr': '160kbps'},
    ]
    
    return {
        'video_formats': video_formats,
        'audio_formats': audio_formats
    }

def generate_clipto_url(youtube_url, format_id, download_type='video'):
    """Generate a Clipto-style direct download URL"""
    video_id = get_video_id(youtube_url)
    if not video_id:
        raise ValueError("Invalid YouTube URL")
    
    # Base Clipto-style URL pattern
    if download_type == 'audio':
        # For audio downloads
        return f"https://yt.youtubeupdated.com/{video_id}/{format_id}"
    else:
        # For video downloads
        return f"https://yt.youtubeupdated.com/{video_id}/{format_id}"