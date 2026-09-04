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
          el.innerText = `+${rc.toFixed(0)} Coins (₹${(rc / 100).toFixed(2)})`;
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

  // Adsgram Ad Block IDs
  ADSGRAM_REWARD_BLOCK_ID: "45936",
  ADSGRAM_INT_BLOCK_ID: "int-45940",
  ADSGRAM_TASK_BLOCK_ID: "task-45941",

  async startAdSession() {
    if (this.isWatching || this.remainingSeconds > 0) return;

    const btn = document.getElementById('btn-watch-ad');
    const btnText = document.getElementById('btn-watch-text');

    this.isWatching = true;
    btn.disabled = true;
    btnText.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> LOADING OFFER...';

    try {
      const initData = await API.post('/ads/start', { ad_type: 'rewarded' });
      
      // 1. PRIMARY: Try Adsgram Native Telegram Rewarded Video (Block ID: 45936)
      if (window.Adsgram && this.ADSGRAM_REWARD_BLOCK_ID) {
        btnText.innerHTML = '<i class="fa-solid fa-play"></i> PLAYING SPONSOR AD...';
        try {
          const adController = window.Adsgram.init({ blockId: this.ADSGRAM_REWARD_BLOCK_ID });
          const result = await adController.show();
          // STRICT CHECK: User MUST have watched ad to full completion (result.done === true)
          if (result && result.done === true) {
            btnText.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> VERIFYING REWARD...';
            const targetId = App.user.telegram_id || App.user.id;
            const verifyRes = await API.get(`/adsgram/reward?userid=${targetId}`);
            App.showToast(`🎉 Reward Received! +${verifyRes.coins_credited || 10} Coins`, 'success');
            await WalletManager.fetchWallet();
            App.fetchUserData();
            await this.checkStatus();
            this.startCooldown(initData.cooldown_seconds);
            this.isWatching = false;
            return;
          } else {
            console.warn('Adsgram ad finished without verified completion:', result);
          }
        } catch (adsgramErr) {
          console.warn('Adsgram ad failed or was blocked by Private DNS:', adsgramErr);
        }
      }

      // 2. SECONDARY: Fallback to Monetag Rewarded Ad (Zone 11715052)
      if (typeof window.show_11715052 === 'function') {
        btnText.innerHTML = '<i class="fa-solid fa-play"></i> PLAYING SPONSOR AD...';
        try {
          // Play standard rewarded interstitial
          await window.show_11715052();
          btnText.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> VERIFYING REWARD...';
          const verifyRes = await API.post('/monetag/postback', {
            sub_id: String(App.user.id),
            event_id: initData.event_id,
            zone_id: "11715052",
            payout: 0.005,
            token: "monetag_verified"
          });
          App.showToast(`🎉 Reward Received! +${verifyRes.coins_credited} Coins`, 'success');
          await WalletManager.fetchWallet();
          App.fetchUserData();
          await this.checkStatus();
          this.startCooldown(initData.cooldown_seconds);
          this.isWatching = false;
          return;
        } catch (monetagErr) {
          console.warn('Monetag video rejected or failed, trying popup fallback...', monetagErr);
          try {
            await window.show_11715052('pop');
            btnText.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> VERIFYING REWARD...';
            const verifyRes = await API.post('/monetag/postback', {
              sub_id: String(App.user.id),
              event_id: initData.event_id,
              zone_id: "11715052",
              payout: 0.005,
              token: "monetag_verified"
            });
            App.showToast(`🎉 Reward Received! +${verifyRes.coins_credited} Coins`, 'success');
            await WalletManager.fetchWallet();
            App.fetchUserData();
            await this.checkStatus();
            this.startCooldown(initData.cooldown_seconds);
            this.isWatching = false;
            return;
          } catch (popErr) {
            console.warn('Monetag popup also failed or closed early:', popErr);
          }
        }
      }

      // 3. If ad was blocked by DNS or failed to play: NO COINS GIVEN!
      App.showToast('⚠️ Ad failed to load! Please disable Private DNS or AdBlocker to earn coins.', 'error');
      this.resetBtn();
      this.isWatching = false;
    } catch (err) {
      App.showToast(err.message || 'Ad session could not start', 'error');
      this.resetBtn();
      this.isWatching = false;
    }
  },

  showInterstitial() {
    if (window.Adsgram && this.ADSGRAM_INT_BLOCK_ID) {
      try {
        const intController = window.Adsgram.init({ blockId: this.ADSGRAM_INT_BLOCK_ID });
        intController.show().catch(e => console.log('Adsgram interstitial skipped:', e));
      } catch (e) {}
    }
  },

  async playAdsgramTask() {
    if (!window.Adsgram || !this.ADSGRAM_TASK_BLOCK_ID) {
      App.showToast('Task ad service not available. Please disable AdBlocker.', 'info');
      return;
    }
    try {
      const taskController = window.Adsgram.init({ blockId: this.ADSGRAM_TASK_BLOCK_ID });
      const res = await taskController.show();
      if (res && res.done === true) {
        const targetId = App.user.telegram_id || App.user.id;
        await API.get(`/adsgram/reward?userid=${targetId}`);
        App.showToast('🎉 Task Completed! +15 Bonus Coins credited', 'success');
        await WalletManager.fetchWallet();
      } else {
        App.showToast('Task was not completed. No coins awarded.', 'info');
      }
    } catch (err) {
      console.warn('Adsgram task error or blocked by DNS:', err);
      App.showToast('Task failed to load. Please disable Private DNS / AdBlocker.', 'error');
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
