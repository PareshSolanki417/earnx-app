// ==========================================================================
// EarnX Admin Dashboard Controller
// ==========================================================================

const AdminApp = {
  currentTab: 'dashboard',

  init() {
    if (AdminAPI.getToken()) {
      this.showDashboard();
    } else {
      this.showLogin();
    }
  },

  showLogin() {
    document.getElementById('admin-login-screen').style.display = 'flex';
    document.getElementById('admin-main-app').style.display = 'none';
  },

  showDashboard() {
    document.getElementById('admin-login-screen').style.display = 'none';
    document.getElementById('admin-main-app').style.display = 'flex';
    this.switchTab('dashboard');
  },

  async handleLogin(event) {
    event.preventDefault();
    const u = document.getElementById('login-username').value;
    const p = document.getElementById('login-password').value;
    const btn = document.getElementById('btn-login');

    btn.disabled = true;
    btn.textContent = 'Authenticating...';

    try {
      const res = await AdminAPI.post('/auth/admin/login', { username: u, password: p });
      AdminAPI.setToken(res.access_token);
      this.showDashboard();
    } catch (err) {
      alert('Login failed: ' + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Sign In';
    }
  },

  logout() {
    AdminAPI.clearToken();
    this.showLogin();
  },

  switchTab(tabId) {
    this.currentTab = tabId;

    // Update navigation styles
    document.querySelectorAll('.nav-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
    });

    // Update panes
    document.querySelectorAll('.tab-pane').forEach(pane => {
      pane.classList.toggle('active', pane.id === `tab-${tabId}`);
    });

    const titles = {
      dashboard: 'Dashboard Overview',
      users: 'User Accounts Management',
      withdrawals: 'Withdrawal Payouts Pipeline',
      tasks: 'Configured Task Activities',
      fraud: 'Anti-Fraud & Risk Detection',
      settings: 'App Economics & Reward Settings',
      logs: 'Immutable Admin Action Audit Logs',
    };
    document.getElementById('current-tab-title').textContent = titles[tabId] || 'Admin Console';

    // Load tab-specific data
    if (tabId === 'dashboard') this.fetchDashboard();
    if (tabId === 'users') this.fetchUsers();
    if (tabId === 'withdrawals') this.fetchWithdrawals();
    if (tabId === 'tasks') this.fetchTasks();
    if (tabId === 'fraud') this.fetchFraud();
    if (tabId === 'settings') this.fetchSettings();
    if (tabId === 'logs') this.fetchLogs();
  },

  async fetchDashboard() {
    try {
      const m = await AdminAPI.get('/admin/dashboard');

      document.getElementById('kpi-total-users').textContent = m.total_users;
      document.getElementById('kpi-today-users').textContent = `+${m.todays_users} new today`;
      document.getElementById('kpi-total-coins').textContent = parseFloat(m.total_coins_issued).toLocaleString();
      document.getElementById('kpi-pending-withdrawals').textContent = m.pending_withdrawals_count;
      document.getElementById('kpi-pending-amount').textContent = `₹${parseFloat(m.pending_withdrawals_amount).toFixed(2)}`;
      document.getElementById('kpi-paid-withdrawals').textContent = m.paid_withdrawals_count;
      document.getElementById('kpi-paid-amount').textContent = `₹${parseFloat(m.paid_withdrawals_amount).toFixed(2)}`;

      document.getElementById('kpi-ad-impressions').textContent = m.todays_ad_events;
      document.getElementById('kpi-gross-revenue').textContent = `₹${parseFloat(m.estimated_gross_revenue).toFixed(2)}`;
      document.getElementById('kpi-user-rewards').textContent = `₹${parseFloat(m.estimated_user_rewards).toFixed(2)}`;
      document.getElementById('kpi-margin').textContent = `₹${parseFloat(m.estimated_platform_margin).toFixed(2)}`;

      const envBadge = document.getElementById('env-badge');
      if (envBadge) {
        envBadge.textContent = m.demo_mode ? 'DEMO MODE' : 'PRODUCTION';
        envBadge.style.color = m.demo_mode ? 'var(--gold)' : 'var(--emerald)';
      }
    } catch (e) {
      console.warn('Error loading metrics:', e);
    }
  },

  async fetchUsers() {
    const tbody = document.getElementById('users-table-body');
    try {
      const users = await AdminAPI.get('/admin/users?limit=50');
      if (!users.length) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">No users registered yet.</td></tr>';
        return;
      }

      tbody.innerHTML = users.map(u => `
        <tr>
          <td>#${u.id}</td>
          <td>${u.first_name || ''} (@${u.username || 'no_user'})</td>
          <td><code>${u.referral_code}</code></td>
          <td><strong>${parseFloat(u.available_coins).toLocaleString()}</strong></td>
          <td><span class="badge-env">${u.status}</span></td>
          <td>${u.risk_level}</td>
          <td>${new Date(u.created_at).toLocaleDateString()}</td>
          <td>
            <button class="btn btn-primary btn-small" onclick="AdminApp.openAdjustModal(${u.id}, '${u.username || u.id}', ${u.available_coins})">
              Adjust
            </button>
          </td>
        </tr>
      `).join('');
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-center">Error loading users.</td></tr>`;
    }
  },

  searchUsers() {
    const q = document.getElementById('user-search-input').value;
    const tbody = document.getElementById('users-table-body');
    AdminAPI.get(`/admin/users?search=${encodeURIComponent(q)}`).then(users => {
      tbody.innerHTML = users.map(u => `
        <tr>
          <td>#${u.id}</td>
          <td>${u.first_name || ''} (@${u.username || 'no_user'})</td>
          <td><code>${u.referral_code}</code></td>
          <td><strong>${parseFloat(u.available_coins).toLocaleString()}</strong></td>
          <td><span class="badge-env">${u.status}</span></td>
          <td>${u.risk_level}</td>
          <td>${new Date(u.created_at).toLocaleDateString()}</td>
          <td>
            <button class="btn btn-primary btn-small" onclick="AdminApp.openAdjustModal(${u.id}, '${u.username || u.id}', ${u.available_coins})">
              Adjust
            </button>
          </td>
        </tr>
      `).join('');
    });
  },

  openAdjustModal(userId, username, currentCoins) {
    document.getElementById('adjust-user-id').value = userId;
    document.getElementById('adjust-user-title').textContent = `User #${userId} (@${username})`;
    document.getElementById('adjust-user-details').innerHTML = `Current Balance: <strong>${parseFloat(currentCoins).toLocaleString()} Coins</strong>`;
    document.getElementById('form-adjust-balance').reset();
    document.getElementById('modal-adjust-user').classList.add('open');
  },

  async submitBalanceAdjustment(event) {
    event.preventDefault();
    const userId = document.getElementById('adjust-user-id').value;
    const amount = parseFloat(document.getElementById('adjust-coins-input').value);
    const reason = document.getElementById('adjust-reason-input').value;

    try {
      const res = await AdminAPI.post(`/admin/users/${userId}/adjust`, {
        amount_coins: amount,
        reason: reason
      });
      alert(res.message);
      this.closeModal('modal-adjust-user');
      this.fetchUsers();
    } catch (err) {
      alert(err.message);
    }
  },

  async fetchWithdrawals() {
    const tbody = document.getElementById('withdrawals-table-body');
    const filter = document.getElementById('withdrawal-filter-status').value;
    const url = filter ? `/admin/withdrawals?status_filter=${filter}` : '/admin/withdrawals';

    try {
      const withdrawals = await AdminAPI.get(url);
      if (!withdrawals.length) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center">No withdrawal requests found.</td></tr>';
        return;
      }

      tbody.innerHTML = withdrawals.map(w => `
        <tr>
          <td><code>${w.id.substring(0, 8)}</code></td>
          <td>#${w.user_id}</td>
          <td><strong>₹${parseFloat(w.amount_rupees).toFixed(2)}</strong></td>
          <td>${parseFloat(w.coins_deducted).toLocaleString()}</td>
          <td>${w.payout_method}</td>
          <td>${w.payout_account}</td>
          <td><span class="badge-env">${w.status}</span></td>
          <td>${new Date(w.created_at).toLocaleDateString()}</td>
          <td>
            <button class="btn btn-primary btn-small" onclick="AdminApp.openWithdrawalActionModal('${w.id}', '${w.status}')">
              Action
            </button>
          </td>
        </tr>
      `).join('');
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="9" class="text-center">Error loading withdrawals.</td></tr>`;
    }
  },

  openWithdrawalActionModal(id, currentStatus) {
    document.getElementById('action-withdrawal-id').value = id;
    document.getElementById('action-status-select').value = currentStatus === 'PENDING' ? 'APPROVED' : currentStatus;
    document.getElementById('form-withdrawal-action').reset();
    document.getElementById('modal-withdrawal-action').classList.add('open');
  },

  async submitWithdrawalAction(event) {
    event.preventDefault();
    const id = document.getElementById('action-withdrawal-id').value;
    const st = document.getElementById('action-status-select').value;
    const notes = document.getElementById('action-notes-input').value;

    try {
      await AdminAPI.post(`/admin/withdrawals/${id}/action`, {
        status: st,
        admin_notes: notes || undefined
      });
      alert(`Withdrawal marked as ${st}!`);
      this.closeModal('modal-withdrawal-action');
      this.fetchWithdrawals();
      this.fetchDashboard();
    } catch (err) {
      alert(err.message);
    }
  },

  async fetchTasks() {
    const tbody = document.getElementById('tasks-table-body');
    try {
      const tasks = await AdminAPI.get('/admin/tasks');
      tbody.innerHTML = tasks.map(t => `
        <tr>
          <td>#${t.id}</td>
          <td>${t.title}</td>
          <td>+${parseFloat(t.reward_coins).toFixed(0)} Coins</td>
          <td>${t.verification_method}</td>
          <td><span class="badge-env">${t.status}</span></td>
          <td>${t.action_url ? `<a href="${t.action_url}" target="_blank" style="color: var(--emerald)">Link</a>` : '—'}</td>
        </tr>
      `).join('');
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center">Error loading tasks.</td></tr>`;
    }
  },

  openCreateTaskModal() {
    document.getElementById('form-create-task').reset();
    document.getElementById('modal-create-task').classList.add('open');
  },

  async submitCreateTask(event) {
    event.preventDefault();
    const payload = {
      title: document.getElementById('task-title').value,
      description: document.getElementById('task-desc').value,
      reward_coins: parseFloat(document.getElementById('task-reward').value),
      action_url: document.getElementById('task-url').value || undefined,
      verification_method: document.getElementById('task-method').value,
    };

    try {
      await AdminAPI.post('/admin/tasks', payload);
      alert('Task created successfully!');
      this.closeModal('modal-create-task');
      this.fetchTasks();
    } catch (err) {
      alert(err.message);
    }
  },

  async fetchFraud() {
    const tbody = document.getElementById('fraud-table-body');
    try {
      const events = await AdminAPI.get('/admin/fraud');
      if (!events.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No fraud events detected. Platform healthy.</td></tr>';
        return;
      }
      tbody.innerHTML = events.map(f => `
        <tr>
          <td>#${f.id}</td>
          <td>${f.user_id ? '#' + f.user_id : 'System'}</td>
          <td><code>${f.event_type}</code></td>
          <td><span class="badge-env" style="color: var(--red);">${f.severity}</span></td>
          <td>${f.details}</td>
          <td>${f.ip_address || '—'}</td>
          <td>${new Date(f.created_at).toLocaleString()}</td>
        </tr>
      `).join('');
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center">Error loading fraud logs.</td></tr>`;
    }
  },

  async fetchSettings() {
    const container = document.getElementById('settings-container');
    try {
      const settings = await AdminAPI.get('/admin/settings');
      const map = {};
      settings.forEach(s => { map[s.key] = s.value; });

      const cpr = parseFloat(map['COINS_PER_RUPEE'] || 100);

      container.innerHTML = `
        <div style="display: flex; flex-direction: column; gap: 24px;">
          <!-- Group 1: Ad Earnings -->
          <div class="settings-group-card" style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 20px;">
            <h4 style="color: var(--gold); margin-bottom: 16px; font-size: 16px;">
              <i class="fa-solid fa-clapperboard"></i> 1. Watch & Earn (Ad Reward Settings)
            </h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
              <div class="setting-field">
                <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 6px;">
                  Coins per Ad View:
                </label>
                <div style="display: flex; gap: 8px;">
                  <input type="number" step="0.5" id="setting-AD_REWARD_COINS" value="${map['AD_REWARD_COINS'] || '10.0'}" style="flex: 1; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-surface); color: #fff;" oninput="AdminApp.calcAdRupees()" />
                  <button class="btn btn-primary btn-small" onclick="AdminApp.saveSetting('AD_REWARD_COINS')">Save</button>
                </div>
                <small id="ad-reward-calc" style="color: var(--emerald); font-size: 12px; display: block; margin-top: 4px;">
                  = ₹${((parseFloat(map['AD_REWARD_COINS'] || 10) / cpr)).toFixed(2)} per ad view
                </small>
              </div>

              <div class="setting-field">
                <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 6px;">
                  Estimated Ad Revenue (₹ per view):
                </label>
                <div style="display: flex; gap: 8px;">
                  <input type="number" step="0.01" id="setting-ESTIMATED_REVENUE_PER_AD_RUPEES" value="${map['ESTIMATED_REVENUE_PER_AD_RUPEES'] || '0.35'}" style="flex: 1; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-surface); color: #fff;" />
                  <button class="btn btn-primary btn-small" onclick="AdminApp.saveSetting('ESTIMATED_REVENUE_PER_AD_RUPEES')">Save</button>
                </div>
                <small style="color: var(--text-sub); font-size: 12px; display: block; margin-top: 4px;">Used for calculating platform profit margin</small>
              </div>

              <div class="setting-field">
                <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 6px;">
                  Daily Ad Limit per User (Ads/day):
                </label>
                <div style="display: flex; gap: 8px;">
                  <input type="number" id="setting-DAILY_AD_LIMIT" value="${map['DAILY_AD_LIMIT'] || '20'}" min="1" max="100" style="flex: 1; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-surface); color: #fff;" />
                  <button class="btn btn-primary btn-small" onclick="AdminApp.saveSetting('DAILY_AD_LIMIT')">Save</button>
                </div>
                <small style="color: var(--emerald); font-size: 12px; display: block; margin-top: 4px;">Recommended: 15 to 25 to maximize network CPM rates</small>
              </div>
            </div>
          </div>

          <!-- Group 2: Currency & Payouts -->
          <div class="settings-group-card" style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 20px;">
            <h4 style="color: var(--emerald); margin-bottom: 16px; font-size: 16px;">
              <i class="fa-solid fa-coins"></i> 2. Currency Conversion & Payout Thresholds
            </h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
              <div class="setting-field">
                <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 6px;">
                  Coins per ₹1.00 (Conversion Rate):
                </label>
                <div style="display: flex; gap: 8px;">
                  <input type="number" id="setting-COINS_PER_RUPEE" value="${map['COINS_PER_RUPEE'] || '100.0'}" style="flex: 1; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-surface); color: #fff;" oninput="AdminApp.calcAdRupees()" />
                  <button class="btn btn-primary btn-small" onclick="AdminApp.saveSetting('COINS_PER_RUPEE')">Save</button>
                </div>
                <small style="color: var(--text-sub); font-size: 12px; display: block; margin-top: 4px;">Default: 100 coins = ₹1.00</small>
              </div>

              <div class="setting-field">
                <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 6px;">
                  Minimum Withdrawal Amount (₹):
                </label>
                <div style="display: flex; gap: 8px;">
                  <input type="number" id="setting-MIN_WITHDRAWAL_RUPEES" value="${map['MIN_WITHDRAWAL_RUPEES'] || '50.0'}" style="flex: 1; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-surface); color: #fff;" />
                  <button class="btn btn-primary btn-small" onclick="AdminApp.saveSetting('MIN_WITHDRAWAL_RUPEES')">Save</button>
                </div>
                <small style="color: var(--text-sub); font-size: 12px; display: block; margin-top: 4px;">Minimum threshold for UPI and Bank transfer</small>
              </div>
            </div>
          </div>

          <!-- Group 3: Referral Engine -->
          <div class="settings-group-card" style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 20px;">
            <h4 style="color: var(--blue, #3b82f6); margin-bottom: 16px; font-size: 16px;">
              <i class="fa-solid fa-users"></i> 3. Referral Program Settings
            </h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
              <div class="setting-field">
                <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 6px;">
                  Referral Bonus (Coins per successful invite):
                </label>
                <div style="display: flex; gap: 8px;">
                  <input type="number" id="setting-REFERRAL_BONUS_COINS" value="${map['REFERRAL_BONUS_COINS'] || '50.0'}" style="flex: 1; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-surface); color: #fff;" />
                  <button class="btn btn-primary btn-small" onclick="AdminApp.saveSetting('REFERRAL_BONUS_COINS')">Save</button>
                </div>
              </div>

              <div class="setting-field">
                <label style="font-size: 13px; font-weight: 600; display: block; margin-bottom: 6px;">
                  Qualifying Ads Required:
                </label>
                <div style="display: flex; gap: 8px;">
                  <input type="number" id="setting-REFERRAL_QUALIFYING_ACTIONS" value="${map['REFERRAL_QUALIFYING_ACTIONS'] || '3'}" style="flex: 1; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); background: var(--bg-surface); color: #fff;" />
                  <button class="btn btn-primary btn-small" onclick="AdminApp.saveSetting('REFERRAL_QUALIFYING_ACTIONS')">Save</button>
                </div>
                <small style="color: var(--text-sub); font-size: 12px; display: block; margin-top: 4px;">Ads invited user must watch before bonus unlocks</small>
              </div>
            </div>
          </div>

          <!-- Group 4: Daily Bonus 7-Day Streak -->
          <div class="settings-group-card" style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 20px;">
            <h4 style="color: #a855f7; margin-bottom: 16px; font-size: 16px;">
              <i class="fa-solid fa-gift"></i> 4. 7-Day Streak Daily Bonus Coins
            </h4>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px;">
              ${[1,2,3,4,5,6,7].map(day => `
                <div class="setting-field" style="background: rgba(0,0,0,0.2); padding: 10px; border-radius: 8px; text-align: center;">
                  <span style="font-size: 12px; font-weight: 700; color: var(--text-sub);">Day ${day}</span>
                  <input type="number" id="setting-DAILY_BONUS_DAY_${day}" value="${map[`DAILY_BONUS_DAY_${day}`] || (day * 10)}" style="width: 100%; margin: 6px 0; padding: 6px; text-align: center; border-radius: 4px; border: 1px solid var(--border-color); background: var(--bg-surface); color: #fff;" />
                  <button class="btn btn-primary btn-small" style="width: 100%; font-size: 11px; padding: 4px;" onclick="AdminApp.saveSetting('DAILY_BONUS_DAY_${day}')">Save</button>
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      `;
    } catch (e) {
      container.innerHTML = '<p style="color: var(--red);">Error loading settings. Please try refreshing.</p>';
    }
  },

  calcAdRupees() {
    const coins = parseFloat(document.getElementById('setting-AD_REWARD_COINS')?.value || 10);
    const cpr = parseFloat(document.getElementById('setting-COINS_PER_RUPEE')?.value || 100);
    const el = document.getElementById('ad-reward-calc');
    if (el && cpr > 0) {
      el.innerText = `= ₹${(coins / cpr).toFixed(2)} per ad view`;
    }
  },

  async saveSetting(key) {
    const input = document.getElementById(`setting-${key}`);
    if (!input) return;
    const val = input.value;
    try {
      await AdminAPI.put(`/admin/settings/${key}`, { value: val });
      alert(`✅ Setting '${key}' saved successfully! New value: ${val}`);
      this.fetchSettings();
    } catch (err) {
      alert(`Error saving setting: ${err.message}`);
    }
  },

  async fetchLogs() {
    const tbody = document.getElementById('logs-table-body');
    try {
      const logs = await AdminAPI.get('/admin/logs');
      if (!logs.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No admin actions recorded yet.</td></tr>';
        return;
      }
      tbody.innerHTML = logs.map(l => `
        <tr>
          <td>#${l.id}</td>
          <td>@${l.admin_username}</td>
          <td><code>${l.action_type}</code></td>
          <td>${l.target_user_id ? '#' + l.target_user_id : '—'}</td>
          <td>${l.details}</td>
          <td>${l.ip_address || '—'}</td>
          <td>${new Date(l.created_at).toLocaleString()}</td>
        </tr>
      `).join('');
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center">Error loading audit logs.</td></tr>`;
    }
  },

  closeModal(modalId) {
    document.getElementById(modalId).classList.remove('open');
  }
};

document.addEventListener('DOMContentLoaded', () => {
  AdminApp.init();
});
