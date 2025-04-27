/**
 * Direct Download Helper
 * Handles direct downloads without redirecting to another page
 */

// Function to fetch a video or audio file directly
async function fetchAndDownloadFile(url, filename, onProgress) {
    try {
        // Show progress notification
        showProgressToast('Starting download...');
        
        // Extract information from the URL
        console.log("Fetching from URL:", url);
        
        // First, fetch the file headers to get content information
        const headResponse = await fetch(url, { 
            method: 'HEAD',
            mode: 'cors',
            credentials: 'omit',
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        });
        
        if (!headResponse.ok) {
            console.error(`HTTP error in HEAD request! Status: ${headResponse.status}`);
            showProgressToast('Trying alternative download method...');
            
            // If HEAD request fails, try direct file download without streaming
            forceDownloadUsingIframe(url, filename);
            return true;
        }
        
        // Get content-type to verify if it's a media file
        const contentType = headResponse.headers.get('content-type') || '';
        if (contentType.includes('text/html')) {
            console.warn("Content appears to be HTML, not media. Using alternative method.");
            forceDownloadUsingIframe(url, filename);
            return true;
        }
        
        // Get content-length if available
        const contentLength = headResponse.headers.get('content-length');
        const totalSize = contentLength ? parseInt(contentLength, 10) : 0;
        
        // Now fetch the actual content
        const response = await fetch(url, {
            mode: 'cors',
            credentials: 'omit',
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        });
        
        if (!response.ok) {
            console.error(`HTTP error in main request! Status: ${response.status}`);
            showProgressToast('Trying alternative download method...');
            
            // If request fails, try direct file download
            forceDownloadUsingIframe(url, filename);
            return true;
        }
        
        // Check content type again on the actual response
        const actualContentType = response.headers.get('content-type') || '';
        if (actualContentType.includes('text/html')) {
            console.warn("Response content is HTML, not media. Using alternative method.");
            forceDownloadUsingIframe(url, filename);
            return true;
        }
        
        // Get the response as a stream
        const reader = response.body.getReader();
        
        // Create a new ReadableStream from the response body
        const stream = new ReadableStream({
            async start(controller) {
                let receivedBytes = 0;
                
                try {
                    while (true) {
                        const { done, value } = await reader.read();
                        
                        if (done) {
                            controller.close();
                            break;
                        }
                        
                        // Update progress
                        receivedBytes += value.length;
                        const progress = totalSize ? Math.round((receivedBytes / totalSize) * 100) : 0;
                        
                        if (onProgress && typeof onProgress === 'function') {
                            onProgress(progress);
                        }
                        
                        // Update progress toast
                        updateProgressToast(progress);
                        
                        // Enqueue the chunk
                        controller.enqueue(value);
                    }
                } catch (error) {
                    controller.error(error);
                }
            }
        });
        
        // Create a response from the stream
        const newResponse = new Response(stream);
        
        // Get the blob from the response
        const blob = await newResponse.blob();
        
        // Create a download link and click it
        const downloadUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename || 'download';
        document.body.appendChild(a);
        a.click();
        
        // Clean up
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(downloadUrl);
            showSuccessToast('Download complete!');
        }, 100);
        
        return true;
    } catch (error) {
        console.error('Download failed:', error);
        showErrorToast(`Download failed: ${error.message}`);
        
        // Try the fallback method if streaming fails
        try {
            forceDownloadUsingIframe(url, filename);
            return true;
        } catch (fallbackError) {
            console.error('Fallback download failed:', fallbackError);
            return false;
        }
    }
}

// Alternative download method using a hidden iframe
function forceDownloadUsingIframe(url, filename) {
    showProgressToast('Using alternative download method...');
    
    // Create a server-side request to handle the download
    const downloadUrl = `/process-download?url=${encodeURIComponent(url)}&filename=${encodeURIComponent(filename)}`;
    
    // Create a hidden iframe to trigger download
    const iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.src = downloadUrl;
    document.body.appendChild(iframe);
    
    // Clean up after a delay
    setTimeout(() => {
        document.body.removeChild(iframe);
        showSuccessToast('Download initiated! Check your downloads folder.');
    }, 2000);
}

// Helper function to show progress toast
function showProgressToast(message, progress = 0) {
    // Remove any existing progress toast
    const existingToast = document.getElementById('download-progress-toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // Create new toast
    const toastDiv = document.createElement('div');
    toastDiv.id = 'download-progress-toast';
    toastDiv.className = 'position-fixed bottom-0 end-0 p-3';
    toastDiv.style.zIndex = '5';
    
    toastDiv.innerHTML = `
        <div class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header bg-primary text-white">
                <i class="bi bi-download me-2"></i>
                <strong class="me-auto">Downloading...</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close" onclick="this.parentNode.parentNode.parentNode.remove()"></button>
            </div>
            <div class="toast-body">
                <p>${message}</p>
                <div class="progress">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" style="width: ${progress}%" 
                         aria-valuenow="${progress}" aria-valuemin="0" aria-valuemax="100">
                        ${progress}%
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(toastDiv);
}

// Helper function to update progress in toast
function updateProgressToast(progress) {
    const progressBar = document.querySelector('#download-progress-toast .progress-bar');
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
        progressBar.innerText = `${progress}%`;
    }
}

// Helper function to show success toast
function showSuccessToast(message) {
    const existingToast = document.getElementById('download-progress-toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toastDiv = document.createElement('div');
    toastDiv.className = 'position-fixed bottom-0 end-0 p-3';
    toastDiv.style.zIndex = '5';
    
    toastDiv.innerHTML = `
        <div class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header bg-success text-white">
                <i class="bi bi-check-circle me-2"></i>
                <strong class="me-auto">Success</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close" onclick="this.parentNode.parentNode.parentNode.remove()"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    document.body.appendChild(toastDiv);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (toastDiv.parentNode) {
            toastDiv.remove();
        }
    }, 5000);
}

// Helper function to show error toast
function showErrorToast(message) {
    const toastDiv = document.createElement('div');
    toastDiv.className = 'position-fixed bottom-0 end-0 p-3';
    toastDiv.style.zIndex = '5';
    
    toastDiv.innerHTML = `
        <div class="toast show" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header bg-danger text-white">
                <i class="bi bi-exclamation-circle me-2"></i>
                <strong class="me-auto">Error</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close" onclick="this.parentNode.parentNode.parentNode.remove()"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    document.body.appendChild(toastDiv);
    
    // Auto-remove after 7 seconds
    setTimeout(() => {
        if (toastDiv.parentNode) {
            toastDiv.remove();
        }
    }, 7000);
}

// Check if we have the fetch API and necessary features
function checkBrowserSupport() {
    return (
        'fetch' in window &&
        'ReadableStream' in window &&
        'Blob' in window &&
        'URL' in window &&
        'createObjectURL' in URL
    );
}