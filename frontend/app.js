// TRNDA Frontend - Simple Version
// Hardcoded credentials
const CREDENTIALS = {
    username: 'sw',
    password: 'AWSomeTogheter'
};

// AWS Configuration - will be set by Terraform
const AWS_CONFIG = {
    region: 'eu-central-1',
    bucket: 'tr-sw-trnda-diagrams',
    accessKeyId: 'REPLACE_WITH_ACCESS_KEY',     // Set by Terraform
    secretAccessKey: 'REPLACE_WITH_SECRET_KEY'  // Set by Terraform
};

// State
let currentImage = null;
let rotation = 0;
let originalImageData = null;
let isLoggedIn = false;

// DOM Elements
const loginScreen = document.getElementById('login-screen');
const mainApp = document.getElementById('main-app');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('login-btn');
const loginError = document.getElementById('login-error');

const cameraInput = document.getElementById('camera-input');
const galleryInput = document.getElementById('gallery-input');
const previewContainer = document.getElementById('preview-container');
const previewCanvas = document.getElementById('preview-canvas');
const rotateBtn = document.getElementById('rotate-btn');
const clientInfoTextarea = document.getElementById('client-info');
const charCount = document.getElementById('char-count');
const uploadBtn = document.getElementById('upload-btn');
const statusDiv = document.getElementById('status');
const loadingOverlay = document.getElementById('loading-overlay');

// Configure AWS SDK
AWS.config.update({
    region: AWS_CONFIG.region,
    accessKeyId: AWS_CONFIG.accessKeyId,
    secretAccessKey: AWS_CONFIG.secretAccessKey
});

const s3 = new AWS.S3();

// Login handler
loginBtn.addEventListener('click', () => {
    const username = usernameInput.value;
    const password = passwordInput.value;
    
    if (username === CREDENTIALS.username && password === CREDENTIALS.password) {
        isLoggedIn = true;
        loginScreen.classList.add('hidden');
        mainApp.classList.remove('hidden');
        loginError.classList.add('hidden');
    } else {
        loginError.textContent = 'Invalid username or password';
        loginError.classList.remove('hidden');
    }
});

// Allow Enter key to login
passwordInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        loginBtn.click();
    }
});

// Event listeners
cameraInput.addEventListener('change', handleImageSelect);
galleryInput.addEventListener('change', handleImageSelect);
rotateBtn.addEventListener('click', handleRotate);
clientInfoTextarea.addEventListener('input', handleTextInput);
uploadBtn.addEventListener('click', handleUpload);

function handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
        showStatus('Please select a valid image file.', 'error');
        return;
    }

    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
        showStatus('Image size must be less than 10MB.', 'error');
        return;
    }

    currentImage = file;
    rotation = 0;
    loadImageToCanvas(file);
    previewContainer.classList.remove('hidden');
    updateUploadButton();
    showStatus('Image loaded! Rotate if needed, then upload.', 'success');
}

function loadImageToCanvas(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
            originalImageData = img;
            drawImageOnCanvas(img, 0);
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function drawImageOnCanvas(img, angle) {
    const canvas = previewCanvas;
    const ctx = canvas.getContext('2d');

    let width = img.width;
    let height = img.height;
    
    const maxDimension = 2048;
    if (width > maxDimension || height > maxDimension) {
        const scale = Math.min(maxDimension / width, maxDimension / height);
        width = Math.floor(width * scale);
        height = Math.floor(height * scale);
    }

    if (angle === 90 || angle === 270) {
        canvas.width = height;
        canvas.height = width;
    } else {
        canvas.width = width;
        canvas.height = height;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.translate(canvas.width / 2, canvas.height / 2);
    ctx.rotate((angle * Math.PI) / 180);
    ctx.drawImage(img, -width / 2, -height / 2, width, height);
    ctx.restore();
}

function handleRotate() {
    if (!originalImageData) return;
    rotation = (rotation + 90) % 360;
    drawImageOnCanvas(originalImageData, rotation);
    showStatus(`Image rotated to ${rotation}°`, 'info');
}

function handleTextInput() {
    let text = clientInfoTextarea.value;
    text = removeDiacritics(text);
    
    if (text !== clientInfoTextarea.value) {
        const cursorPosition = clientInfoTextarea.selectionStart;
        clientInfoTextarea.value = text;
        clientInfoTextarea.setSelectionRange(cursorPosition, cursorPosition);
    }
    
    charCount.textContent = text.length;
    
    if (text.length > 1800) {
        charCount.style.color = '#dc3545';
    } else {
        charCount.style.color = '#667eea';
    }
}

function removeDiacritics(str) {
    const normalized = str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    return normalized.replace(/[^\x20-\x7E]/g, '');
}

function updateUploadButton() {
    uploadBtn.disabled = !currentImage;
}

async function handleUpload() {
    if (!currentImage || !isLoggedIn) return;

    const clientInfo = clientInfoTextarea.value.trim();

    if (clientInfo.length > 1900) {
        showStatus('Client info exceeds 1900 characters limit.', 'error');
        return;
    }

    try {
        loadingOverlay.classList.remove('hidden');
        uploadBtn.disabled = true;

        // Get rotated image as blob
        const blob = await new Promise((resolve) => {
            previewCanvas.toBlob(resolve, 'image/jpeg', 0.85);
        });

        // Generate filename
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const filename = `diagram-${timestamp}.jpg`;
        const key = `input/${filename}`;

        // Prepare S3 upload parameters
        const params = {
            Bucket: AWS_CONFIG.bucket,
            Key: key,
            Body: blob,
            ContentType: 'image/jpeg'
        };

        // Add metadata if client info provided
        if (clientInfo) {
            params.Metadata = {
                'client-info': clientInfo
            };
        }

        // Upload to S3
        await s3.putObject(params).promise();

        showStatus(
            'Upload successful! Your diagram will be processed in 10-15 minutes.' +
            (clientInfo.includes('@') ? ' Report will be sent to your email.' : ''),
            'success'
        );

        setTimeout(() => resetForm(), 3000);

    } catch (error) {
        console.error('Upload failed:', error);
        let errorMessage = 'Upload failed. Please try again.';
        
        if (error.code === 'InvalidAccessKeyId' || error.code === 'SignatureDoesNotMatch') {
            errorMessage = 'AWS credentials not configured. Please run Terraform deployment.';
        } else if (error.message) {
            errorMessage = `Upload failed: ${error.message}`;
        }
        
        showStatus(errorMessage, 'error');
    } finally {
        loadingOverlay.classList.add('hidden');
        updateUploadButton();
    }
}

function showStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = 'status';
    if (type) {
        statusDiv.classList.add(type);
    }
}

function resetForm() {
    currentImage = null;
    rotation = 0;
    originalImageData = null;
    
    cameraInput.value = '';
    galleryInput.value = '';
    clientInfoTextarea.value = '';
    charCount.textContent = '0';
    charCount.style.color = '#667eea';
    
    previewContainer.classList.add('hidden');
    
    const ctx = previewCanvas.getContext('2d');
    ctx.clearRect(0, 0, previewCanvas.width, previewCanvas.height);
    
    updateUploadButton();
    showStatus('', '');
}

// Initialize
updateUploadButton();
