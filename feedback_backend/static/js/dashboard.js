/**
 * Initialize all dashboard functionality when DOM is loaded
 */
document.addEventListener('DOMContentLoaded', function() {
    initBootstrapComponents();
    setupNotificationHandlers();
    initSettingsIntegration();
});

/* --------------------------------
   BOOTSTRAP COMPONENTS
-------------------------------- */
function initBootstrapComponents() {
    // Dropdowns
    document.querySelectorAll('.dropdown-toggle').forEach(el => {
        new bootstrap.Dropdown(el);
    });

    // Tooltips
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });
}

/* --------------------------------
   NOTIFICATIONS
-------------------------------- */
function setupNotificationHandlers() {
    const notificationItems = document.querySelectorAll('.notification-item');
    notificationItems.forEach(item => {
        item.addEventListener('click', function() {
            const notificationId = this.dataset.notificationId;
            if (notificationId && !this.classList.contains('read')) {
                markNotificationAsRead(notificationId, this);
            }
        });
    });
}

function markNotificationAsRead(notificationId, element) {
    if (!notificationId || !element) return;

    fetch(`/notifications/${notificationId}/mark-read/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) throw new Error('Failed to mark as read');
        element.classList.add('read');
        const dot = element.querySelector('.notification-dot');
        if (dot) dot.remove();
    })
    .catch(error => console.error('Error marking notification as read:', error));
}

function markAllNotificationsAsRead() {
    fetch('/notifications/mark-all-read/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(res => {
        if (!res.ok) throw new Error('Failed to mark all as read');
        return res.json();
    })
    .then(data => {
        if (data.status === 'success') {
            // Update UI instantly
            document.querySelectorAll('.notification-item').forEach(item => {
                item.classList.add('read');
                const dot = item.querySelector('.notification-dot');
                if (dot) dot.remove();
            });

            showToast(`${data.updated_count} notifications marked as read`, 'success');
        }
    })
    .catch(err => {
        console.error(err);
        showToast('Failed to mark notifications as read', 'danger');
    });
}

function getCSRFToken() {
    const cookie = document.cookie.split('; ').find(row => row.startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}

/* --------------------------------
   SETTINGS INTEGRATION
-------------------------------- */
function initSettingsIntegration() {
    const settingsModal = document.getElementById('settingsModal');
    if (!settingsModal) {
        console.log('Settings modal not found on this page');
        return;
    }

    const form = document.getElementById('settingsForm');
    if (!form) {
        console.error('Settings form not found');
        return;
    }

    const fontSizeInput = document.getElementById('fontSize');
    const fontPreview = document.querySelector('.font-size-preview');
    const languageSelect = document.getElementById('languageSelect');
    const emailToggle = document.getElementById('emailNotifications');
    const pushToggle = document.getElementById('pushNotifications');

    /* --------------------------------
       LIVE FONT SIZE PREVIEW
    -------------------------------- */
    if (fontSizeInput && fontPreview) {
        fontSizeInput.addEventListener('input', () => {
            fontPreview.style.fontSize = `${fontSizeInput.value}px`;
        });
        fontPreview.style.fontSize = `${fontSizeInput.value}px`;
    }

    /* --------------------------------
       LOAD SETTINGS WHEN MODAL SHOWN
    -------------------------------- */
    settingsModal.addEventListener('show.bs.modal', () => {
        const getSettingsUrl = form.dataset.getSettingsUrl;
        if (!getSettingsUrl) {
            console.error('Missing data-get-settings-url attribute on form');
            return;
        }

        fetch(getSettingsUrl)
            .then(res => res.json())
            .then(settings => {
                if (!settings.success) return;

                // Theme (radio buttons)
                if (settings.theme) {
                    const themeInput = form.querySelector(`input[name="theme"][value="${settings.theme}"]`);
                    if (themeInput) themeInput.checked = true;
                }

                // Font size
                if (fontSizeInput && settings.font_size) {
                    fontSizeInput.value = settings.font_size;
                    if (fontPreview) fontPreview.style.fontSize = `${settings.font_size}px`;
                }

                // Language
                if (languageSelect && settings.preferred_language) {
                    languageSelect.value = settings.preferred_language;
                }

                // Notifications
                if (emailToggle && settings.email_notifications !== undefined) {
                    emailToggle.checked = settings.email_notifications;
                }
                if (pushToggle && settings.push_notifications !== undefined) {
                    pushToggle.checked = settings.push_notifications;
                }
            })
            .catch(err => console.error("Failed to load settings:", err));
    });

    /* --------------------------------
       HANDLE FORM SUBMISSION
    -------------------------------- */
    form.addEventListener('submit', function (e) {
        e.preventDefault();

        // Get the selected theme from radio buttons
        const selectedTheme = form.querySelector('input[name="theme"]:checked');
        
        // Build settings object with safe checks
        const newSettings = {
            theme: selectedTheme ? selectedTheme.value : 'light',
            font_size: fontSizeInput ? fontSizeInput.value : 16,
            preferred_language: languageSelect ? languageSelect.value : 'en',
            email_notifications: emailToggle ? emailToggle.checked : true,
            push_notifications: pushToggle ? pushToggle.checked : true,
        };

        // Get CSRF token
        const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]');
        if (!csrfToken) {
            console.error('CSRF token not found');
            showToast('Form error: CSRF token missing', 'danger');
            return;
        }

        fetch(form.action, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken.value,
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify(newSettings),
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                showToast('Settings saved successfully!', 'success');
                applySettings(newSettings);
                const modalInstance = bootstrap.Modal.getInstance(settingsModal);
                if (modalInstance) modalInstance.hide();
            } else {
                showToast(data.error || 'Failed to save settings.', 'danger');
            }
        })
        .catch(err => {
            console.error('Error saving settings:', err);
            showToast('Network error occurred.', 'danger');
        });
    });
}

/* --------------------------------
   APPLY SETTINGS TO PAGE
-------------------------------- */
function applySettings(settings) {
    const html = document.documentElement;

    // Dark mode
    if (settings.theme) {
        if (settings.theme === 'system') {
            // Use system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            html.setAttribute('data-bs-theme', prefersDark ? 'dark' : 'light');
        } else {
            html.setAttribute('data-bs-theme', settings.theme);
        }
    }

    // Font size
    if (settings.font_size) {
        html.style.fontSize = `${settings.font_size}px`;
    }

    // Language
    if (settings.preferred_language) {
        html.lang = settings.preferred_language;
    }
}

/* --------------------------------
   TOAST NOTIFICATIONS
-------------------------------- */
function showToast(message, type = 'success') {
    if (!message) return;

    // Check if window.showToast exists (from toast template)
    if (typeof window.showToast === 'function' && window.showToast !== showToast) {
        window.showToast(message, type);
        return;
    }

    // Fallback toast creation
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1100';
        document.body.appendChild(container);
    }

    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white bg-${type} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    container.appendChild(toastEl);
    const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: 3000 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}