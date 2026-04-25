/* ========================================================================
   Agent Comms — Dashboard-Specific Logic
   ======================================================================== */

(function() {
    'use strict';

    // --- Live Clock ---
    function updateClock() {
        const clockEl = document.getElementById('live-clock');
        if (!clockEl) return;
        const now = new Date();
        const timeStr = now.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        clockEl.textContent = timeStr;
    }

    // Update clock every second
    setInterval(updateClock, 1000);
    updateClock();

    // --- Real-time Agent Status Updates ---
    const socket = window.socket;
    if (!socket) return;

    // Update agent status when SocketIO emits changes
    socket.on('agent_online', function(data) {
        updateSingleAgentStatus(data.agent_id, 'online');
        updateOnlineCount(1);
    });

    socket.on('agent_offline', function(data) {
        updateSingleAgentStatus(data.agent_id, 'offline');
        updateOnlineCount(-1);
    });

    socket.on('agent_away', function(data) {
        updateSingleAgentStatus(data.agent_id, 'away');
    });

    socket.on('agent_busy', function(data) {
        updateSingleAgentStatus(data.agent_id, 'busy');
    });

    function updateSingleAgentStatus(agentId, status) {
        const cards = document.querySelectorAll('.agent-card');
        cards.forEach(function(card) {
            const href = card.getAttribute('href');
            if (href && href.endsWith('/' + agentId)) {
                const dot = card.querySelector('.status-dot');
                const label = card.querySelector('.status-label');
                if (dot) {
                    dot.className = 'status-dot ' + status;
                }
                if (label) {
                    label.textContent = status.charAt(0).toUpperCase() + status.slice(1);
                }
            }
        });
    }

    let onlineCountCache = null;

    function updateOnlineCount(delta) {
        const onlineStat = document.getElementById('stat-online-agents');
        if (!onlineStat) return;

        if (onlineCountCache === null) {
            onlineCountCache = parseInt(onlineStat.textContent, 10) || 0;
        }
        onlineCountCache += delta;
        if (onlineCountCache < 0) onlineCountCache = 0;
        onlineStat.textContent = onlineCountCache;
    }

    // --- Send Message Form ---
    const sendForm = document.getElementById('send-message-form');
    if (sendForm) {
        sendForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const receiverSelect = document.getElementById('msg-receiver');
            const subjectInput = document.getElementById('msg-subject');
            const bodyTextarea = document.getElementById('msg-body');
            const prioritySelect = document.getElementById('msg-priority');
            const agentId = this.dataset.agentId;

            const payload = {
                from_agent_id: parseInt(agentId, 10),
                to_agent_id: parseInt(receiverSelect.value, 10),
                subject: subjectInput.value.trim(),
                body: bodyTextarea.value.trim(),
                type: 'text',
                priority: prioritySelect.value,
            };

            if (!payload.to_agent_id || !payload.subject || !payload.body) {
                showFormMessage('Please fill in all required fields.', 'error');
                return;
            }

            const submitBtn = this.querySelector('.btn-primary');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Sending...';

            fetch('/api/messages/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            })
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.status === 'ok') {
                    subjectInput.value = '';
                    bodyTextarea.value = '';
                    showFormMessage('Message sent!', 'success');
                    // Emit via socket for real-time
                    if (socket && socket.connected) {
                        socket.emit('new_message', data.message);
                    }
                } else {
                    showFormMessage(data.error || 'Failed to send message.', 'error');
                }
            })
            .catch(function(err) {
                console.error('Send message error:', err);
                showFormMessage('Network error. Please try again.', 'error');
            })
            .finally(function() {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Send Message';
            });
        });
    }

    function showFormMessage(text, type) {
        const form = document.getElementById('send-message-form');
        if (!form) return;

        let msgEl = form.querySelector('.form-message');
        if (!msgEl) {
            msgEl = document.createElement('div');
            msgEl.className = 'form-message';
            form.appendChild(msgEl);
        }

        msgEl.textContent = text;
        msgEl.className = 'form-message form-message-' + (type || 'info');
        msgEl.style.cssText = '' +
            'margin-top: 0.5rem; padding: 0.4rem 0.75rem; ' +
            'border-radius: 6px; font-size: 0.8rem; ' +
            (type === 'success'
                ? 'background: rgba(0,255,136,0.1); color: #00ff88; border: 1px solid rgba(0,255,136,0.2);'
                : 'background: rgba(255,51,85,0.1); color: #ff3355; border: 1px solid rgba(255,51,85,0.2);');

        setTimeout(function() { msgEl.remove(); }, 4000);
    }

    // --- Dashboard data refresh ---
    const refreshBtn = document.getElementById('refresh-dashboard');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            location.reload();
        });
    }

    console.log('[Dashboard.js] Initialized');
})();
