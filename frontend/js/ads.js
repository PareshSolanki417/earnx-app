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
      
      // Simulate video view in development mode
      if (initData.is_mock) {
        btnText.innerHTML = '<i class="fa-solid fa-video fa-fade"></i> WATCHING VIDEO (3s)...';

        setTimeout(async () => {
          try {
            // Trigger backend postback verification
            const verifyRes = await API.post('/monetag/postback', {
              sub_id: String(App.user.id),
              event_id: initData.event_id,
              zone_id: initData.zone_id,
              payout: 0.005,
              token: "mock_signature_valid"
            });

            App.showToast(`🎉 Reward Received! +${verifyRes.coins_credited} Coins`, 'success');
            
            // Refresh wallet balance
            await WalletManager.fetchWallet();
            App.fetchUserData();

            // Start cooldown
            this.startCooldown(initData.cooldown_seconds);
          } catch (postbackErr) {
            App.showToast(postbackErr.message, 'error');
            this.resetBtn();
          } finally {
            this.isWatching = false;
          }
        }, 3000);
      } else {
        // Production Monetag Tag Integration
        // If Monetag Web SDK is loaded: window.show_rewarded_tag()
        btnText.innerHTML = '<i class="fa-solid fa-hourglass-half"></i> VERIFYING EVENT...';
        // The backend receives the postback from Monetag server-to-server
        App.showToast('Please complete the sponsor offer to verify your reward.', 'success');
        this.startCooldown(initData.cooldown_seconds);
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
