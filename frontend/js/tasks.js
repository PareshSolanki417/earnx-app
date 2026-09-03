// ==========================================================================
// EarnX Tasks & Daily Bonus Manager
// ==========================================================================

const TasksManager = {
  tasks: [],

  async openOfferwall() {
    try {
      App.showToast('Loading Mega Offerwall missions...', 'info');
      const res = await API.get('/paymentwall/widget-url');
      if (res && res.url) {
        if (window.Telegram?.WebApp?.openLink) {
          window.Telegram.WebApp.openLink(res.url);
        } else {
          window.open(res.url, '_blank');
        }
      }
    } catch (e) {
      console.warn('Could not open offerwall:', e);
      App.showToast('Could not load offerwall. Please try again.', 'error');
    }
  },

  async fetchTasks() {
    const container = document.getElementById('tasks-list-container');
    try {
      this.tasks = await API.get('/tasks');
      this.renderTasks();
      
      const homeTaskCount = document.getElementById('home-tasks-status');
      const uncompleted = this.tasks.filter(t => !t.is_completed).length;
      if (homeTaskCount) homeTaskCount.textContent = `${uncompleted} Available`;
    } catch (e) {
      if (container) container.innerHTML = `<div class="empty-state">Could not load tasks.</div>`;
    }
  },

  renderTasks() {
    const container = document.getElementById('tasks-list-container');
    if (!container) return;

    if (!this.tasks.length) {
      container.innerHTML = `<div class="empty-state">No active tasks available right now. Check back soon!</div>`;
      return;
    }

    container.innerHTML = this.tasks.map(task => {
      const isCompleted = task.is_completed;
      let iconClass = 'fa-solid fa-list-check';
      if (task.icon === 'telegram') iconClass = 'fa-brands fa-telegram';
      if (task.icon === 'globe') iconClass = 'fa-solid fa-globe';
      if (task.icon === 'video') iconClass = 'fa-solid fa-video';
      if (task.icon === 'users') iconClass = 'fa-solid fa-users';

      return `
        <div class="task-item-card">
          <div class="task-item-left">
            <div class="task-icon">
              <i class="${iconClass}"></i>
            </div>
            <div class="task-details">
              <h4>${task.title}</h4>
              <p>${task.description}</p>
              <span class="task-reward-tag">+${parseFloat(task.reward_coins).toFixed(0)} Coins</span>
            </div>
          </div>
          <div class="task-item-right">
            ${isCompleted 
              ? `<button class="btn btn-action-done"><i class="fa-solid fa-check"></i> Done</button>`
              : `<button class="btn btn-action-claim" onclick="TasksManager.startAndCompleteTask(${task.id}, '${task.action_url || ''}')">Start</button>`
            }
          </div>
        </div>
      `;
    }).join('');
  },

  async startAndCompleteTask(taskId, actionUrl) {
    if (actionUrl && actionUrl.startsWith('http')) {
      window.open(actionUrl, '_blank');
    }

    App.showToast('Verifying task completion...', 'success');

    try {
      const res = await API.post(`/tasks/${taskId}/complete`, {});
      App.showToast(res.message, 'success');
      await this.fetchTasks();
      await WalletManager.fetchWallet();
      App.fetchUserData();
    } catch (err) {
      App.showToast(err.message, 'error');
    }
  },

  async fetchDailyBonusStatus() {
    try {
      const data = await API.get('/tasks/daily-bonus/status');
      this.renderDailyBonus(data);
    } catch (e) {
      console.warn('Could not fetch daily bonus status:', e);
    }
  },

  renderDailyBonus(data) {
    const streakEl = document.getElementById('bonus-streak-count');
    const homeStreakEl = document.getElementById('home-streak-status');
    const daysContainer = document.getElementById('streak-days-container');
    const claimBtn = document.getElementById('btn-claim-bonus');
    const claimBtnText = document.getElementById('btn-claim-text');

    if (streakEl) streakEl.textContent = data.current_streak;
    if (homeStreakEl) homeStreakEl.textContent = `Streak: ${data.current_streak} Days`;

    if (daysContainer) {
      daysContainer.innerHTML = data.days.map((d, index) => {
        const isCurrent = d.is_current;
        const isClaimed = d.is_claimed;
        const isDay7 = d.day === 7;
        let cardClass = 'streak-day-card';
        if (isClaimed) cardClass += ' claimed';
        if (isCurrent && data.can_claim_today) cardClass += ' current';
        if (isDay7) cardClass += ' span-2';

        return `
          <div class="${cardClass}">
            <span class="streak-day-title">Day ${d.day}</span>
            <div class="streak-day-icon">
              <i class="fa-solid ${isClaimed ? 'fa-circle-check' : (isDay7 ? 'fa-crown' : 'fa-coins')}"></i>
            </div>
            <span class="streak-day-coins">+${parseFloat(d.coins).toFixed(0)}</span>
          </div>
        `;
      }).join('');
    }

    if (claimBtn && claimBtnText) {
      if (data.can_claim_today) {
        claimBtn.disabled = false;
        claimBtnText.textContent = `CLAIM +${parseFloat(data.today_coins).toFixed(0)} COINS`;
      } else {
        claimBtn.disabled = true;
        claimBtnText.textContent = 'ALREADY CLAIMED TODAY';
      }
    }
  },

  async claimDailyBonus() {
    const claimBtn = document.getElementById('btn-claim-bonus');
    if (claimBtn) claimBtn.disabled = true;

    try {
      const res = await API.post('/tasks/daily-bonus/claim', {});
      App.showToast(res.message, 'success');
      await this.fetchDailyBonusStatus();
      await WalletManager.fetchWallet();
      App.fetchUserData();
    } catch (err) {
      App.showToast(err.message, 'error');
      if (claimBtn) claimBtn.disabled = false;
    }
  }
};
