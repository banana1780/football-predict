const api = require('../../utils/api');

Page({
  data: {
    matchId: null,
    team_a: '', team_b: '',
    elo_a: 0, elo_b: 0,
    xg_a: 0, xg_b: 0,
    group: '', time_str: '',
    unlocked: false,
    credits: 0,
    prediction: null
  },

  onLoad(options) {
    const id = parseInt(options.id);
    this.setData({ matchId: id });
    this.loadPreview(id);
    this.loadCredits();
    this.checkLocked(id);
  },

  loadPreview(id) {
    api.getPreview(id).then(data => {
      this.setData({
        team_a: data.team_a,
        team_b: data.team_b,
        elo_a: data.elo_a,
        elo_b: data.elo_b,
        xg_a: data.xg_a,
        xg_b: data.xg_b,
        group: data.group_name || '',
        time_str: data.match_time || '',
        unlocked: !data.locked
      });
      if (!data.locked) {
        this.loadFull(id);
      }
    });
  },

  loadFull(id) {
    api.getFull(id, 'all').then(data => {
      this.setData({ prediction: data });
    });
  },

  checkLocked(id) {
    api.getCredits().then(data => {
      this.setData({ credits: data.credits || 0 });
    });
  },

  loadCredits() {
    api.getCredits().then(data => {
      this.setData({ credits: data.credits || 0 });
    });
  },

  unlock() {
    if (this.data.credits <= 0) {
      wx.showModal({
        title: '余额不足',
        content: '请先充值',
        success: (res) => {
          if (res.confirm) {
            wx.navigateTo({ url: '/pages/pay/pay' });
          }
        }
      });
      return;
    }

    wx.showModal({
      title: '确认解锁',
      content: '消耗1次解锁机会查看完整预测？',
      success: (res) => {
        if (res.confirm) {
          this.doUnlock();
        }
      }
    });
  },

  doUnlock() {
    wx.showLoading({ title: '解锁中...' });
    api.unlockMatch(this.data.matchId).then(data => {
      wx.hideLoading();
      if (data.success) {
        this.setData({ unlocked: true });
        this.loadFull(this.data.matchId);
        this.loadCredits();
        wx.showToast({ title: '解锁成功', icon: 'success' });
      } else {
        wx.showToast({ title: data.error || '解锁失败', icon: 'none' });
      }
    }).catch(() => {
      wx.hideLoading();
      wx.showToast({ title: '网络错误', icon: 'none' });
    });
  }
});
