/* ========================================================================
   Agent Comms — Compose Message Form Logic
   ======================================================================== */

(function () {
    "use strict";

    const DRAFT_KEY_PREFIX = "agent-comms-draft-";

    // --- DOM refs ---
    const form = document.getElementById("compose-form");
    const fromSelect = document.getElementById("compose-from");
    const toSelect = document.getElementById("compose-to");
    const typeSelect = document.getElementById("compose-type");
    const prioritySelect = document.getElementById("compose-priority");
    const subjectInput = document.getElementById("compose-subject");
    const bodyTextarea = document.getElementById("compose-body");
    const sendBtn = document.getElementById("compose-send");
    const discardBtn = document.getElementById("compose-discard");
    const statusEl = document.getElementById("compose-status");
    const draftIndicator = document.getElementById("draft-indicator");

    if (!form) return;

    // -------------------------------------------------------------------
    // Draft key — unique per (from, to) combination so multi-draft works
    // -------------------------------------------------------------------
    function getDraftKey() {
        const f = fromSelect.value || "any";
        const t = toSelect.value || "any";
        return DRAFT_KEY_PREFIX + f + "-" + t;
    }

    // -------------------------------------------------------------------
    // Save / Load / Clear drafts
    // -------------------------------------------------------------------
    function saveDraft() {
        const data = {
            from: fromSelect.value,
            to: toSelect.value,
            type: typeSelect.value,
            priority: prioritySelect.value,
            subject: subjectInput.value,
            body: bodyTextarea.value,
            savedAt: new Date().toISOString(),
        };
        try {
            localStorage.setItem(getDraftKey(), JSON.stringify(data));
            updateDraftIndicator("saved");
        } catch (_) {
            /* storage full — ignore */
        }
    }

    function loadDraft() {
        try {
            const raw = localStorage.getItem(getDraftKey());
            if (!raw) return false;
            const data = JSON.parse(raw);
            if (!data || typeof data !== "object") return false;

            // Only restore if it looks like a real draft (has content)
            if (!data.subject && !data.body) return false;

            // Restore non-empty values
            if (data.from && document.querySelector('#compose-from option[value="' + data.from + '"]')) {
                fromSelect.value = data.from;
            }
            if (data.to && document.querySelector('#compose-to option[value="' + data.to + '"]')) {
                toSelect.value = data.to;
            }
            typeSelect.value = data.type || "notification";
            prioritySelect.value = data.priority || "normal";
            subjectInput.value = data.subject || "";
            bodyTextarea.value = data.body || "";

            updateDraftIndicator("restored");
            return true;
        } catch (_) {
            return false;
        }
    }

    function clearDraft() {
        try {
            localStorage.removeItem(getDraftKey());
        } catch (_) {
            /* ignore */
        }
        updateDraftIndicator("cleared");
    }

    // Re-save if switching from/to so the old key gets stale data
    // but we load for the new key
    function onAgentChange() {
        // Save current draft under old key first
        saveDraft();
        // Then try loading under new key
        loadDraft();
    }

    // -------------------------------------------------------------------
    // Draft indicator
    // -------------------------------------------------------------------
    let draftTimer = null;

    function updateDraftIndicator(state) {
        if (!draftIndicator) return;
        draftIndicator.classList.remove(
            "draft-saved",
            "draft-restored",
            "draft-cleared"
        );

        if (state === "saved") {
            draftIndicator.textContent = "Draft auto-saved ✓";
            draftIndicator.className = "draft-indicator draft-saved";
        } else if (state === "restored") {
            draftIndicator.textContent =
                "Draft restored from " +
                new Date().toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                });
            draftIndicator.className = "draft-indicator draft-restored";
        } else if (state === "cleared") {
            draftIndicator.textContent = "Draft discarded";
            draftIndicator.className = "draft-indicator draft-cleared";
        }

        if (draftTimer) clearTimeout(draftTimer);
        if (state !== "cleared") {
            draftTimer = setTimeout(function () {
                draftIndicator.textContent = "";
                draftIndicator.className = "draft-indicator";
            }, 3000);
        }
    }

    // -------------------------------------------------------------------
    // Auto-save on input (debounced)
    // -------------------------------------------------------------------
    let saveTimeout = null;

    function onInputChange() {
        if (saveTimeout) clearTimeout(saveTimeout);
        saveTimeout = setTimeout(saveDraft, 600);
    }

    // Bind auto-save to all inputs
    [fromSelect, toSelect, typeSelect, prioritySelect, subjectInput, bodyTextarea].forEach(function (el) {
        if (!el) return;
        el.addEventListener("change", onInputChange);
        el.addEventListener("input", onInputChange);
    });

    // When from/to changes, switch draft context
    fromSelect.addEventListener("change", onAgentChange);
    toSelect.addEventListener("change", onAgentChange);

    // -------------------------------------------------------------------
    // Discard draft
    // -------------------------------------------------------------------
    if (discardBtn) {
        discardBtn.addEventListener("click", function () {
            fromSelect.value = "";
            toSelect.value = "";
            typeSelect.value = "notification";
            prioritySelect.value = "normal";
            subjectInput.value = "";
            bodyTextarea.value = "";
            clearDraft();
            fromSelect.focus();
        });
    }

    // -------------------------------------------------------------------
    // Form validation
    // -------------------------------------------------------------------
    function validate() {
        if (!fromSelect.value) {
            setStatus("Please select a sender.", "error");
            fromSelect.focus();
            return false;
        }
        if (!toSelect.value) {
            setStatus("Please select a receiver.", "error");
            toSelect.focus();
            return false;
        }
        if (fromSelect.value === toSelect.value) {
            setStatus("Sender and receiver must be different agents.", "error");
            return false;
        }
        if (!subjectInput.value.trim()) {
            setStatus("Please enter a subject.", "error");
            subjectInput.focus();
            return false;
        }
        if (!bodyTextarea.value.trim()) {
            setStatus("Please write a message.", "error");
            bodyTextarea.focus();
            return false;
        }
        return true;
    }

    // -------------------------------------------------------------------
    // Status messages
    // -------------------------------------------------------------------
    function setStatus(msg, type) {
        if (!statusEl) return;
        statusEl.textContent = msg;
        statusEl.className = "compose-status compose-status-" + (type || "info");
        if (type === "error" || type === "success") {
            setTimeout(function () {
                statusEl.textContent = "";
                statusEl.className = "compose-status";
            }, 5000);
        }
    }

    // -------------------------------------------------------------------
    // Submit
    // -------------------------------------------------------------------
    form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!validate()) return;

        const payload = {
            from_agent_id: parseInt(fromSelect.value, 10),
            to_agent_id: parseInt(toSelect.value, 10),
            type: typeSelect.value,
            priority: prioritySelect.value,
            subject: subjectInput.value.trim(),
            body: bodyTextarea.value.trim(),
        };

        sendBtn.disabled = true;
        sendBtn.textContent = "Sending...";
        setStatus("Sending message...", "info");

        fetch("/api/messages/send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        })
            .then(function (resp) {
                return resp.json().then(function (data) {
                    return { status: resp.status, data: data };
                });
            })
            .then(function (result) {
                if (result.data.status === "ok") {
                    const msg = result.data.message;
                    clearDraft();
                    setStatus("Message sent! Redirecting...", "success");

                    // Emit via socket for real-time if available
                    if (
                        typeof window.socket !== "undefined" &&
                        window.socket.connected
                    ) {
                        window.socket.emit("new_message", msg);
                    }

                    // Redirect to conversation after brief pause
                    setTimeout(function () {
                        window.location.href =
                            "/conversation/" + msg.conversation_id;
                    }, 800);
                } else {
                    setStatus(
                        result.data.error || "Failed to send message.",
                        "error"
                    );
                    sendBtn.disabled = false;
                    sendBtn.textContent = "Send Message";
                }
            })
            .catch(function (err) {
                console.error("Compose send error:", err);
                setStatus(
                    "Network error. Please check your connection and try again.",
                    "error"
                );
                sendBtn.disabled = false;
                sendBtn.textContent = "Send Message";
            });
    });

    // -------------------------------------------------------------------
    // Init — load draft on page load
    // -------------------------------------------------------------------
    loadDraft();

    console.log("[Compose.js] Initialized");
})();
