/**
 * Direct Download Helper
 * Handles direct downloads without redirecting to another page
 */

// Function to fetch a video or audio file directly
async function fetchAndDownloadFile(url, filename, onProgress) {
    try {
        // Show progress notification
        showProgressToast('Starting download...');
        
        // First, fetch the file headers to get content information
        const headResponse = await fetch(url, { method: 'HEAD' });
        
        if (!headResponse.ok) {
            throw new Error(`HTTP error! Status: ${headResponse.status}`);
        }
        
        // Get content-length if available
        const contentLength = headResponse.headers.get('content-length');
        const totalSize = contentLength ? parseInt(contentLength, 10) : 0;
        
        // Now fetch the actual content
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
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
        return false;
    }
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