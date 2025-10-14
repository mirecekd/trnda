// TRNDA Frontend - Local Testing Version
// Password: Set your password here for local testing

const PASSWORD = 'YourSecurePassword123';

// State
let currentImage = null;
let rotation = 0;
let originalImageData = null;
let isAuthenticated = false;

// DOM Elements
const loginContainer = document.getElementById('login-container');
const appContainer = document.getElementById('app-container');
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

// Login handler
loginBtn.addEventListener('click', () => {
    if (passwordInput.value === PASSWORD) {
        isAuthenticated = true;
        loginContainer.classList.add('hidden');
        appContainer.classList.remove('hidden');
        loginError.classList.add('hidden');
    } else {
        loginError.textContent = 'Invalid password';
        loginError.classList.remove('hidden');
    }
});

passwordInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') loginBtn.click();
});

cameraInput.addEventListener('change', handleImageSelect);
galleryInput.addEventListener('change', handleImageSelect);
rotateBtn.addEventListener('click', handleRotate);
clientInfoTextarea.addEventListener('input', handleTextInput);
uploadBtn.addEventListener('click', handleUpload);

function handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) { showStatus('Invalid file', 'error'); return; }
    if (file.size > 10485760) { showStatus('File too large', 'error'); return; }
    currentImage = file;
    rotation = 0;
    loadImageToCanvas(file);
    previewContainer.classList.remove('hidden');
    updateUploadButton();
    showStatus('Image loaded!', 'success');
}

function loadImageToCanvas(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = () => { originalImageData = img; drawImageOnCanvas(img, 0); };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

function drawImageOnCanvas(img, angle) {
    const canvas = previewCanvas, ctx = canvas.getContext('2d');
    let width = img.width, height = img.height;
    if (width > 2048 || height > 2048) {
        const scale = Math.min(2048 / width, 2048 / height);
        width = Math.floor(width * scale);
        height = Math.floor(height * scale);
    }
    if (angle === 90 || angle === 270) { canvas.width = height; canvas.height = width; }
    else { canvas.width = width; canvas.height = height; }
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
}

function handleTextInput() {
    let text = clientInfoTextarea.value;
    text = text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^\x20-\x7E]/g, '');
    if (text !== clientInfoTextarea.value) {
        const pos = clientInfoTextarea.selectionStart;
        clientInfoTextarea.value = text;
        clientInfoTextarea.setSelectionRange(pos, pos);
    }
    charCount.textContent = text.length;
    charCount.style.color = text.length > 1800 ? '#dc3545' : '#667eea';
}

function updateUploadButton() { uploadBtn.disabled = !currentImage; }

async function handleUpload() {
    if (!currentImage) return;
    const clientInfo = clientInfoTextarea.value.trim();
    if (clientInfo.length > 1900) { showStatus('Too long', 'error'); return; }
    
    loadingOverlay.classList.remove('hidden');
    uploadBtn.disabled = true;
    
    // Simulate upload
    setTimeout(() => {
        loadingOverlay.classList.add('hidden');
        showStatus('LOCAL TEST: Upload simulated! In production this would go to S3.', 'success');
        console.log('Would upload:', { 
            image: currentImage.name, 
            rotation, 
            clientInfo,
            size: currentImage.size 
        });
        setTimeout(() => resetForm(), 5000);
    }, 2000);
}

function showStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = 'status';
    if (type) statusDiv.classList.add(type);
}

function resetForm() {
    currentImage = rotation = originalImageData = null;
    cameraInput.value = galleryInput.value = clientInfoTextarea.value = '';
    charCount.textContent = '0';
    charCount.style.color = '#667eea';
    previewContainer.classList.add('hidden');
    previewCanvas.getContext('2d').clearRect(0, 0, previewCanvas.width, previewCanvas.height);
    updateUploadButton();
    showStatus('', '');
}

updateUploadButton();
