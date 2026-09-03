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
      if (!data.can_watch && data.cooldown_seconds > 0) {
        this.startCooldown(data.cooldown_seconds);
      }
    } catch (e) {
      console.warn('Could not check ad status:', e);
    }
  },

  async startAdSession() {
    if (this.isWatching || this.remainingSeconds > 0) return;

    const btn = document.getElementById('btn-watch-ad');
    const btnText = document.getElementById('btn-watch-text');

    this.isWatching = true;
    btn.disabled = true;
    btnText.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> LOADING OFFER...';

    try {
      const initData = await API.post('/ads/start', { ad_type: 'rewarded' });
      
      // 1. If Monetag live rewarded SDK function is loaded
      if (typeof window.show_11715052 === 'function') {
        btnText.innerHTML = '<i class="fa-solid fa-play"></i> PLAYING SPONSOR AD...';
        
        window.show_11715052().then(async () => {
          btnText.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> VERIFYING REWARD...';
          try {
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
            this.startCooldown(initData.cooldown_seconds);
          } catch (postbackErr) {
            App.showToast(postbackErr.message, 'error');
            this.resetBtn();
          } finally {
            this.isWatching = false;
          }
        }).catch(err => {
          console.warn('Monetag ad cancelled or failed:', err);
          App.showToast('Ad was closed early or could not load.', 'error');
          this.resetBtn();
          this.isWatching = false;
        });
      } else if (initData.is_mock) {
        // 2. Mock simulation for development
        btnText.innerHTML = '<i class="fa-solid fa-video fa-fade"></i> WATCHING VIDEO (3s)...';

        setTimeout(async () => {
          try {
            const verifyRes = await API.post('/monetag/postback', {
              sub_id: String(App.user.id),
              event_id: initData.event_id,
              zone_id: initData.zone_id || "11715052",
              payout: 0.005,
              token: "mock_signature_valid"
            });

            App.showToast(`🎉 Reward Received! +${verifyRes.coins_credited} Coins`, 'success');
            await WalletManager.fetchWallet();
            App.fetchUserData();
            this.startCooldown(initData.cooldown_seconds);
          } catch (postbackErr) {
            App.showToast(postbackErr.message, 'error');
            this.resetBtn();
          } finally {
            this.isWatching = false;
          }
        }, 3000);
      } else {
        // 3. Fallback when Monetag tag script is waiting to load
        btnText.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> LOADING AD TAG...';
        App.showToast('Ad service is connecting, please try again in a moment.', 'info');
        this.resetBtn();
        this.isWatching = false;
      }
    } catch (err) {
      App.showToast(err.message, 'error');
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
