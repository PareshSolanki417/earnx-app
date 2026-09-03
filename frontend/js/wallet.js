// ==========================================================================
// EarnX Wallet & Ledger Manager
// ==========================================================================

const WalletManager = {
  walletData: null,

  async fetchWallet() {
    try {
      this.walletData = await API.get('/wallet');
      this.renderWallet();
    } catch (e) {
      console.warn('Failed to load wallet data:', e);
    }
  },

  renderWallet() {
    if (!this.walletData) return;

    const rupees = parseFloat(this.walletData.rupee_value).toFixed(2);
    const coins = parseFloat(this.walletData.available_coins).toLocaleString();

    // Home Screen
    const homeRupees = document.getElementById('home-balance-rupees');
    const homeCoins = document.getElementById('home-coins');
    if (homeRupees) homeRupees.textContent = rupees;
    if (homeCoins) homeCoins.textContent = coins;

    // Wallet Screen
    const wRupees = document.getElementById('wallet-balance-rupees');
    const wCoins = document.getElementById('wallet-coins');
    const wPending = document.getElementById('wallet-pending-coins');
    const wLifetime = document.getElementById('wallet-lifetime-earned');
    const modalRupees = document.getElementById('modal-avail-rupees');

    if (wRupees) wRupees.textContent = rupees;
    if (wCoins) wCoins.textContent = coins;
    if (wPending) wPending.textContent = `${parseFloat(this.walletData.pending_coins).toFixed(0)} Coins`;
    if (wLifetime) wLifetime.textContent = `${parseFloat(this.walletData.lifetime_earned).toFixed(0)} Coins`;
    if (modalRupees) modalRupees.textContent = `₹${rupees}`;
  },

  async fetchTransactions() {
    const container = document.getElementById('tx-list-container');
    try {
      const data = await API.get('/wallet/transactions?limit=25');
      if (!container) return;

      if (!data.items.length) {
        container.innerHTML = `<div class="empty-state">No transactions recorded yet. Start watching ads or complete tasks!</div>`;
        return;
      }

      container.innerHTML = data.items.map(tx => {
        const isCredit = parseFloat(tx.amount) > 0;
        const formattedAmount = Math.abs(parseFloat(tx.amount)).toFixed(0);
        const dateStr = new Date(tx.created_at).toLocaleDateString(undefined, {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        });

        let typeLabel = tx.type.replace('_', ' ');
        let icon = 'fa-arrow-down-left';
        if (tx.type === 'AD_REWARD') { icon = 'fa-play'; typeLabel = 'Video Ad Reward'; }
        if (tx.type === 'DAILY_BONUS') { icon = 'fa-gift'; typeLabel = 'Daily Streak Bonus'; }
        if (tx.type === 'TASK_REWARD') { icon = 'fa-list-check'; typeLabel = 'Task Reward'; }
        if (tx.type === 'REFERRAL_REWARD') { icon = 'fa-users'; typeLabel = 'Referral Bonus'; }
        if (tx.type === 'WITHDRAWAL') { icon = 'fa-paper-plane'; typeLabel = 'Withdrawal Payout'; }
        if (tx.type === 'ADJUSTMENT') { icon = 'fa-sliders'; typeLabel = 'Wallet Adjustment'; }

        return `
          <div class="tx-item">
            <div class="tx-item-left">
              <div class="tx-icon-box ${isCredit ? 'credit' : 'debit'}">
                <i class="fa-solid ${icon}"></i>
              </div>
              <div>
                <div class="tx-title">${typeLabel}</div>
                <div class="tx-date">${dateStr}</div>
              </div>
            </div>
            <div class="tx-item-right">
              <div class="tx-amount ${isCredit ? 'credit' : 'debit'}">
                ${isCredit ? '+' : '-'}${formattedAmount} Coins
              </div>
              <span class="tx-status-badge">${tx.status}</span>
            </div>
          </div>
        `;
      }).join('');
    } catch (e) {
      if (container) container.innerHTML = `<div class="empty-state">Could not load transactions.</div>`;
    }
  },

  selectMethod(method) {
    document.getElementById('withdraw-method').value = method;
    const tabUpi = document.getElementById('tab-upi');
    const tabBank = document.getElementById('tab-bank');
    const labelAccount = document.getElementById('label-account');
    const inputAccount = document.getElementById('withdraw-account');

    if (method === 'UPI') {
      tabUpi.classList.add('active');
      tabBank.classList.remove('active');
      labelAccount.textContent = 'UPI ID (e.g. yourname@upi)';
      inputAccount.placeholder = 'username@okaxis / 9876543210@paytm';
    } else {
      tabBank.classList.add('active');
      tabUpi.classList.remove('active');
      labelAccount.textContent = 'Bank Account Number & IFSC Code';
      inputAccount.placeholder = 'Account: 1234567890, IFSC: SBIN0001234';
    }
  },

  async submitWithdrawal(event) {
    event.preventDefault();
    const btn = document.getElementById('btn-submit-withdrawal');
    btn.disabled = true;
    btn.textContent = 'Submitting Request...';

    const amountRupees = parseFloat(document.getElementById('withdraw-amount').value);
    const method = document.getElementById('withdraw-method').value;
    const account = document.getElementById('withdraw-account').value;
    const holderName = document.getElementById('withdraw-name').value;

    try {
      const res = await API.post('/withdrawals', {
        amount_rupees: amountRupees,
        payout_method: method,
        payout_account: account,
        account_holder_name: holderName || undefined
      });

      App.showToast('Withdrawal request submitted! It will be reviewed within 24h.', 'success');
      App.closeModal('withdraw-modal');
      
      // Reset form
      document.getElementById('withdraw-form').reset();

      // Refresh wallet & transactions
      await this.fetchWallet();
      await this.fetchTransactions();
    } catch (err) {
      App.showToast(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Submit Withdrawal Request';
    }
  }
};
