/* ── Match Page ── */

async function initMatchPage(matchId, isUnlocked) {
    // Load free preview
    try {
        const resp = await fetch(`/api/matches/${matchId}/preview`);
        const data = await resp.json();
        renderPreview(data);
    } catch (e) {
        document.getElementById('preview-content').innerHTML =
            '<div class="error">加载失败</div>';
    }

    // FREE MODE: always show full prediction
    if (isUnlocked || true) {
        document.getElementById('lock-overlay').style.display = 'none';
        document.getElementById('lock-tag').textContent = '免费开放';
        document.getElementById('lock-tag').className = 'free-tag';
        document.getElementById('module-selector').style.display = 'block';
        loadFullPrediction(matchId);
    }

    updateCreditsDisplay();
}

function renderPreview(data) {
    const html = `
        <div class="data-row">
            <span class="data-label">Elo 评级</span>
            <span class="data-value">${data.team_a} ${data.elo_a} vs ${data.elo_b} ${data.team_b}</span>
        </div>
        <div class="data-row">
            <span class="data-label">预期进球 (xG)</span>
            <span class="data-value">${data.xg_a} vs ${data.xg_b}</span>
        </div>
        <div class="data-row">
            <span class="data-label">让球盘</span>
            <span class="data-value">${data.handicap || 0}</span>
        </div>
        <div class="data-row">
            <span class="data-label">赛事</span>
            <span class="data-value">${data.group_name} | ${data.match_time}</span>
        </div>
    `;
    document.getElementById('preview-content').innerHTML = html;
}

async function loadFullPrediction(matchId) {
    const modules = getSelectedModules();
    try {
        const resp = await fetch(`/api/matches/${matchId}/full?modules=${modules}`);
        if (resp.status === 403) {
            document.getElementById('paid-content').innerHTML =
                '<div class="lock-overlay"><p>请先解锁</p></div>';
            return;
        }
        const data = await resp.json();
        renderFullPrediction(data);
    } catch (e) {
        document.getElementById('paid-content').innerHTML =
            '<div class="error">加载预测失败</div>';
    }
}

function getSelectedModules() {
    const checks = document.querySelectorAll('input[name="module"]:checked');
    if (checks.length === 0) return 'basic';
    const values = Array.from(checks).map(c => c.value);
    if (values.length >= 3) return 'all';
    return values.join(',');
}

function renderFullPrediction(data) {
    let html = '';

    // 1. Win/Draw/Loss - 3 layer breakdown
    if (data.final && data.poisson && data.combined) {
        html += `
            <h3>📈 胜平负概率预测</h3>
            <table class="prob-table">
                <tr><th>模型层级</th><th>${data.team_a} 胜</th><th>平局</th><th>${data.team_b} 胜</th></tr>
                <tr><td class="data-label">泊松分布 (xG)</td>
                    <td>${data.poisson.win_a}%</td><td>${data.poisson.draw}%</td><td>${data.poisson.win_b}%</td></tr>
                <tr><td class="data-label">Elo + 泊松混合</td>
                    <td>${data.combined.win_a}%</td><td>${data.combined.draw}%</td><td>${data.combined.win_b}%</td></tr>
                <tr style="font-weight:800;color:var(--accent);">
                    <td class="data-label">最终预测</td>
                    <td>${data.final.win_a}%</td><td>${data.final.draw}%</td><td>${data.final.win_b}%</td></tr>
            </table>
        `;
    }

    // 2. Elo expected
    if (data.elo_expected) {
        html += `
            <div class="data-row">
                <span class="data-label">Elo 预期胜率</span>
                <span class="data-value">${data.team_a} ${data.elo_expected}% — ${data.team_b} ${(100-data.elo_expected).toFixed(1)}%</span>
            </div>
        `;
    }

    // 3. Top Scores
    if (data.top_scores && data.top_scores.length) {
        html += '<h3>🎯 最可能比分 TOP5</h3><div class="score-list">';
        data.top_scores.forEach(([s, p], i) => {
            const cls = i === 0 ? 'score-item-top' : '';
            html += `<span class="score-item ${cls}">${s} <small>${p}%</small></span>`;
        });
        html += '</div>';
    }

    // 4. Total goals distribution
    if (data.total_goals_dist) {
        html += '<h3>⚽ 总进球数分布</h3><div class="goal-bars">';
        const entries = Object.entries(data.total_goals_dist);
        entries.forEach(([goals, prob]) => {
            const barW = Math.max(prob * 2, 2);
            html += `<div class="goal-bar-row">
                <span class="goal-label">${goals}球</span>
                <span class="goal-bar"><span style="width:${barW}px"></span></span>
                <span class="goal-pct">${prob}%</span></div>`;
        });
        html += '</div>';
    }

    // 5. Team stats comparison
    if (data.team_stats) {
        const sa = data.team_stats.a, sb = data.team_stats.b;
        html += `
            <h3>📊 球队攻防数据对比</h3>
            <table class="prob-table">
                <tr><th>指标</th><th>${data.team_a}</th><th>${data.team_b}</th><th>联赛均值</th></tr>
                <tr><td class="data-label">场均进球</td><td>${sa.goals}</td><td>${sb.goals}</td><td>1.35</td></tr>
                <tr><td class="data-label">场均失球</td><td>${sa.conceded}</td><td>${sb.conceded}</td><td>1.35</td></tr>
                <tr><td class="data-label">进攻指数</td><td>${sa.attack_index}</td><td>${sb.attack_index}</td><td>1.00</td></tr>
                <tr><td class="data-label">防守指数</td><td>${sa.defense_index}</td><td>${sb.defense_index}</td><td>1.00</td></tr>
            </table>
        `;
    }

    // 6. Upset analysis
    if (data.upset) {
        const u = data.upset;
        const tierColor = u.tier.includes('Tier 1') ? 'var(--red)' :
                          u.tier.includes('Tier 2') ? 'var(--orange)' :
                          u.tier.includes('Tier 3') ? 'var(--yellow)' : 'var(--green)';
        html += `
            <h3>🔥 爆冷分析</h3>
            <div class="data-row">
                <span class="data-label">强弱判定</span>
                <span class="data-value">${u.favorite} (强) vs ${u.underdog} (弱)  |  Elo差距: ${u.elo_gap}分</span>
            </div>
            <div class="data-row">
                <span class="data-label">弱队胜率</span>
                <span class="data-value prob-high">${u.adjusted_upset_prob}%</span>
            </div>
            <div class="data-row">
                <span class="data-label">平局概率</span>
                <span class="data-value">${u.base_draw_prob || '—'}%</span>
            </div>
            <div class="data-row">
                <span class="data-label">综合爆冷值</span>
                <span class="data-value" style="color:${tierColor};font-weight:800;">${u.upset_combined}%</span>
            </div>
            <div class="data-row">
                <span class="data-label">爆冷等级</span>
                <span class="data-value" style="color:${tierColor};">${u.tier}</span>
            </div>
        `;
    }

    // 7. Handicap analysis
    if (data.handicap) {
        const h = data.handicap;
        const label = h.line < 0
            ? `${data.team_a} 让${Math.abs(h.line)}球`
            : `${data.team_b} 让${h.line}球`;
        html += `
            <h3>🎰 让球盘分析 (${label})</h3>
            <table class="prob-table">
                <tr><th>${h.line < 0 ? data.team_a+'赢盘' : data.team_b+'赢盘'}</th>
                    <th>走水</th>
                    <th>${h.line < 0 ? data.team_b+'赢盘' : data.team_a+'赢盘'}</th></tr>
                <tr>
                    <td class="prob-high">${h.cover}%</td>
                    <td class="prob-mid">${h.push}%</td>
                    <td style="color:var(--red);">${h.lose}%</td>
                </tr>
            </table>
            <p style="font-size:0.8rem;color:var(--text-dim);margin-top:8px;">
                赢盘条件: ${h.line < 0 ? data.team_a+'净胜'+Math.abs(h.line)+'球以上' : data.team_b+'净胜'+h.line+'球以上'}
            </p>
        `;
    }

    // 8. Methodology note
    html += `
        <div class="method-note">
            <h4>🧬 模型说明</h4>
            <p>本预测基于 <strong>Elo评级 (30%) + 泊松分布xG (70%)</strong> 双模型加权融合，结合世界杯48队扩军赛制修正因子。</p>
            <p>Elo数据来源：国际足联历史战绩；xG参数：各队近10场场均进球/失球。</p>
            <p>⚠️ 统计模型存在不确定性，不构成投注建议。</p>
        </div>
    `;

    document.getElementById('paid-content').innerHTML = html;
}

async function unlockMatch() {
    const btn = document.getElementById('unlock-btn');
    btn.disabled = true;
    btn.textContent = '验证中...';

    try {
        const resp = await fetch(`/api/matches/${MATCH_ID}/unlock`, { method: 'POST' });
        const data = await resp.json();

        if (data.success) {
            document.getElementById('lock-overlay').style.display = 'none';
            document.getElementById('lock-tag').textContent = '✅ 已解锁';
            document.getElementById('lock-tag').className = 'free-tag';
            document.getElementById('module-selector').style.display = 'block';
            loadFullPrediction(MATCH_ID);
            updateCreditsDisplay();
        } else {
            alert(data.error || '解锁失败');
            btn.disabled = false;
            btn.textContent = '解锁本场 (消耗1次)';
        }
    } catch (e) {
        alert('网络错误，请重试');
        btn.disabled = false;
        btn.textContent = '解锁本场 (消耗1次)';
    }
}

async function updateCreditsDisplay() {
    try {
        const resp = await fetch('/api/session/credits');
        const data = await resp.json();
        const els = document.querySelectorAll('#credits-display, #credits-num, #credits-amount');
        els.forEach(el => { if (el) el.textContent = data.credits; });
        const topBadge = document.getElementById('credits-badge-top');
        if (topBadge) topBadge.textContent = `💳 ${data.credits}次`;
    } catch (e) {}
}

// Listen for module checkbox changes
document.addEventListener('DOMContentLoaded', () => {
    const checks = document.querySelectorAll('input[name="module"]');
    checks.forEach(c => {
        c.addEventListener('change', () => {
            if (typeof MATCH_ID !== 'undefined' && IS_UNLOCKED) {
                loadFullPrediction(MATCH_ID);
            }
        });
    });
});

/* ── Review Section ── */

function renderResultLabel(result) {
    if (result === 'win_a') return '主胜';
    if (result === 'draw') return '平局';
    return '客胜';
}

async function loadReview(date) {
    const container = document.getElementById('review-list');
    if (!container) return;

    const queryDate = date || (typeof currentDate !== 'undefined' ? currentDate : new Date().toISOString().slice(0,10));
    try {
        const resp = await fetch('/api/results?date=' + queryDate);
        const data = await resp.json();

        if (!data.results || data.results.length === 0) {
            container.innerHTML = '<p style="color:var(--text-dim);text-align:center;">暂无比赛结果</p>';
            return;
        }

        let html = '';
        data.results.forEach(r => {
            const dot = r.matched
                ? '<span style="color:#4ade80;font-size:18px;">●</span>'
                : '<span style="color:#f87171;font-size:18px;">●</span>';
            const status = r.matched
                ? '<span style="color:#4ade80;">命中</span>'
                : '<span style="color:#f87171;">未中</span>';

            html += '<div class="data-row" style="padding:10px 0;">';
            html += '<span>' + dot + ' ' + r.team_a + ' <strong>' + r.score + '</strong> ' + r.team_b + '</span>';
            html += '<span style="font-size:0.8rem;">预测' + renderResultLabel(r.predicted_result) + ' → 实际' + renderResultLabel(r.actual_result) + ' ' + status + '</span>';
            html += '</div>';
        });

        // Summary
        const total = data.results.length;
        const hits = data.results.filter(r => r.matched).length;
        html += '<div style="text-align:center;padding:12px;margin-top:8px;background:var(--bg);border-radius:8px;">';
        html += '<span style="font-size:1.2rem;">准确率：<strong style="color:var(--accent);">' + hits + '/' + total + '</strong> (' + Math.round(hits/total*100) + '%)</span>';
        html += '</div>';

        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<p style="color:var(--text-dim);text-align:center;">加载失败</p>';
    }
}

/* ── Pay Page ── */

async function submitPayment() {
    const input = document.getElementById('nickname-input');
    const msg = document.getElementById('pay-msg');
    const nickname = input.value.trim();

    if (!nickname) {
        msg.className = 'error';
        msg.textContent = '请输入你的微信昵称';
        return;
    }
    if (typeof selectedCredits === 'undefined' || selectedCredits <= 0) {
        msg.className = 'error';
        msg.textContent = '请先选择场次';
        return;
    }

    msg.textContent = '提交中...';
    msg.className = '';

    try {
        const resp = await fetch('/api/pay/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nickname: nickname, credits: selectedCredits })
        });
        const data = await resp.json();

        if (data.success) {
            msg.className = 'success';
            msg.textContent = data.message;
            input.value = '';
            document.getElementById('pay-status').style.display = 'block';
            document.getElementById('pay-status').innerHTML = '⏳ 等待管理员确认到账...';
            let checkCount = 0;
            const interval = setInterval(async () => {
                const sr = await fetch('/api/pay/status');
                const sd = await sr.json();
                if (sd.status === 'approved') {
                    clearInterval(interval);
                    document.getElementById('pay-status').innerHTML =
                        '<span style="color:var(--green)">✅ 已确认！获得 ' + sd.credits + ' 次解锁 <a href="/">回首页看预测</a></span>';
                    updateCreditsDisplay();
                }
                checkCount++;
                if (checkCount > 36) {
                    clearInterval(interval);
                    document.getElementById('pay-status').innerHTML =
                        '<span style="color:var(--text-dim)">如已付款请耐心等待，管理员看到后会确认</span>';
                }
            }, 5000);
            // Disable submit button
            document.getElementById('submit-btn').disabled = true;
            document.getElementById('submit-btn').textContent = '已提交';
        } else {
            msg.className = 'error';
            msg.textContent = data.error || '提交失败';
        }
    } catch (e) {
        msg.className = 'error';
        msg.textContent = '网络错误，请重试';
    }
}

async function checkStatus() {
    const resp = await fetch('/api/pay/status');
    const data = await resp.json();
    if (data.status === 'approved') {
        document.getElementById('pay-status').innerHTML =
            '<span style="color:var(--green)">✅ 已确认！<a href="/">回首页看预测</a></span>';
    } else if (data.status === 'pending') {
        document.getElementById('pay-status').innerHTML =
            '⏳ 还在等待确认...请确保已付款';
    } else {
        document.getElementById('pay-status').innerHTML =
            '还没有提交记录';
    }
}

async function redeemCard() {
    const input = document.getElementById('card-input');
    const msg = document.getElementById('redeem-msg');
    const code = input.value.trim();

    if (!code) {
        msg.className = 'error';
        msg.textContent = '请输入卡密';
        return;
    }

    msg.textContent = '验证中...';
    msg.className = '';

    try {
        const resp = await fetch('/api/cards/redeem', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });
        const data = await resp.json();

        if (data.success) {
            msg.className = 'success';
            msg.textContent = `激活成功！获得 ${data.credits} 次解锁机会`;
            input.value = '';
            setTimeout(() => { window.location.href = '/'; }, 1500);
        } else {
            msg.className = 'error';
            msg.textContent = data.error || '激活失败';
        }
    } catch (e) {
        msg.className = 'error';
        msg.textContent = '网络错误，请重试';
    }
}

/* ── Admin Page ── */

let adminToken = '';

function adminLogin() {
    adminToken = document.getElementById('admin-token').value.trim();
    if (!adminToken) return alert('请输入管理密钥');

    fetch('/api/admin/cards', { headers: { 'X-Admin-Token': adminToken } })
        .then(r => {
            if (r.ok) {
                document.getElementById('admin-login').style.display = 'none';
                document.getElementById('admin-dashboard').style.display = 'block';
                loadPending();
            } else {
                alert('密钥错误');
                adminToken = '';
            }
        })
        .catch(() => alert('连接失败'));
}

async function loadPending() {
    try {
        const resp = await fetch('/api/admin/payments/pending', {
            headers: { 'X-Admin-Token': adminToken }
        });
        const data = await resp.json();

        if (!data.payments || data.payments.length === 0) {
            document.getElementById('pending-list').innerHTML =
                '<p style="color:var(--green);padding:12px;">✅ 没有待确认的付款</p>';
            return;
        }

        let html = '<table class="cards-table"><tr><th>昵称</th><th>时间</th><th>操作</th></tr>';
        data.payments.forEach(p => {
            html += `<tr>
                <td><strong>${p.nickname}</strong></td>
                <td>${p.created_at ? p.created_at.slice(11,16) : ''}</td>
                <td><button class="btn-primary" style="padding:4px 12px;font-size:0.8rem;"
                    onclick="approvePayment(${p.id})">确认到账 ✓</button></td>
            </tr>`;
        });
        html += '</table>';
        document.getElementById('pending-list').innerHTML = html;
    } catch (e) {
        document.getElementById('pending-list').innerHTML = '加载失败';
    }
}

async function approvePayment(pid) {
    if (!confirm('确认这笔付款已到账？')) return;

    try {
        const resp = await fetch(`/api/admin/payments/${pid}/approve`, {
            method: 'POST',
            headers: { 'X-Admin-Token': adminToken }
        });
        const data = await resp.json();
        if (data.success) {
            alert(`已确认！用户「${data.nickname}」获得 ${data.credits} 次解锁`);
            loadPending();
        }
    } catch (e) {
        alert('操作失败');
    }
}

async function generateCards() {
    const tier = document.getElementById('card-tier').value;
    const count = parseInt(document.getElementById('card-count').value) || 1;

    try {
        const resp = await fetch('/api/admin/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Admin-Token': adminToken,
            },
            body: JSON.stringify({ tier, count })
        });
        const data = await resp.json();

        if (data.success) {
            let html = '<h3>生成的卡密：</h3>';
            data.cards.forEach(c => {
                html += `<div class="code-display">${c.code} — ${c.label} (${c.credits}场)</div>`;
            });
            html += '<p style="margin-top:8px;color:var(--orange)">⚠️ 请立即复制保存，刷新后不可找回</p>';
            document.getElementById('gen-result').innerHTML = html;
        }
    } catch (e) {
        document.getElementById('gen-result').innerHTML = '生成失败';
    }
}

async function addMatch() {
    const data = {
        team_a: document.getElementById('m-team-a').value.trim(),
        team_b: document.getElementById('m-team-b').value.trim(),
        match_date: document.getElementById('m-date').value,
        match_time: document.getElementById('m-time').value.trim(),
        group_name: document.getElementById('m-group').value.trim(),
        handicap: parseInt(document.getElementById('m-handicap').value) || -1,
    };

    if (!data.team_a || !data.team_b || !data.match_date) {
        document.getElementById('add-result').innerHTML =
            '<span style="color:var(--red)">请填写主队、客队和日期</span>';
        return;
    }

    try {
        const resp = await fetch('/api/admin/matches/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Admin-Token': adminToken,
            },
            body: JSON.stringify(data)
        });
        const result = await resp.json();
        if (result.success) {
            document.getElementById('add-result').innerHTML =
                `<span style="color:var(--green)">添加成功！ID: ${result.id}</span>`;
        }
    } catch (e) {
        document.getElementById('add-result').innerHTML =
            '<span style="color:var(--red)">添加失败</span>';
    }
}
