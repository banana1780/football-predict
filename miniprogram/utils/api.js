const app = getApp();

function request(path, method = 'GET', data = null) {
  return new Promise((resolve, reject) => {
    const url = app.globalData.apiBase + path;
    wx.request({
      url,
      method,
      data,
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data);
        } else {
          reject(res.data);
        }
      },
      fail: reject
    });
  });
}

module.exports = {
  // Get matches
  getMatches(date) {
    const d = date || new Date().toISOString().slice(0, 10);
    return request('/api/matches?date=' + d);
  },

  // Get match preview (free)
  getPreview(matchId) {
    return request('/api/matches/' + matchId + '/preview');
  },

  // Get full prediction (requires unlock)
  getFull(matchId, modules = 'all') {
    return request('/api/matches/' + matchId + '/full?modules=' + modules);
  },

  // Unlock match
  unlockMatch(matchId) {
    return request('/api/matches/' + matchId + '/unlock', 'POST');
  },

  // Submit payment
  submitPayment(nickname, credits) {
    return request('/api/pay/submit', 'POST', { nickname, credits });
  },

  // Check payment status
  checkPaymentStatus() {
    return request('/api/pay/status');
  },

  // Get credits
  getCredits() {
    return request('/api/session/credits');
  }
};
