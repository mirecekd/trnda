// TRNDA Frontend - Simple Lambda Upload
const API_URL = '${api_url}';

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
loginBtn.addEventListener('click', async () => {
    const password = passwordInput.value;
    if (!password) {
        loginError.textContent = 'Please enter password';
        loginError.classList.remove('hidden');
        return;
    }
    
    try {
        // Verify password with API
        const response = await fetch(`$${API_URL}/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password })
        });
        
        if (response.ok) {
            isAuthenticated = true;
            sessionStorage.setItem('trnda_password', password);
            loginContainer.classList.add('hidden');
            appContainer.classList.remove('hidden');
            loginError.classList.add('hidden');
        } else {
            loginError.textContent = 'Invalid password';
            loginError.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Auth error:', error);
        loginError.textContent = 'Connection error';
        loginError.classList.remove('hidden');
    }
});

passwordInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') loginBtn.click();
});

// Check if already has password
const savedPassword = sessionStorage.getItem('trnda_password');
if (savedPassword) {
    passwordInput.value = savedPassword;
    isAuthenticated = true;
    loginContainer.classList.add('hidden');
    appContainer.classList.remove('hidden');
}

cameraInput.addEventListener('change', handleImageSelect);
galleryInput.addEventListener('change', handleImageSelect);
rotateBtn.addEventListener('click', handleRotate);
clientInfoTextarea.addEventListener('input', handleTextInput);
uploadBtn.addEventListener('click', handleUpload);

function handleImageSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) { showStatus('Please select a valid image file.', 'error'); return; }
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) { showStatus('Image size must be less than 10MB.', 'error'); return; }
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
    const canvas = previewCanvas;
    const ctx = canvas.getContext('2d');
    let width = img.width, height = img.height;
    const maxDimension = 2048;
    if (width > maxDimension || height > maxDimension) {
        const scale = Math.min(maxDimension / width, maxDimension / height);
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
    const normalized = text.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    text = normalized.replace(/[^\x20-\x7E]/g, '');
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
    if (!currentImage || !isAuthenticated) return;
    const clientInfo = clientInfoTextarea.value.trim();
    if (clientInfo.length > 1900) { showStatus('Client info exceeds 1900 characters limit.', 'error'); return; }
    
    try {
        loadingOverlay.classList.remove('hidden');
        uploadBtn.disabled = true;
        
        // Convert canvas to base64
        const base64 = previewCanvas.toDataURL('image/jpeg', 0.85).split(',')[1];
        
        // Send to API
        const response = await fetch(`$${API_URL}/upload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                password: sessionStorage.getItem('trnda_password'),
                image: base64,
                clientInfo: clientInfo
            })
        });
        
        if (response.status === 401) {
            showStatus('Wrong password. Please refresh and login again.', 'error');
            setTimeout(() => {
                sessionStorage.removeItem('trnda_password');
                location.reload();
            }, 2000);
        } else if (response.ok) {
            showStatus('Upload successful! Processing takes 10-15 minutes.' +
                (clientInfo.includes('@') ? ' Report will be sent to your email.' : ''), 'success');
            setTimeout(() => resetForm(), 3000);
        } else {
            throw new Error('Upload failed');
        }
    } catch (error) {
        console.error('Upload failed:', error);
        showStatus('Upload failed. Please try again.', 'error');
    } finally {
        loadingOverlay.classList.add('hidden');
        updateUploadButton();
    }
}

function showStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = 'status';
    if (type) statusDiv.classList.add(type);
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

updateUploadButton();
