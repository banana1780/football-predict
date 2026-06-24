const api = require('../../utils/api');
const app = getApp();

Page({
  data: {
    matches: [],
    credits: 0,
    today: ''
  },

  onLoad() {
    const now = new Date();
    this.setData({
      today: now.toISOString().slice(0, 10)
    });
    this.loadMatches();
    this.loadCredits();
  },

  onShow() {
    this.loadCredits();
  },

  loadMatches() {
    api.getMatches().then(data => {
      this.setData({ matches: data.matches || [] });
    });
  },

  loadCredits() {
    api.getCredits().then(data => {
      this.setData({ credits: data.credits || 0 });
      app.globalData.credits = data.credits || 0;
    });
  },

  goMatch(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: '/pages/match/match?id=' + id });
  }
});
