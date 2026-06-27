const Chat = {
    ws: null,
    isStreaming: false,
    currentAiMessage: null,
    currentAiContent: '',
    pendingCitations: null,

    init() {
        this.connectWebSocket();
        this.setupInputHandlers();
        document.getElementById('clearChatBtn').addEventListener('click', () => this.clearChat());
    },

    connectWebSocket() {
        const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
        const wsUrl = `${protocol}://${location.host}/ws/chat`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                App.setStatus('Connected', 'ready');
            };

            this.ws.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };

            this.ws.onclose = () => {
                App.setStatus('Disconnected', 'error');
                setTimeout(() => this.connectWebSocket(), 3000);
            };

            this.ws.onerror = () => {
                App.setStatus('Connection error', 'error');
            };
        } catch (e) {
            console.error('WebSocket error:', e);
            App.setStatus('Connection failed', 'error');
        }
    },

    setupInputHandlers() {
        const input = document.getElementById('chatInput');
        const sendBtn = document.getElementById('sendBtn');

        input.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 140) + 'px';
            sendBtn.disabled = !input.value.trim() || this.isStreaming;
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (input.value.trim() && !this.isStreaming) {
                    this.sendMessage(input.value.trim());
                }
            }
        });

        sendBtn.addEventListener('click', () => {
            if (input.value.trim() && !this.isStreaming) {
                this.sendMessage(input.value.trim());
            }
        });
    },

    sendMessage(text) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
            showToast('Not connected. Reconnecting...', 'error');
            this.connectWebSocket();
            return;
        }

        const welcome = document.querySelector('.welcome-message');
        if (welcome) welcome.remove();

        this.addUserMessage(text);

        const input = document.getElementById('chatInput');
        input.value = '';
        input.style.height = 'auto';
        document.getElementById('sendBtn').disabled = true;

        this.isStreaming = true;
        App.setStatus('Thinking...', 'busy');

        this.createAiMessagePlaceholder();
        this.ws.send(JSON.stringify({ question: text }));
    },

    handleMessage(msg) {
        switch (msg.type) {
            case 'citations':
                this.pendingCitations = msg.data;
                break;
            case 'token':
                this.appendToken(msg.data);
                break;
            case 'done':
                this.finishStreaming(msg.data);
                break;
            case 'error':
                this.showError(msg.data);
                break;
        }
    },

    addUserMessage(text) {
        const messagesDiv = document.getElementById('chatMessages');
        const msg = document.createElement('div');
        msg.className = 'message user';
        msg.innerHTML = `
            <div class="message-avatar">U</div>
            <div class="message-body">
                <div class="message-content">${this.escapeHtml(text)}</div>
            </div>
        `;
        messagesDiv.appendChild(msg);
        this.scrollToBottom();
    },

    createAiMessagePlaceholder() {
        const messagesDiv = document.getElementById('chatMessages');
        const msg = document.createElement('div');
        msg.className = 'message ai';
        msg.id = 'currentAiMsg';
        msg.innerHTML = `
            <div class="message-avatar">AI</div>
            <div class="message-body">
                <div class="message-content" id="aiContentArea">
                    <div class="streaming-dots"><span></span><span></span><span></span></div>
                </div>
            </div>
        `;
        messagesDiv.appendChild(msg);
        this.currentAiMessage = msg;
        this.currentAiContent = '';
        this.scrollToBottom();
    },

    appendToken(token) {
        this.currentAiContent += token;
        const contentArea = document.getElementById('aiContentArea');
        if (contentArea) {
            contentArea.innerHTML = this.formatMarkdown(this.currentAiContent) +
                '<span class="streaming-cursor" style="display:inline-block;width:2px;height:1em;background:var(--accent-secondary);animation:pulse 0.8s infinite;vertical-align:text-bottom;margin-left:2px;"></span>';
        }
        this.scrollToBottom();
    },

    finishStreaming(meta) {
        this.isStreaming = false;
        App.setStatus('Ready', 'ready');

        const contentArea = document.getElementById('aiContentArea');
        if (contentArea) {
            contentArea.innerHTML = this.formatMarkdown(this.currentAiContent);
        }

        if (this.currentAiMessage) {
            const body = this.currentAiMessage.querySelector('.message-body');

            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';
            metaDiv.innerHTML = `
                ${this.buildConfidenceRing(meta.confidence || 7)}
                <span>${meta.elapsed_time || 0}s · ${meta.num_sources || 0} sources</span>
            `;
            body.appendChild(metaDiv);

            if (this.pendingCitations && this.pendingCitations.length > 0) {
                body.appendChild(this.buildCitationsSection(this.pendingCitations));
            }

            this.pendingCitations = null;
        }

        const aiMsg = document.getElementById('currentAiMsg');
        if (aiMsg) aiMsg.removeAttribute('id');
        const aiContent = document.getElementById('aiContentArea');
        if (aiContent) aiContent.removeAttribute('id');

        document.getElementById('sendBtn').disabled = false;
        this.scrollToBottom();
    },

    showError(errorText) {
        this.isStreaming = false;
        App.setStatus('Ready', 'ready');

        const contentArea = document.getElementById('aiContentArea');
        if (contentArea) {
            contentArea.innerHTML = `<span style="color:var(--accent-error);">⚠️ ${this.escapeHtml(errorText)}</span>`;
        }

        const aiMsg = document.getElementById('currentAiMsg');
        if (aiMsg) aiMsg.removeAttribute('id');
        const aiContent = document.getElementById('aiContentArea');
        if (aiContent) aiContent.removeAttribute('id');

        document.getElementById('sendBtn').disabled = false;
        showToast(errorText, 'error');
    },

    buildConfidenceRing(score) {
        const pct = Math.min(100, Math.max(0, (score / 10) * 100));
        const circumference = 2 * Math.PI * 8;
        const dashLen = (pct / 100) * circumference;
        const color = pct >= 70 ? 'var(--accent-success)' : pct >= 40 ? 'var(--accent-warning)' : 'var(--accent-error)';

        return `
            <span class="confidence-ring">
                <svg viewBox="0 0 20 20">
                    <circle class="ring-bg" cx="10" cy="10" r="8" fill="none" stroke-width="2.5"/>
                    <circle class="ring-fill" cx="10" cy="10" r="8" fill="none" stroke="${color}" stroke-width="2.5"
                        stroke-dasharray="${dashLen} ${circumference}" stroke-dashoffset="0"
                        transform="rotate(-90 10 10)" stroke-linecap="round"/>
                </svg>
                <span style="font-weight:600;font-size:0.75rem;">${score}/10</span>
            </span>
        `;
    },

    buildCitationsSection(citations) {
        const container = document.createElement('div');
        container.className = 'citations-container';

        const toggle = document.createElement('button');
        toggle.className = 'citations-toggle';
        toggle.innerHTML = `📎 ${citations.length} source${citations.length > 1 ? 's' : ''} <span style="font-size:0.65rem;">▼</span>`;

        const list = document.createElement('div');
        list.className = 'citations-list';

        citations.forEach(c => {
            const card = document.createElement('div');
            card.className = 'citation-card';
            const relScore = Math.min(100, Math.max(0, (c.relevance_score || 0) * 10));
            card.innerHTML = `
                <div class="citation-header">
                    <span>[${c.index}] ${this.escapeHtml(c.filename)}</span>
                    <div class="relevance-bar"><div class="relevance-fill" style="width:${relScore}%"></div></div>
                </div>
                <div>${this.escapeHtml(c.text)}</div>
            `;
            list.appendChild(card);
        });

        toggle.addEventListener('click', () => {
            list.classList.toggle('expanded');
            toggle.querySelector('span').textContent = list.classList.contains('expanded') ? '▲' : '▼';
        });

        container.appendChild(toggle);
        container.appendChild(list);
        return container;
    },

    clearChat() {
        const messagesDiv = document.getElementById('chatMessages');
        messagesDiv.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="url(#welcomeGrad)" stroke-width="1.5">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
                        <line x1="9" y1="9" x2="9.01" y2="9"/>
                        <line x1="15" y1="9" x2="15.01" y2="9"/>
                        <defs>
                            <linearGradient id="welcomeGrad" x1="2" y1="2" x2="22" y2="22">
                                <stop offset="0%" stop-color="#10b981"/>
                                <stop offset="100%" stop-color="#06b6d4"/>
                            </linearGradient>
                        </defs>
                    </svg>
                </div>
                <h2>Welcome to CogniLearn</h2>
                <p>Upload documents in the <strong>Documents</strong> tab, then ask me anything about them!</p>
                <div class="welcome-features">
                    <div class="feature-chip"><span>📄</span> Multi-format support</div>
                    <div class="feature-chip"><span>🔍</span> Hybrid search</div>
                    <div class="feature-chip"><span>📝</span> Source citations</div>
                    <div class="feature-chip"><span>🧠</span> Context-aware</div>
                </div>
            </div>
        `;
    },

    formatMarkdown(text) {
        let html = this.escapeHtml(text);

        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        html = html.replace(/`(.*?)`/g, '<code style="background:var(--bg-elevated);padding:2px 6px;border-radius:4px;font-family:var(--font-mono);font-size:0.85em;">$1</code>');
        html = html.replace(/\n/g, '<br>');
        html = html.replace(/\[Source (\d+)\]/g, '<span style="color:var(--accent-secondary);font-weight:600;cursor:pointer;" title="Source $1">[Source $1]</span>');

        return html;
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    scrollToBottom() {
        const messagesDiv = document.getElementById('chatMessages');
        requestAnimationFrame(() => {
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        });
    },
};

const Documents = {
    init() {
        this.setupUploadZone();
        this.refresh();
    },

    setupUploadZone() {
        const zone = document.getElementById('uploadZone');
        const input = document.getElementById('fileInput');

        zone.addEventListener('click', (e) => {
            if (e.target.closest('.upload-progress')) return;
            input.click();
        });

        input.addEventListener('change', (e) => {
            if (e.target.files.length) {
                this.uploadFiles(Array.from(e.target.files));
                input.value = '';
            }
        });

        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });
        zone.addEventListener('dragleave', () => {
            zone.classList.remove('dragover');
        });
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                this.uploadFiles(Array.from(e.dataTransfer.files));
            }
        });
    },

    async uploadFiles(files) {
        const progressDiv = document.getElementById('uploadProgress');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');

        progressDiv.style.display = 'block';
        App.setStatus('Uploading...', 'busy');

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            progressText.textContent = `Processing ${file.name} (${i + 1}/${files.length})...`;
            progressFill.style.width = `${((i) / files.length) * 100}%`;

            try {
                const formData = new FormData();
                formData.append('file', file);

                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) {
                    const err = await response.json().catch(() => ({}));
                    throw new Error(err.detail || 'Upload failed');
                }

                const result = await response.json();
                showToast(`✓ ${file.name} uploaded (${result.document.num_chunks} chunks)`, 'success');

            } catch (error) {
                showToast(`Failed: ${file.name} — ${error.message}`, 'error');
            }

            progressFill.style.width = `${((i + 1) / files.length) * 100}%`;
        }

        progressText.textContent = 'Done!';
        App.setStatus('Ready', 'ready');

        setTimeout(() => {
            progressDiv.style.display = 'none';
            progressFill.style.width = '0%';
        }, 1500);

        this.refresh();
    },

    async refresh() {
        try {
            const data = await apiCall('/api/documents');
            this.renderDocuments(data.documents || []);
        } catch (error) {
            console.error('Failed to load documents:', error);
        }
    },

    renderDocuments(docs) {
        const grid = document.getElementById('documentsGrid');
        if (!docs.length) {
            grid.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:40px;">No documents uploaded yet</p>';
            return;
        }

        grid.innerHTML = docs.map(doc => `
            <div class="doc-card" data-doc-id="${doc.doc_id}">
                <div class="doc-card-header">
                    <span class="doc-type-badge ${(doc.file_type || '').toLowerCase()}">${doc.file_type || '?'}</span>
                    <span class="doc-card-title">${this.escapeHtml(doc.filename)}</span>
                </div>
                <div class="doc-card-stats">
                    <span>📦 ${doc.num_chunks} chunks</span>
                    <span>📏 ${this.formatSize(doc.total_chars)} chars</span>
                </div>
                <div class="doc-card-actions">
                    <button class="btn btn-danger" onclick="Documents.deleteDoc('${doc.doc_id}', '${this.escapeHtml(doc.filename)}')">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                        Delete
                    </button>
                </div>
            </div>
        `).join('');
    },

    async deleteDoc(docId, filename) {
        if (!confirm(`Delete "${filename}"? This will remove all its chunks from the knowledge base.`)) return;

        try {
            await apiCall(`/api/documents/${docId}`, { method: 'DELETE' });
            showToast(`Deleted ${filename}`, 'info');
            this.refresh();
        } catch (error) {
            showToast(`Failed to delete: ${error.message}`, 'error');
        }
    },

    formatSize(chars) {
        if (chars > 100000) return Math.round(chars / 1000) + 'K';
        if (chars > 1000) return (chars / 1000).toFixed(1) + 'K';
        return chars;
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
};

const Study = {
    quizScore: 0,
    quizTotal: 0,

    init() {
        document.getElementById('genFlashcardsBtn').addEventListener('click', () => this.generateFlashcards());
        document.getElementById('genQuizBtn').addEventListener('click', () => this.generateQuiz());
        document.getElementById('genMindmapBtn').addEventListener('click', () => this.generateMindmap());
        this.refreshDocList();
    },

    async refreshDocList() {
        try {
            const data = await apiCall('/api/documents');
            const select = document.getElementById('studyDocSelect');
            const current = select.value;
            select.innerHTML = '<option value="">All Documents</option>';
            (data.documents || []).forEach(doc => {
                select.innerHTML += `<option value="${doc.doc_id}">${doc.filename}</option>`;
            });
            select.value = current;
        } catch (e) {
            // Ignore
        }
    },

    getParams() {
        return {
            doc_id: document.getElementById('studyDocSelect').value || null,
            topic: document.getElementById('studyTopic').value.trim(),
        };
    },

    showLoading(text) {
        const output = document.getElementById('studyOutput');
        output.innerHTML = `
            <div class="study-loading">
                <div class="spinner"></div>
                <p>${text}</p>
            </div>
        `;
    },

    async generateFlashcards() {
        const params = this.getParams();
        this.showLoading('Generating flashcards...');
        App.setStatus('Generating flashcards...', 'busy');

        try {
            const data = await apiCall('/api/flashcards', {
                method: 'POST',
                body: JSON.stringify({ ...params, num_cards: 10 }),
            });
            this.renderFlashcards(data.flashcards || []);
            showToast(`Generated ${data.flashcards.length} flashcards`, 'success');
        } catch (error) {
            showToast(`Failed: ${error.message}`, 'error');
            document.getElementById('studyOutput').innerHTML = `<div class="study-placeholder"><p style="color:var(--accent-error);">Error: ${error.message}</p></div>`;
        }
        App.setStatus('Ready', 'ready');
    },

    renderFlashcards(cards) {
        const output = document.getElementById('studyOutput');
        if (!cards.length) {
            output.innerHTML = '<div class="study-placeholder"><p>No flashcards generated. Try uploading documents first.</p></div>';
            return;
        }

        output.innerHTML = `<div class="flashcards-grid">${cards.map((c, i) => `
                <div class="flashcard" onclick="this.classList.toggle('flipped')">
                    <div class="flashcard-inner">
                        <div class="flashcard-front">
                            <span class="flashcard-number">${i + 1}/${cards.length}</span>
                            <h3>${this.escapeHtml(c.front)}</h3>
                        </div>
                        <div class="flashcard-back">
                            ${this.escapeHtml(c.back)}
                        </div>
                    </div>
                </div>
            `).join('')
            }</div>`;
    },

    async generateQuiz() {
        const params = this.getParams();
        this.showLoading('Generating quiz questions...');
        App.setStatus('Generating quiz...', 'busy');

        try {
            const data = await apiCall('/api/quiz', {
                method: 'POST',
                body: JSON.stringify({ ...params, num_questions: 5 }),
            });
            this.renderQuiz(data.quiz || []);
            showToast(`Generated ${data.quiz.length} questions`, 'success');
        } catch (error) {
            showToast(`Failed: ${error.message}`, 'error');
            document.getElementById('studyOutput').innerHTML = `<div class="study-placeholder"><p style="color:var(--accent-error);">Error: ${error.message}</p></div>`;
        }
        App.setStatus('Ready', 'ready');
    },

    renderQuiz(questions) {
        const output = document.getElementById('studyOutput');
        if (!questions.length) {
            output.innerHTML = '<div class="study-placeholder"><p>No quiz generated. Try uploading documents first.</p></div>';
            return;
        }

        this.quizScore = 0;
        this.quizTotal = questions.length;

        const letters = ['A', 'B', 'C', 'D'];

        output.innerHTML = `
            <div class="quiz-container">
                <div class="quiz-score-bar">
                    <span class="score-text" id="quizScoreText">Score: 0 / ${questions.length}</span>
                    <span style="color:var(--text-muted);font-size:0.82rem;" id="quizProgressText">0 answered</span>
                </div>
                ${questions.map((q, qi) => `
                    <div class="quiz-question" id="quizQ${qi}">
                        <div class="quiz-question-number">Question ${qi + 1}</div>
                        <div class="quiz-question-text">${this.escapeHtml(q.question)}</div>
                        <div class="quiz-options">
                            ${(q.options || []).map((opt, oi) => `
                                <div class="quiz-option" data-question="${qi}" data-option="${oi}" data-correct="${q.correct}" onclick="Study.answerQuiz(this)">
                                    <span class="quiz-option-letter">${letters[oi]}</span>
                                    <span>${this.escapeHtml(opt)}</span>
                                </div>
                            `).join('')}
                        </div>
                        <div class="quiz-explanation" id="quizExpl${qi}">${this.escapeHtml(q.explanation || '')}</div>
                    </div>
                `).join('')}
            </div>
        `;
    },

    answerQuiz(optionEl) {
        if (optionEl.classList.contains('disabled')) return;

        const qi = parseInt(optionEl.dataset.question);
        const oi = parseInt(optionEl.dataset.option);
        const correct = parseInt(optionEl.dataset.correct);
        const questionDiv = document.getElementById(`quizQ${qi}`);

        questionDiv.querySelectorAll('.quiz-option').forEach(o => o.classList.add('disabled'));
        optionEl.classList.add('selected');

        if (oi === correct) {
            optionEl.classList.add('correct');
            questionDiv.classList.add('correct');
            this.quizScore++;
        } else {
            optionEl.classList.add('incorrect');
            questionDiv.classList.add('incorrect');
            questionDiv.querySelectorAll('.quiz-option')[correct]?.classList.add('show-correct');
        }

        const expl = document.getElementById(`quizExpl${qi}`);
        if (expl) expl.classList.add('visible');

        const answered = document.querySelectorAll('.quiz-question.correct, .quiz-question.incorrect').length;
        document.getElementById('quizScoreText').textContent = `Score: ${this.quizScore} / ${this.quizTotal}`;
        document.getElementById('quizProgressText').textContent = `${answered} answered`;
    },

    async generateMindmap() {
        const params = this.getParams();
        this.showLoading('Generating mind map...');
        App.setStatus('Generating mind map...', 'busy');

        try {
            const data = await apiCall('/api/mindmap', {
                method: 'POST',
                body: JSON.stringify(params),
            });
            this.renderMindmap(data.mindmap || {});
            showToast('Mind map generated!', 'success');
        } catch (error) {
            showToast(`Failed: ${error.message}`, 'error');
            document.getElementById('studyOutput').innerHTML = `<div class="study-placeholder"><p style="color:var(--accent-error);">Error: ${error.message}</p></div>`;
        }
        App.setStatus('Ready', 'ready');
    },

    renderMindmap(mapData) {
        const output = document.getElementById('studyOutput');
        if (!mapData.nodes || !mapData.nodes.length) {
            output.innerHTML = '<div class="study-placeholder"><p>No mind map data generated.</p></div>';
            return;
        }

        output.innerHTML = '<div class="mindmap-container"><canvas class="mindmap-canvas" id="mindmapCanvas"></canvas></div>';

        const canvas = document.getElementById('mindmapCanvas');
        const container = canvas.parentElement;

        const dpr = window.devicePixelRatio || 1;
        const w = container.clientWidth;
        const h = container.clientHeight;
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        canvas.style.width = w + 'px';
        canvas.style.height = h + 'px';
        const ctx = canvas.getContext('2d');
        ctx.scale(dpr, dpr);

        const cx = w / 2;
        const cy = h / 2;

        const nodes = [];
        const central = { id: 'center', label: mapData.central, x: cx, y: cy, color: '#10b981', radius: 50 };
        nodes.push(central);

        const topLevel = mapData.nodes.filter(n => !n.parent);
        const secondLevel = mapData.nodes.filter(n => n.parent && n.parent !== 'center');

        const maxDist1 = Math.min(w, h) * 0.32;
        const dist1 = Math.max(180, maxDist1);
        const dist2 = Math.max(110, maxDist1 * 0.55);

        topLevel.forEach((n, i) => {
            const angle = (2 * Math.PI * i) / topLevel.length - Math.PI / 2;
            const x = cx + Math.cos(angle) * dist1;
            const y = cy + Math.sin(angle) * dist1;
            nodes.push({
                id: n.id,
                label: n.label,
                x: Math.max(60, Math.min(w - 60, x)),
                y: Math.max(50, Math.min(h - 50, y)),
                color: n.color || '#06b6d4',
                radius: 38,
                parent: 'center',
            });
        });

        secondLevel.forEach((n) => {
            const parent = nodes.find(nd => nd.id === n.parent);
            if (!parent) return;
            const siblings = secondLevel.filter(s => s.parent === n.parent);
            const si = siblings.indexOf(n);
            const baseAngle = Math.atan2(parent.y - cy, parent.x - cx);
            const spreadAngle = Math.PI / (siblings.length <= 2 ? 2.5 : 2);
            const angle = siblings.length === 1
                ? baseAngle
                : baseAngle - spreadAngle / 2 + (spreadAngle * si) / Math.max(siblings.length - 1, 1);
            const x = parent.x + Math.cos(angle) * dist2;
            const y = parent.y + Math.sin(angle) * dist2;
            nodes.push({
                id: n.id,
                label: n.label,
                x: Math.max(50, Math.min(w - 50, x)),
                y: Math.max(40, Math.min(h - 40, y)),
                color: n.color || '#f59e0b',
                radius: 28,
                parent: n.parent,
            });
        });

        nodes.forEach(n => {
            if (!n.parent) return;
            const parent = nodes.find(nd => nd.id === n.parent);
            if (!parent) return;

            const gradient = ctx.createLinearGradient(parent.x, parent.y, n.x, n.y);
            gradient.addColorStop(0, parent.color + '88');
            gradient.addColorStop(1, n.color + '88');

            ctx.beginPath();
            ctx.moveTo(parent.x, parent.y);
            const cpx = (parent.x + n.x) / 2 + (n.y - parent.y) * 0.15;
            const cpy = (parent.y + n.y) / 2 - (n.x - parent.x) * 0.15;
            ctx.quadraticCurveTo(cpx, cpy, n.x, n.y);
            ctx.strokeStyle = gradient;
            ctx.lineWidth = 2.5;
            ctx.stroke();
        });

        nodes.forEach(n => {
            const glow = ctx.createRadialGradient(n.x, n.y, n.radius * 0.5, n.x, n.y, n.radius * 2);
            glow.addColorStop(0, n.color + '20');
            glow.addColorStop(1, n.color + '00');
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius * 2, 0, Math.PI * 2);
            ctx.fillStyle = glow;
            ctx.fill();

            const fill = ctx.createRadialGradient(n.x - n.radius * 0.3, n.y - n.radius * 0.3, 0, n.x, n.y, n.radius);
            fill.addColorStop(0, n.color + '50');
            fill.addColorStop(1, n.color + '22');
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
            ctx.fillStyle = fill;
            ctx.fill();

            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
            ctx.strokeStyle = n.color + 'CC';
            ctx.lineWidth = 2;
            ctx.stroke();

            ctx.fillStyle = '#0f172a';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';

            const isCenter = n.radius >= 50;
            const fontSize = isCenter ? 14 : n.radius > 30 ? 12 : 10;
            ctx.font = `${isCenter ? 'bold ' : ''}${fontSize}px Inter, system-ui, sans-serif`;

            const maxWidth = n.radius * 1.6;
            const words = n.label.split(' ');

            if (words.length === 1 || ctx.measureText(n.label).width <= maxWidth) {
                ctx.fillText(n.label, n.x, n.y, n.radius * 2 - 8);
            } else {
                const lines = [];
                let currentLine = words[0];
                for (let w = 1; w < words.length; w++) {
                    const test = currentLine + ' ' + words[w];
                    if (ctx.measureText(test).width > maxWidth) {
                        lines.push(currentLine);
                        currentLine = words[w];
                    } else {
                        currentLine = test;
                    }
                }
                lines.push(currentLine);

                const lineHeight = fontSize + 2;
                const startY = n.y - ((lines.length - 1) * lineHeight) / 2;
                lines.forEach((line, li) => {
                    ctx.fillText(line, n.x, startY + li * lineHeight, n.radius * 2 - 8);
                });
            }
        });
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    },
};

// Start interaction modules
document.addEventListener('DOMContentLoaded', () => {
    Chat.init();
    Documents.init();
    Study.init();
});
