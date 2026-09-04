// ==========================================================================
// EarnX Ads & Monetag Manager
// Handles Ad verification, cooldown timers, anti-abuse state
// ==========================================================================

const AdsManager = {
  isWatching: false,
  cooldownTimer: null,
  remainingSeconds: 0,

  async checkStatus() {
    try {
      const data = await API.get('/ads/status');
      if (data.reward_coins) {
        const rc = parseFloat(data.reward_coins);
        const el = document.getElementById('watch-reward-val');
        if (el) {
          el.innerText = `+${rc.toFixed(0)} Coins`;
        }
      }

      // Update Daily Limit progress UI
      const watched = data.watched_today || 0;
      const limit = data.daily_limit || 20;
      const progressEl = document.getElementById('daily-ads-progress');
      const barEl = document.getElementById('daily-ads-bar');
      const btn = document.getElementById('btn-watch-ad');
      const btnText = document.getElementById('btn-watch-text');

      if (progressEl) {
        progressEl.innerText = `${watched} / ${limit} Watched`;
      }
      if (barEl && limit > 0) {
        const pct = Math.min(100, Math.round((watched / limit) * 100));
        barEl.style.width = `${pct}%`;
      }

      if (data.daily_limit_reached) {
        if (btn && btnText) {
          btn.disabled = true;
          btnText.innerText = `DAILY LIMIT REACHED (${limit}/${limit})`;
        }
        return;
      }

      if (!data.can_watch && data.cooldown_seconds > 0) {
        this.startCooldown(data.cooldown_seconds);
      }
    } catch (e) {
      console.warn('Could not check ad status:', e);
    }
  },

  inAppInitialized: false,

  initInAppAds() {
    if (this.inAppInitialized) return;
    let attempts = 0;
    const interval = setInterval(() => {
      attempts++;
      if (typeof window.show_11715052 === 'function') {
        clearInterval(interval);
        try {
          // Activate Monetag In-App Interstitial format
          window.show_11715052({
            type: 'inApp',
            inAppSettings: {
              frequency: 2,
              capping: 0.1,
              interval: 30,
              timeout: 5,
              everyPage: false
            }
          });
          this.inAppInitialized = true;
          console.info('✅ Monetag In-App Interstitial activated successfully.');
        } catch (e) {
          console.warn('Monetag inApp init warning:', e);
        }
      } else if (attempts > 20) {
        clearInterval(interval);
      }
    }, 1000);
  },

  waitingInterval: null,

  startWaitingForBrowserAd(eventId, cooldownSeconds, initialCoins) {
    const btn = document.getElementById('btn-watch-ad');
    const btnText = document.getElementById('btn-watch-text');
    if (btnText) btnText.innerHTML = '<i class="fa-solid fa-arrow-up-right-from-square"></i> AD OPENED IN CHROME...';

    let elapsed = 0;
    if (this.waitingInterval) clearInterval(this.waitingInterval);

    this.waitingInterval = setInterval(async () => {
      elapsed += 2;
      try {
        await WalletManager.fetchWallet();
        const currentCoins = parseFloat(WalletManager.walletData?.available_coins || 0);
        if (currentCoins > initialCoins) {
          clearInterval(this.waitingInterval);
          this.waitingInterval = null;
          App.showToast('🎉 Ad Completed in Browser! Coins Credited', 'success');
          App.fetchUserData();
          await this.checkStatus();
          this.startCooldown(cooldownSeconds);
          this.isWatching = false;
          return;
        }
      } catch (e) {
        console.warn('Waiting poll error:', e);
      }

      if (elapsed >= 120) {
        clearInterval(this.waitingInterval);
        this.waitingInterval = null;
        this.resetBtn();
        this.isWatching = false;
      }
    }, 2000);
  },

  async startAdSession() {
    if (this.isWatching || this.remainingSeconds > 0) return;

    const btn = document.getElementById('btn-watch-ad');
    const btnText = document.getElementById('btn-watch-text');

    this.isWatching = true;
    btn.disabled = true;
    btnText.innerHTML = '<i class="fa-solid fa-arrow-up-right-from-square fa-fade"></i> OPENING CHROME...';

    try {
      const initData = await API.post('/ads/start', { ad_type: 'rewarded' });
      
      const currentCoins = parseFloat(WalletManager.walletData?.available_coins || 0);
      const baseHost = window.location.origin || 'https://earnx-app.onrender.com';
      const adViewerUrl = `${baseHost}/view-ad.html?v=20260904_04&uid=${App.user.id}&event_id=${initData.event_id}&zone_id=11715052`;

      // Open ad in Google Chrome or default external browser
      if (window.Telegram?.WebApp?.openLink) {
        App.showToast('🌐 Opening ad in Chrome browser...', 'info');
        window.Telegram.WebApp.openLink(adViewerUrl, { try_instant_view: false });
      } else {
        window.open(adViewerUrl, '_blank');
      }

      this.startWaitingForBrowserAd(initData.event_id, initData.cooldown_seconds, currentCoins);
    } catch (err) {
      App.showToast(err.message || 'Ad session could not start', 'error');
      this.resetBtn();
      this.isWatching = false;
    }
  },

  startCooldown(seconds) {
    this.remainingSeconds = seconds;
    const cooldownEl = document.getElementById('ad-cooldown-timer');
    const secEl = document.getElementById('cooldown-seconds');
    const btn = document.getElementById('btn-watch-ad');
    const btnText = document.getElementById('btn-watch-text');

    if (cooldownEl) cooldownEl.style.display = 'block';
    btn.disabled = true;
    btnText.textContent = 'COOLDOWN ACTIVE';

    if (this.cooldownTimer) clearInterval(this.cooldownTimer);

    this.cooldownTimer = setInterval(() => {
      this.remainingSeconds--;
      if (secEl) secEl.textContent = this.remainingSeconds;

      if (this.remainingSeconds <= 0) {
        clearInterval(this.cooldownTimer);
        this.cooldownTimer = null;
        if (cooldownEl) cooldownEl.style.display = 'none';
        this.resetBtn();
      }
    }, 1000);
  },

  resetBtn() {
    const btn = document.getElementById('btn-watch-ad');
    const btnText = document.getElementById('btn-watch-text');
    if (btn) btn.disabled = false;
    if (btnText) btnText.innerHTML = '<i class="fa-solid fa-play"></i> WATCH AD NOW';
  }
};
