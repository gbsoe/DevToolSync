
# YouTube Downloader Setup Instructions

## Initial Setup

1. Create a new Repl
   - Go to https://replit.com
   - Click "Create Repl"
   - Choose "Python" as the template
   - Name it "youtube-downloader"
   - Click "Create Repl"

2. Configure Dependencies
   - Create `pyproject.toml` with these exact dependencies:
   ```toml
   [project]
   name = "repl-nix-workspace"
   version = "0.1.0"
   description = "Add your description here"
   requires-python = ">=3.11"
   dependencies = [
       "email-validator>=2.2.0",
       "ffmpeg>=1.4",
       "flask>=3.1.0",
       "flask-sqlalchemy>=3.1.1",
       "gunicorn>=23.0.0",
       "psycopg2-binary>=2.9.10",
       "pytube>=15.0.0",
       "requests>=2.32.3",
       "werkzeug>=3.1.3",
       "yt-dlp>=2025.3.31",
   ]
   ```

3. Create Directory Structure
   ```
   youtube-downloader/
   ├── static/
   │   ├── css/
   │   │   ├── custom.css
   │   │   └── style.css
   │   ├── img/
   │   │   └── youtube-downloader-thumbnail.svg
   │   ├── js/
   │   │   └── script.js
   │   ├── robots.txt
   │   └── sitemap.xml
   ├── templates/
   │   ├── admin.html
   │   ├── disclaimer.html
   │   ├── donate.html
   │   ├── error.html
   │   ├── faq.html
   │   ├── index.html
   │   ├── layout.html
   │   └── privacy.html
   ├── app.py
   ├── cache_manager.py
   ├── downloader.py
   ├── main.py
   └── models.py
   ```

4. Core Files Setup
   - Create all files listed above
   - Copy exact content from source files for:
     - app.py (2,431 lines)
     - downloader.py (1,183 lines)
     - main.py (6 lines)
     - All template files in /templates
     - All static files in /static

5. Database Configuration
   - PostgreSQL is used for data storage
   - Database URL should be configured through environment variables
   - Default tables will be auto-created on first run

6. Environment Variables
   Required variables:
   - DATABASE_URL: PostgreSQL connection string
   - SESSION_SECRET: For Flask session security

7. Running the Application
   The application uses gunicorn and should be started with:
   ```bash
   gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
   ```

## File Content Details

### main.py
```python
from app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```

### models.py
Must include:
- Download class for tracking downloads
- Statistics class for site metrics
- SQLAlchemy models for both classes
- Methods for:
  - Recording visits
  - Tracking downloads
  - Updating download status
  - Calculating statistics

### Configuration Requirements

1. Port Configuration
   - Application runs on port 5000
   - External port maps to 80

2. Security Settings
   - Rate limiting implemented in downloader.py
   - Anti-bot measures in place
   - IP anonymization for privacy

3. File Handling
   - Temporary directory created at runtime
   - Automatic cleanup after downloads
   - ZIP file creation for playlists

## Features to Verify

1. Video Downloads
   - Multiple quality options (240p to 4K)
   - Progress tracking
   - Format selection
   - Playlist support

2. Audio Extraction
   - Multiple formats (MP3, M4A)
   - Quality options
   - Automatic conversion

3. User Interface
   - Mobile responsive design
   - Real-time progress updates
   - Error handling
   - Format selection interface

## Testing Checklist

1. Basic Functionality
   - [ ] Video info retrieval works
   - [ ] Single video download works
   - [ ] Playlist download works
   - [ ] Audio extraction works
   - [ ] Progress tracking works

2. Error Handling
   - [ ] Invalid URLs handled
   - [ ] Network errors handled
   - [ ] Rate limiting works
   - [ ] Anti-bot measures active

3. Database
   - [ ] Download tracking works
   - [ ] Statistics recording works
   - [ ] Clean up routines work

## Common Issues

1. FFmpeg Missing
   - System will fall back to alternate methods
   - Audio conversion may be limited

2. Database Connection
   - Ensure DATABASE_URL is properly set
   - Check PostgreSQL service is running

3. File Permissions
   - Temporary directory needs write access
   - Download directory needs write access

## Maintenance

1. Regular Tasks
   - Monitor error logs
   - Check download statistics
   - Update dependencies
   - Clear temporary files

2. Performance Monitoring
   - Watch database connections
   - Monitor download speeds
   - Check cache efficiency
   - Track API rate limits
