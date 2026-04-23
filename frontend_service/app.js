const HOST = window.location.hostname;
const API = {
    auth: `http://${HOST}:30001`,
    wash: `http://${HOST}:30002`,
    booking: `http://${HOST}:30003`
};

let currentUser = null;
let currentAuthMode = 'login'; // 'login' or 'register'
let selectedWashId = null;

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');
    if (token && userStr) {
        currentUser = JSON.parse(userStr);
        updateNavState();
    }
    fetchCarWashes();
});

// UI Navigation
function showPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(`page-${pageId}`).classList.add('active');
    
    if (pageId === 'dashboard') {
        if (!currentUser) return showAuth('login');
        fetchMyBookings();
    }
}

// Auth UI
function showAuth(mode) {
    currentAuthMode = mode;
    document.getElementById('auth-title').innerText = mode === 'login' ? 'Log In' : 'Sign Up';
    document.getElementById('auth-submit').innerText = mode === 'login' ? 'Log In' : 'Sign Up';
    document.querySelector('.toggle-auth').innerText = mode === 'login' ? "Don't have an account? Sign up" : "Already have an account? Log in";
    document.getElementById('auth-error').innerText = '';
    document.getElementById('auth-modal').style.display = 'flex';
}

function toggleAuthMode() {
    showAuth(currentAuthMode === 'login' ? 'register' : 'login');
}

function closeModals() {
    document.querySelectorAll('.modal-overlay').forEach(m => m.style.display = 'none');
}

function updateNavState() {
    if (currentUser) {
        document.getElementById('auth-section').style.display = 'none';
        document.getElementById('user-section').style.display = 'flex';
        document.getElementById('user-email').innerText = currentUser.email;
        document.getElementById('nav-dashboard').style.display = 'inline-block';
    } else {
        document.getElementById('auth-section').style.display = 'flex';
        document.getElementById('user-section').style.display = 'none';
        document.getElementById('nav-dashboard').style.display = 'none';
        showPage('home');
    }
}

// API Calls
async function handleAuth(e) {
    e.preventDefault();
    const email = document.getElementById('auth-email').value;
    const password = document.getElementById('auth-password').value;
    const errorEl = document.getElementById('auth-error');
    errorEl.innerText = 'Loading...';

    const endpoint = currentAuthMode === 'login' ? '/login' : '/register';
    
    try {
        const res = await fetch(`${API.auth}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, role: 'user' })
        });
        const data = await res.json();
        
        if (!res.ok) throw new Error(data.detail || 'Authentication failed');
        
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        currentUser = data.user;
        
        closeModals();
        updateNavState();
    } catch (err) {
        errorEl.innerText = err.message;
    }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    currentUser = null;
    updateNavState();
}

async function fetchCarWashes() {
    const grid = document.getElementById('wash-grid');
    try {
        const res = await fetch(`${API.wash}/car_washes`);
        const washes = await res.json();
        
        if (washes.length === 0) {
            grid.innerHTML = '<p>No car washes available at the moment.</p>';
            return;
        }

        grid.innerHTML = washes.map(w => `
            <div class="card">
                <h3>${w.name}</h3>
                <p>📍 ${w.location}</p>
                <p>⭐ ${w.rating} / 5.0</p>
                <div style="margin-top: 1rem;">
                    ${w.services.map(s => `<div style="font-size: 0.9rem; margin-bottom: 0.2rem;">- ${s.name} <span class="price">$${s.price}</span> (${s.duration_minutes}m)</div>`).join('')}
                </div>
                <button class="btn-primary w-100" style="margin-top: 1rem;" onclick='openBooking(${JSON.stringify(w)})'>Book Now</button>
            </div>
        `).join('');
    } catch (err) {
        grid.innerHTML = '<p class="error-text">Failed to load car washes. Ensure backend is running.</p>';
    }
}

function openBooking(wash) {
    if (!currentUser) return showAuth('login');
    
    selectedWashId = wash.id;
    document.getElementById('book-wash-name').innerText = wash.name;
    const select = document.getElementById('book-service');
    select.innerHTML = wash.services.map(s => 
        `<option value='${JSON.stringify(s)}'>${s.name} - $${s.price} (${s.duration_minutes}m)</option>`
    ).join('');
    
    document.getElementById('booking-error').innerText = '';
    document.getElementById('booking-success').innerText = '';
    document.getElementById('booking-modal').style.display = 'flex';
}

async function handleBooking(e) {
    e.preventDefault();
    const serviceData = JSON.parse(document.getElementById('book-service').value);
    const errorEl = document.getElementById('booking-error');
    const successEl = document.getElementById('booking-success');
    
    errorEl.innerText = '';
    successEl.innerText = 'Processing booking...';

    try {
        const res = await fetch(`${API.booking}/bookings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                car_wash_id: selectedWashId,
                service_name: serviceData.name,
                duration_minutes: serviceData.duration_minutes
            })
        });
        
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Booking failed');
        
        successEl.innerText = `Booking confirmed! Your queue number is ${data.queue_number}. Est wait: ${data.estimated_wait_time_minutes} mins.`;
        setTimeout(() => {
            closeModals();
            showPage('dashboard');
        }, 3000);
    } catch (err) {
        successEl.innerText = '';
        errorEl.innerText = err.message;
    }
}

async function fetchMyBookings() {
    const list = document.getElementById('bookings-list');
    list.innerHTML = '<div class="loader">Loading bookings...</div>';
    
    try {
        const res = await fetch(`${API.booking}/bookings/my`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        const bookings = await res.json();
        
        if (bookings.length === 0) {
            list.innerHTML = '<p>You have no bookings yet.</p>';
            return;
        }

        list.innerHTML = bookings.map(b => `
            <li>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>${b.service_name}</strong>
                        <div style="font-size: 0.8rem; color: var(--text-muted);">Queue: #${b.queue_number} | Wait: ${b.estimated_wait_time_minutes}m</div>
                    </div>
                    <span class="status-badge status-${b.status}">${b.status.toUpperCase()}</span>
                </div>
            </li>
        `).join('');
    } catch (err) {
        list.innerHTML = '<p class="error-text">Failed to load bookings.</p>';
    }
}
