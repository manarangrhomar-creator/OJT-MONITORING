/**
 * PWA Registration & Install Prompt
 * Handles service worker registration, install banner, and push notifications
 */

const PWA = {
  deferredPrompt: null,
  isInstalled: false,
  isOnline: navigator.onLine,

  init() {
    this.registerServiceWorker();
    this.setupOnlineOfflineDetection();
    this.setupInstallPrompt();
    this.requestNotificationPermission();
  },

  // ─── Service Worker Registration ───────────────────────────────
  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js', {
          scope: '/',
        });

        console.log('Service Worker registered:', registration.scope);

        // Check for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'activated') {
                this.showUpdateBanner();
              }
            });
          }
        });

        // Listen for controlling change
        navigator.serviceWorker.addEventListener('controllerchange', () => {
          window.location.reload();
        });
      } catch (error) {
        console.error('Service Worker registration failed:', error);
      }
    }
  },

  // ─── Install Prompt ────────────────────────────────────────────
  setupInstallPrompt() {
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      this.deferredPrompt = e;
      this.showInstallBanner();
    });

    window.addEventListener('appinstalled', () => {
      this.isInstalled = true;
      this.hideInstallBanner();
      console.log('PWA installed successfully');
    });
  },

  showInstallBanner() {
    const banner = document.getElementById('pwa-install-banner');
    if (banner) {
      banner.classList.remove('hidden');
    }
  },

  hideInstallBanner() {
    const banner = document.getElementById('pwa-install-banner');
    if (banner) {
      banner.classList.add('hidden');
    }
  },

  async installApp() {
    if (!this.deferredPrompt) return;

    this.deferredPrompt.prompt();
    const { outcome } = await this.deferredPrompt.userChoice;

    if (outcome === 'accepted') {
      console.log('User accepted install prompt');
    }
    this.deferredPrompt = null;
    this.hideInstallBanner();
  },

  // ─── Online/Offline Detection ──────────────────────────────────
  setupOnlineOfflineDetection() {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.showConnectionStatus('back online', 'success');
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.showConnectionStatus('offline — some features may be limited', 'warning');
    });
  },

  showConnectionStatus(message, type) {
    const existing = document.getElementById('pwa-connection-status');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.id = 'pwa-connection-status';
    toast.className = `fixed top-4 right-4 z-50 px-4 py-2 rounded-lg shadow-lg text-white text-sm font-medium transition-all duration-300 ${
      type === 'success' ? 'bg-green-600' : 'bg-yellow-600'
    }`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  },

  // ─── Push Notifications ────────────────────────────────────────
  async requestNotificationPermission() {
    if (!('Notification' in window)) return;

    if (Notification.permission === 'default') {
      // Don't auto-request — wait for user action
      console.log('Notification permission not yet requested');
    }
  },

  async subscribeToPush() {
    if (!('Notification' in window) || !('serviceWorker' in navigator)) {
      return null;
    }

    const permission = await Notification.requestPermission();
    if (permission !== 'granted') return null;

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array(
          document.querySelector('meta[name="vapid-key"]')?.content || ''
        ),
      });
      return subscription;
    } catch (error) {
      console.error('Push subscription failed:', error);
      return null;
    }
  },

  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; i++) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  },

  // ─── Update Banner ─────────────────────────────────────────────
  showUpdateBanner() {
    const existing = document.getElementById('pwa-update-banner');
    if (existing) return;

    const banner = document.createElement('div');
    banner.id = 'pwa-update-banner';
    banner.className = 'fixed bottom-4 left-4 right-4 sm:left-auto sm:right-4 sm:w-80 z-50 bg-[#11693A] text-white p-4 rounded-lg shadow-xl flex items-center gap-3';
    banner.innerHTML = `
      <div class="flex-1">
        <p class="font-semibold text-sm">Update Available</p>
        <p class="text-xs opacity-90">Refresh to get the latest version.</p>
      </div>
      <button onclick="PWA.applyUpdate()" class="bg-white text-[#11693A] px-3 py-1.5 rounded text-sm font-medium hover:bg-gray-100">
        Update
      </button>
      <button onclick="this.closest('#pwa-update-banner').remove()" class="text-white/70 hover:text-white text-lg">&times;</button>
    `;
    document.body.appendChild(banner);
  },

  applyUpdate() {
    if (navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' });
    }
  },
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => PWA.init());
