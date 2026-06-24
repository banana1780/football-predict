const api = require('../../utils/api');
const app = getApp();

Page({
  data: {
    credits: 0,
    apiBase: '',
    tiers: [],
    selectedTier: '',
    selectedCredits: 0,
    selectedPrice: 0,
    nickname: '',
    msg: '',
    msgType: ''
  },

  onLoad() {
    this.setData({ apiBase: app.globalData.apiBase });
    this.loadCredits();
    this.buildTiers();
  },

  loadCredits() {
    api.getCredits().then(data => {
      this.setData({ credits: data.credits || 0 });
    });
  },

  buildTiers() {
    const base = 9.9;
    const tiers = [];
    for (let n = 1; n <= 10; n++) {
      let price = n * base;
      let tag = '';
      if (n >= 2) {
        price = Math.round(price * 0.8 * 10) / 10;
        tag = '8折';
      }
      tiers.push({
        id: 'm' + n,
        credits: n,
        price: price,
        label: n + '场',
        tag: tag
      });
    }
    this.setData({ tiers });
  },

  selectTier(e) {
    const { id, credits, price } = e.currentTarget.dataset;
    this.setData({
      selectedTier: id,
      selectedCredits: credits,
      selectedPrice: price,
      msg: ''
    });
  },

  onNickname(e) {
    this.setData({ nickname: e.detail.value });
  },

  submitPay() {
    if (!this.data.nickname) {
      wx.showToast({ title: '请输入昵称', icon: 'none' });
      return;
    }

    wx.showLoading({ title: '提交中...' });
    api.submitPayment(this.data.nickname, this.data.selectedCredits).then(data => {
      wx.hideLoading();
      if (data.success) {
        this.setData({
          msg: data.message,
          msgType: 'success',
          nickname: ''
        });
        this.pollStatus();
      } else {
        this.setData({ msg: data.error, msgType: 'error' });
      }
    }).catch(() => {
      wx.hideLoading();
      this.setData({ msg: '网络错误', msgType: 'error' });
    });
  },

  pollStatus() {
    let count = 0;
    const timer = setInterval(() => {
      api.checkPaymentStatus().then(data => {
        if (data.status === 'approved') {
          clearInterval(timer);
          this.setData({
            msg: '已确认！获得 ' + data.credits + ' 次解锁',
            msgType: 'success'
          });
          this.loadCredits();
        }
      });
      count++;
      if (count > 36) clearInterval(timer);
    }, 5000);
  }
});
