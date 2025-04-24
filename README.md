# YouTube Downloader Application

A Flask-based web application that allows users to download YouTube videos and audio in various formats with anti-bot measures and efficient processing.

![YouTube Downloader](static/img/youtube-downloader-thumbnail.svg)

## Features

- **Multi-format Video Download**: Download videos in various resolutions (240p to 4K)
- **Audio Extraction**: Extract audio in multiple formats (MP3, M4A, etc.)
- **Playlist Support**: Download entire YouTube playlists at once
- **Real-time Progress Tracking**: Monitor download progress with a visual progress bar
- **Responsive Design**: Works on desktop and mobile devices
- **Anti-bot Protection**: Implements measures to prevent abuse
- **Caching System**: Reduces API calls to YouTube for better performance

## Technology Stack

- **Backend**: Python, Flask
- **Database**: PostgreSQL
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Video Processing**: yt-dlp with ffmpeg fallback to pytube

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL
- ffmpeg (optional, for advanced audio processing)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/youtube-downloader.git
   cd youtube-downloader
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   export DATABASE_URL=postgresql://username:password@localhost/youtube_downloader
   export SESSION_SECRET=your_secret_key
   ```

4. Initialize the database:
   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

5. Run the application:
   ```bash
   python main.py
   ```

## Usage

1. Enter a YouTube URL in the input field
2. Click "Get Video Info" to retrieve available formats
3. Select your preferred format (video quality or audio)
4. Click "Download" and wait for the process to complete
5. Click the download link to save the file

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main page with download form |
| `/video_info` | POST | Get information about a video |
| `/download` | POST | Start a download |
| `/download_status/<id>` | GET | Check download status |
| `/get_file/<id>` | GET | Download completed file |
| `/faq` | GET | Frequently asked questions |
| `/privacy` | GET | Privacy policy |
| `/disclaimer` | GET | Terms of service |
| `/donate` | GET | Donation page |
| `/admin` | GET | Admin dashboard (requires authentication) |

## Configuration Options

The application can be configured through environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `SESSION_SECRET`: Secret key for session management
- `MAX_DOWNLOADS_PER_HOUR`: Limit downloads per IP (default: 10)
- `DOWNLOAD_EXPIRY_HOURS`: Hours before downloads are cleaned up (default: 24)
- `ENABLE_PLAYLIST`: Enable/disable playlist downloads (default: True)

## Architecture

The application follows a modular design:

- `app.py`: Main Flask application with routes
- `downloader.py`: YouTube downloader with anti-bot measures
- `cache_manager.py`: Caching system for video information
- `models.py`: Database models for tracking downloads
- `static/js/script.js`: Frontend functionality
- `templates/`: HTML templates

## Database Schema

### Downloads Table
- `id`: Primary key
- `url`: YouTube URL
- `video_title`: Title of the video
- `format_type`: Video or audio
- `quality`: Resolution or audio quality
- `file_size`: Size in bytes
- `download_time`: Processing time
- `status`: Download status
- `created_at`: Timestamp
- `ip_address`: User's IP (anonymized)

### Statistics Table
- `id`: Primary key
- `date`: Date
- `visits`: Page visits
- `downloads`: Total downloads
- `video_downloads`: Video downloads
- `audio_downloads`: Audio downloads

## Security Measures

- Rate limiting to prevent abuse
- IP anonymization for privacy
- Secure file handling with proper cleanup
- Input validation to prevent injection attacks
- Session management for user tracking

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for video extraction
- [pytube](https://github.com/pytube/pytube) as fallback downloader
- [Flask](https://flask.palletsprojects.com/) web framework
- [Bootstrap](https://getbootstrap.com/) for frontend styling