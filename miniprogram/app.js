App({
  globalData: {
    // IMPORTANT: Change this to your actual server URL
    apiBase: 'https://exit-eventually-shots-shopzilla.trycloudflare.com',
    credits: 0
  },

  onLaunch() {
    this.loadCredits();
  },

  loadCredits() {
    wx.request({
      url: this.globalData.apiBase + '/api/session/credits',
      success: (res) => {
        this.globalData.credits = res.data.credits || 0;
      }
    });
  }
});
