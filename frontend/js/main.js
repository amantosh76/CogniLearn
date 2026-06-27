(function () {
    const canvas = document.getElementById('particleCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let width, height;
    const particles = [];
    const PARTICLE_COUNT = 60;
    const CONNECTION_DISTANCE = 150;
    const MOUSE_RADIUS = 200;
    let mouse = { x: -1000, y: -1000 };

    function resize() {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    }

    class Particle {
        constructor() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.vx = (Math.random() - 0.5) * 0.4;
            this.vy = (Math.random() - 0.5) * 0.4;
            this.radius = Math.random() * 2 + 1;
            this.color = this._randomColor();
            this.alpha = Math.random() * 0.2 + 0.08;
        }

        _randomColor() {
            const colors = [
                '16, 185, 129',  // emerald
                '6, 182, 212',   // mint
                '245, 158, 11',  // amber
            ];
            return colors[Math.floor(Math.random() * colors.length)];
        }

        update() {
            this.x += this.vx;
            this.y += this.vy;

            if (this.x < 0 || this.x > width) this.vx *= -1;
            if (this.y < 0 || this.y > height) this.vy *= -1;

            const dx = this.x - mouse.x;
            const dy = this.y - mouse.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < MOUSE_RADIUS) {
                const force = (MOUSE_RADIUS - dist) / MOUSE_RADIUS * 0.02;
                this.vx += dx / dist * force;
                this.vy += dy / dist * force;
            }

            const speed = Math.sqrt(this.vx * this.vx + this.vy * this.vy);
            if (speed > 1) {
                this.vx *= 0.99;
                this.vy *= 0.99;
            }
        }

        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${this.color}, ${this.alpha})`;
            ctx.fill();
        }
    }

    function drawConnections() {
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < CONNECTION_DISTANCE) {
                    const opacity = (1 - dist / CONNECTION_DISTANCE) * 0.08;
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = `rgba(16, 185, 129, ${opacity})`;
                    ctx.lineWidth = 0.5;
                    ctx.stroke();
                }
            }
        }
    }

    function animate() {
        ctx.clearRect(0, 0, width, height);
        particles.forEach(p => {
            p.update();
            p.draw();
        });
        drawConnections();
        requestAnimationFrame(animate);
    }

    function init() {
        resize();
        for (let i = 0; i < PARTICLE_COUNT; i++) {
            particles.push(new Particle());
        }
        animate();
    }

    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', (e) => {
        mouse.x = e.clientX;
        mouse.y = e.clientY;
    });
    window.addEventListener('mouseleave', () => {
        mouse.x = -1000;
        mouse.y = -1000;
    });

    init();
})();

const App = {
    currentTab: 'chat',
    sessionId: 'session_' + Math.random().toString(36).substr(2, 9),

    init() {
        this.setupNavigation();
        this.switchTab('chat');
    },

    setupNavigation() {
        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.tab;
                if (tab) this.switchTab(tab);
            });
        });
    },

    switchTab(tabName) {
        this.currentTab = tabName;

        // Toggle nav items
        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Toggle tab sections
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.remove('active');
        });

        const targetTab = document.getElementById(tabName + 'Tab');
        if (targetTab) targetTab.classList.add('active');

        // Tab refresh hooks
        if (tabName === 'analytics' && typeof Analytics !== 'undefined') {
            Analytics.refresh();
        }
        if (tabName === 'study' && typeof Study !== 'undefined') {
            Study.refreshDocList();
        }
        if (tabName === 'documents' && typeof Documents !== 'undefined') {
            Documents.refresh();
        }
    },

    setStatus(text, type = 'ready') {
        const badge = document.getElementById('statusBadge');
        const dot = badge?.querySelector('.status-dot');
        const label = badge?.querySelector('.status-text');
        if (label) label.textContent = text;
        if (dot) {
            dot.style.background = type === 'busy'
                ? 'var(--accent-warning)'
                : type === 'error'
                    ? 'var(--accent-error)'
                    : 'var(--accent-success)';
        }
    },
};

const Analytics = {
    init() {
        this.refresh();
        setInterval(() => {
            if (App.currentTab === 'analytics') this.refresh();
        }, 30000);
    },

    async refresh() {
        try {
            const data = await apiCall('/api/analytics');
            this.renderStats(data);
            this.renderQueryLog(data.recent_queries || []);
        } catch (error) {
            console.error('Analytics error:', error);
        }
    },

    renderStats(data) {
        this.animateValue('statDocsValue', data.total_documents || 0);
        this.animateValue('statChunksValue', data.total_chunks || 0);
        this.animateValue('statQueriesValue', data.total_queries || 0);

        const avgTime = document.getElementById('statAvgTimeValue');
        if (avgTime) avgTime.textContent = (data.avg_response_time || 0) + 's';
    },

    animateValue(elementId, target) {
        const el = document.getElementById(elementId);
        if (!el) return;

        const current = parseInt(el.textContent) || 0;
        if (current === target) return;

        const duration = 600;
        const startTime = performance.now();

        function update(now) {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.round(current + (target - current) * eased);
            if (progress < 1) requestAnimationFrame(update);
        }

        requestAnimationFrame(update);
    },

    renderQueryLog(queries) {
        const log = document.getElementById('queryLog');
        if (!queries.length) {
            log.innerHTML = '<p class="empty-state">No queries yet</p>';
            return;
        }

        log.innerHTML = queries.reverse().map(q => `
            <div class="query-log-item">
                <span class="query-text">${this.escapeHtml(q.question)}</span>
                <div class="query-stats">
                    <span>⏱ ${q.time}s</span>
                    <span>🎯 ${q.confidence}/10</span>
                </div>
            </div>
        `).join('');
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
};

// Show notification toast
function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '✓',
        error: '✕',
        info: 'ℹ',
    };

    toast.innerHTML = `
        <span style="font-size:1.1rem;font-weight:700;">${icons[type] || 'ℹ'}</span>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// REST call helper
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options,
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(err.detail || 'Request failed');
        }
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Start app modules
document.addEventListener('DOMContentLoaded', () => {
    App.init();
    Analytics.init();
});
