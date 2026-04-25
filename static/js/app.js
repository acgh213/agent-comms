/* ========================================================================
   Agent Comms — SocketIO Client & Real-Time Updates
   ======================================================================== */

(function() {
    'use strict';

    // --- SocketIO Connection ---
    const socket = io({
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        timeout: 10000,
    });

    // Make socket globally available for page-specific scripts
    window.socket = socket;

    // --- DOM References ---
    const connIndicator = document.getElementById('conn-indicator');
    const connText = document.getElementById('conn-text');

    // --- Connection Event Handlers ---
    socket.on('connect', function() {
        console.log('[SocketIO] Connected:', socket.id);
        updateConnectionStatus('online', 'Connected');
    });

    socket.on('disconnect', function(reason) {
        console.log('[SocketIO] Disconnected:', reason);
        updateConnectionStatus('offline', 'Disconnected');
    });

    socket.on('connect_error', function(err) {
        console.error('[SocketIO] Connection error:', err.message);
        updateConnectionStatus('offline', 'Error');
    });

    socket.on('reconnect', function(attempt) {
        console.log('[SocketIO] Reconnected after', attempt, 'attempts');
        updateConnectionStatus('online', 'Connected');
        showNotification('Reconnected to server', 'info');
    });

    socket.on('reconnect_attempt', function(attempt) {
        updateConnectionStatus('offline', 'Reconnecting...');
    });

    socket.on('reconnect_error', function(err) {
        console.error('[SocketIO] Reconnect error:', err);
    });

    socket.on('reconnect_failed', function() {
        updateConnectionStatus('offline', 'Lost Connection');
        showNotification('Connection lost. Please refresh the page.', 'error');
    });

    function updateConnectionStatus(state, text) {
        if (connIndicator && connText) {
            connIndicator.className = 'status-indicator ' + state;
            connText.textContent = text;
        }
    }

    // --- Real-Time Event Handlers ---

    // New message received
    socket.on('message', function(data) {
        console.log('[SocketIO] New message:', data);
        updateUnreadBadge();
        appendMessageToFeed(data);
        showNotification('New message from ' + (data.sender_name || 'Unknown'), 'info');
    });

    // Agent status changed
    socket.on('agent_status', function(data) {
        console.log('[SocketIO] Agent status:', data);
        updateAgentStatus(data.agent_id, data.status);
    });

    // New note added
    socket.on('note_added', function(data) {
        console.log('[SocketIO] New note:', data);
    });

    // Conversation updated
    socket.on('conversation_updated', function(data) {
        console.log('[SocketIO] Conversation updated:', data);
    });

    // --- UI Update Helpers ---

    function updateUnreadBadge() {
        // Update unread stat card if present
        const unreadStat = document.getElementById('stat-unread-messages');
        if (unreadStat) {
            const current = parseInt(unreadStat.textContent, 10) || 0;
            unreadStat.textContent = current + 1;
        }
    }

    function appendMessageToFeed(data) {
        const feed = document.getElementById('recent-messages');
        if (!feed || !feed.querySelector('.message-feed')) return;

        const list = feed.querySelector('.message-feed');
        const newItem = document.createElement('li');
        newItem.className = 'message-feed-item';
        newItem.innerHTML = '' +
            '<div class="msg-sender-avatar" style="background: ' + (data.sender_color || '#555') + ';">' +
                (data.sender_name ? data.sender_name[0].toUpperCase() : '?') +
            '</div>' +
            '<div class="msg-content">' +
                '<div class="msg-header">' +
                    '<strong class="msg-sender">' + (data.sender_name || 'Unknown') + '</strong>' +
                    '<span class="msg-arrow">→</span>' +
                    '<span class="msg-receiver">' + (data.receiver_name || 'Unknown') + '</span>' +
                    '<span class="msg-time">just now</span>' +
                '</div>' +
                '<div class="msg-preview">' +
                    '<span class="msg-subject">' + (data.subject || '(no subject)') + '</span>' +
                '</div>' +
            '</div>' +
            '<span class="msg-unread-dot"></span>';

        // Add to top, remove last if > 10
        list.insertBefore(newItem, list.firstChild);
        if (list.children.length > 10) {
            list.removeChild(list.lastChild);
        }
    }

    function updateAgentStatus(agentId, status) {
        // Update agent status dots on the dashboard
        const agentCards = document.querySelectorAll('.agent-card');
        agentCards.forEach(function(card) {
            const link = card.getAttribute('href');
            if (link && link.includes('/agent/' + agentId)) {
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

        // Update online count stat
        const onlineStat = document.getElementById('stat-online-agents');
        if (onlineStat && status === 'online') {
            onlineStat.textContent = parseInt(onlineStat.textContent, 10) + 1;
        }
    }

    // --- Notification System ---
    function showNotification(message, type) {
        // Use browser notification if available and permitted
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('Agent Comms', { body: message });
            return;
        }

        // Fallback: create an in-page toast
        const existing = document.querySelector('.toast-notification');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'toast-notification toast-' + (type || 'info');
        toast.textContent = message;
        toast.style.cssText = '' +
            'position: fixed; bottom: 1.5rem; right: 1.5rem; ' +
            'padding: 0.75rem 1.25rem; border-radius: 8px; ' +
            'background: var(--bg-secondary, #1a1a25); ' +
            'border: 1px solid var(--border-color, #2a2a3d); ' +
            'color: var(--text-primary, #e0d8d0); ' +
            'font-size: 0.85rem; z-index: 9999; ' +
            'box-shadow: 0 4px 20px rgba(0,0,0,0.4); ' +
            'animation: fadeIn 0.3s ease; ' +
            'max-width: 350px;';

        document.body.appendChild(toast);
        setTimeout(function() { toast.remove(); }, 4000);
    }

    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
})();
