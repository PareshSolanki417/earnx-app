// ==========================================================================
// EarnX Master Client Application Controller
// ==========================================================================

const App = {
  user: null,
  currentScreen: 'home',

  async init() {
    console.log('Initializing EarnX Application...');
    i18n.applyTranslations();

    // 1. Initialize Telegram WebApp SDK
    const tg = window.Telegram?.WebApp;
    if (tg) {
      try {
        tg.ready();
        tg.expand();
      } catch (e) {
        console.warn('Telegram SDK initialization note:', e);
      }
    }

    // 2. Authenticate session
    await this.authenticate();

    // 3. Load initial dashboard data
    await this.fetchUserData();
    await WalletManager.fetchWallet();
    await TasksManager.fetchDailyBonusStatus();
    await AdsManager.checkStatus();

    // 4. Setup Event Listeners
    this.setupEventListeners();
  },

  async authenticate() {
    let initData = window.Telegram?.WebApp?.initData;
    const urlParams = new URLSearchParams(window.location.search);
    const refCode = urlParams.get('startapp') || urlParams.get('start') || null;

    // Fallback for standalone web browser and mobile visitors outside Telegram
    if (!initData) {
      let webUserId = localStorage.getItem('earnx_web_user_id');
      if (!webUserId) {
        webUserId = String(Math.floor(10000000 + Math.random() * 89999999));
        localStorage.setItem('earnx_web_user_id', webUserId);
      }
      console.info('Running in Web Browser mode with persistent user ID:', webUserId);
      initData = `web_user_${webUserId}`;
    }

    try {
      const res = await API.post('/auth/telegram', {
        init_data: initData,
        referral_code: refCode,
      });

      API.setToken(res.token.access_token);
      this.user = res.user;
      console.log('Authenticated successfully as User #', this.user.id);
    } catch (err) {
      console.error('Authentication failure:', err);
      this.showToast('Authentication failed: ' + err.message, 'error');
    }
  },

  async fetchUserData() {
    try {
      const profile = await API.get('/user/me');
      this.user = profile;
      this.renderUserProfile(profile);
    } catch (e) {
      console.warn('Could not fetch user profile:', e);
    }
  },

  renderUserProfile(u) {
    const avatar = u.photo_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${u.username || u.id}`;
    const name = u.first_name || u.username || `User #${u.id}`;
    const handle = u.username ? `@${u.username}` : `ID: ${u.id}`;

    // Header
    const hAvatar = document.getElementById('header-avatar');
    const hName = document.getElementById('header-username');
    if (hAvatar) hAvatar.src = avatar;
    if (hName) hName.textContent = name;

    // Profile Screen
    const pAvatar = document.getElementById('profile-avatar');
    const pName = document.getElementById('profile-fullname');
    const pHandle = document.getElementById('profile-username');
    const pRisk = document.getElementById('profile-risk');

    if (pAvatar) pAvatar.src = avatar;
    if (pName) pName.textContent = name;
    if (pHandle) pHandle.textContent = handle;
    if (pRisk) {
      pRisk.className = `risk-pill ${u.risk_level.toLowerCase()}`;
      pRisk.innerHTML = `<i class="fa-solid fa-shield"></i> ${u.risk_level}`;
    }

    // Referral Screen
    const refCode = document.getElementById('ref-code-display');
    if (refCode) refCode.textContent = u.referral_code;
  },

  navigateTo(screenId) {
    this.currentScreen = screenId;

    // Toggle screen visibility
    document.querySelectorAll('.view-screen').forEach(el => {
      el.classList.remove('active');
    });

    const targetEl = document.getElementById(`view-${screenId}`);
    if (targetEl) targetEl.classList.add('active');

    // Update bottom navigation bar
    document.querySelectorAll('.nav-item').forEach(el => {
      el.classList.toggle('active', el.getAttribute('data-target') === screenId);
    });

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Contextual data refresh
    if (screenId === 'wallet') {
      WalletManager.fetchWallet();
      WalletManager.fetchTransactions();
    } else if (screenId === 'tasks') {
      TasksManager.fetchTasks();
    } else if (screenId === 'daily-bonus') {
      TasksManager.fetchDailyBonusStatus();
    } else if (screenId === 'referral') {
      this.fetchReferralData();
    } else if (screenId === 'watch') {
      AdsManager.checkStatus();
    }
  },

  async fetchReferralData() {
    try {
      const data = await API.get('/referral');
      document.getElementById('ref-code-display').textContent = data.referral_code;
      document.getElementById('ref-total-count').textContent = data.total_referred;
      document.getElementById('ref-qualified-count').textContent = data.qualified_referred;
      document.getElementById('ref-coins-earned').textContent = parseFloat(data.coins_earned).toFixed(0);

      const listContainer = document.getElementById('referred-list-container');
      if (listContainer) {
        if (!data.recent_referrals.length) {
          listContainer.innerHTML = '<div class="empty-state">No friends invited yet. Share your link to get started!</div>';
        } else {
          listContainer.innerHTML = data.recent_referrals.map(ref => `
            <div class="ref-user-item">
              <span>${ref.first_name || ref.username || 'Friend'}</span>
              <span class="${ref.is_qualified ? 'user-tier-badge' : 'sub-stat-lbl'}">
                ${ref.is_qualified ? '<i class="fa-solid fa-check"></i> Qualified (+50)' : 'In Progress'}
              </span>
            </div>
          `).join('');
        }
      }
    } catch (e) {
      console.warn('Could not load referral stats:', e);
    }
  },

  copyReferralCode() {
    if (!this.user) return;
    navigator.clipboard.writeText(this.user.referral_code);
    this.showToast(`Referral code ${this.user.referral_code} copied!`, 'success');
  },

  copyReferralLink() {
    if (!this.user) return;
    const link = `https://t.me/EarnXBot?start=${this.user.referral_code}`;
    navigator.clipboard.writeText(link);
    this.showToast('Referral invite link copied to clipboard!', 'success');
  },

  shareToTelegram() {
    if (!this.user) return;
    const text = encodeURIComponent(
      `Join EarnX and earn real coins by watching sponsored videos and completing quick tasks! Use my invite code: ${this.user.referral_code}`
    );
    const link = encodeURIComponent(`https://t.me/EarnXBot?start=${this.user.referral_code}`);
    window.open(`https://t.me/share/url?url=${link}&text=${text}`, '_blank');
  },

  openWithdrawModal() {
    WalletManager.fetchWallet();
    const modal = document.getElementById('withdraw-modal');
    if (modal) modal.classList.add('open');
  },

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('open');
  },

  openPolicyModal(policyType) {
    const titleEl = document.getElementById('policy-modal-title');
    const contentEl = document.getElementById('policy-modal-content');
    const policies = {
      privacy: {
        title: 'Privacy Policy',
        content: `
          <h4>1. Information We Collect</h4>
          <p>EarnX collects your Telegram identifier (ID, first name, username) solely for authentication, balance tracking, and fraud prevention.</p>
          <h4>2. Data Security & Storage</h4>
          <p>We do not sell personal data. Payout details (e.g. UPI IDs) are encrypted and accessed exclusively for verified payout disbursement.</p>
          <h4>3. Third-Party Ad Networks</h4>
          <p>We work with vetted ad networks (such as Monetag). Ad impressions and interactions are verified securely via server callbacks.</p>
        `
      },
      terms: {
        title: 'Terms & Conditions',
        content: `
          <h4>1. Ad-Supported Platform</h4>
          <p>EarnX is an ad-supported rewards platform. We do not provide gambling, betting, lottery, or investment doubling schemes.</p>
          <h4>2. Prohibited Activities</h4>
          <p>Automated scripts, bots, fake accounts, self-referrals, or artificial clicking are strictly prohibited and result in immediate account restriction.</p>
          <h4>3. Fair Use</h4>
          <p>Reward balances are subject to activity verification and compliance reviews.</p>
        `
      },
      rewards: {
        title: 'Reward Policy',
        content: `
          <h4>1. Legitimate Activities</h4>
          <p>Coins are awarded for verified sponsor video views, authorized tasks, and qualified friend referrals.</p>
          <h4>2. Conversion & Payouts</h4>
          <p>Coin exchange rates (e.g. 100 coins = ₹1) are transparently configured based on platform advertising economics.</p>
        `
      },
      withdrawals: {
        title: 'Withdrawal Policy',
        content: `
          <h4>1. Minimum Threshold</h4>
          <p>The standard minimum withdrawal is ₹50.00. Requests below the minimum cannot be submitted.</p>
          <h4>2. Processing & Audit</h4>
          <p>Withdrawals are reviewed and disbursed within 24–48 hours via UPI or Bank Transfer. If an application is rejected, coins are refunded to your wallet.</p>
        `
      },
      support: {
        title: 'Contact & Support',
        content: `
          <h4>Need Assistance?</h4>
          <p>For payout inquiries, task verification, or account reviews, please reach out via our official support channels:</p>
          <p><strong>Telegram:</strong> <a href="https://t.me/SolankiPareshm" target="_blank" style="color:var(--primary)">@SolankiPareshm</a></p>
          <p><strong>Channel:</strong> <a href="https://t.me/EarnX_App" target="_blank" style="color:var(--primary)">@EarnX_App</a></p>
          <p><strong>Email:</strong> support@earnx.app</p>
        `
      }
    };

    const sel = policies[policyType] || policies.terms;
    if (titleEl) titleEl.textContent = sel.title;
    if (contentEl) contentEl.innerHTML = sel.content;

    const modal = document.getElementById('policy-modal');
    if (modal) modal.classList.add('open');
  },

  toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('earnx_theme', next);

    const icon = document.getElementById('theme-icon');
    const label = document.getElementById('theme-label-text');
    if (icon) icon.className = next === 'dark' ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
    if (label) label.textContent = next === 'dark' ? 'Dark Mode' : 'Light Mode';
  },

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? 'fa-circle-check' : (type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-info');
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  },

  setupEventListeners() {
    const themeBtn = document.getElementById('theme-toggle-btn');
    if (themeBtn) themeBtn.addEventListener('click', () => this.toggleTheme());

    const savedTheme = localStorage.getItem('earnx_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    const icon = document.getElementById('theme-icon');
    if (icon) icon.className = savedTheme === 'dark' ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
  }
};

// Start application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
