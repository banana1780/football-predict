"""
Football Predict App - World Cup Match Score Prediction with Paywall
Flask backend serving the football prediction engine
"""
import sys
import os
import uuid
from datetime import datetime

from flask import (Flask, request, jsonify, render_template,
                   session as flask_session, redirect, url_for)

# Add engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'engine'))
from prediction_engine import FootballPredictionEngine

from config import (SECRET_KEY, ENGINE_DATA_DIR, ADMIN_TOKEN,
                    PRICE_TIERS, CARD_PREFIX, get_price_tiers, calc_price)
from models import (init_db, get_db, create_card, redeem_card,
                    get_session_credits, unlock_match, is_match_unlocked,
                    get_today_matches, get_match, add_match, get_all_cards,
                    create_payment, approve_payment, get_pending_payments,
                    get_all_payments)

# ── App Setup ──

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Initialize engine (singleton)
engine = FootballPredictionEngine(data_dir=ENGINE_DATA_DIR)


@app.before_request
def ensure_session():
    """Ensure every visitor has a session ID"""
    if 'sid' not in flask_session:
        flask_session['sid'] = str(uuid.uuid4())


def get_sid():
    return flask_session.get('sid', 'anonymous')


# ── Frontend Routes ──

@app.route('/')
def index():
    """Home page - today's matches"""
    today = datetime.now().strftime('%Y-%m-%d')
    matches = get_today_matches(today)
    credits = get_session_credits(get_sid())
    return render_template('index.html', matches=matches,
                           credits=credits, today=today)


@app.route('/match/<int:match_id>')
def match_page(match_id):
    """Match detail page"""
    match = get_match(match_id)
    if not match:
        return "Match not found", 404
    sid = get_sid()
    unlocked = is_match_unlocked(sid, match_id)
    credits = get_session_credits(sid)
    return render_template('match.html', match=match,
                           unlocked=unlocked, credits=credits)


@app.route('/pay')
def pay_page():
    """Payment / card redemption page"""
    credits = get_session_credits(get_sid())
    tiers = get_price_tiers()
    return render_template('pay.html', credits=credits, tiers=tiers, base_price=9.9)


@app.route('/admin')
def admin_page():
    """Admin dashboard"""
    return render_template('admin.html', tiers=get_price_tiers())


# ── API Routes ──

# -- Match data --

@app.route('/api/matches')
def api_matches():
    """Get today's matches with free preview data"""
    today = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    matches = get_today_matches(today)
    sid = get_sid()

    result = []
    for m in matches:
        try:
            pred = engine.predict(m['team_a'], m['team_b'])
        except Exception:
            pred = None

        unlocked = is_match_unlocked(sid, m['id'])

        item = {
            'id': m['id'],
            'team_a': m['team_a'],
            'team_b': m['team_b'],
            'match_time': m['match_time'] or '',
            'group_name': m['group_name'] or '',
            'handicap': m['handicap'],
            'status': m['status'],
            'locked': not unlocked,
        }

        if pred:
            item['elo_a'] = pred['elo_a']
            item['elo_b'] = pred['elo_b']
            item['xg_a'] = pred['xg_a']
            item['xg_b'] = pred['xg_b']

        if unlocked and pred:
            item['prediction'] = {
                'final': pred['final'],
                'top_scores': pred['top_scores'],
                'poisson': pred['poisson'],
                'combined': pred['combined'],
            }

        result.append(item)

    return jsonify({
        'matches': result,
        'credits': get_session_credits(sid),
        'date': today,
    })


@app.route('/api/matches/<int:match_id>/preview')
def api_match_preview(match_id):
    """Free preview: Elo + xG only, no probabilities"""
    match = get_match(match_id)
    if not match:
        return jsonify({'error': 'Match not found'}), 404

    try:
        pred = engine.predict(match['team_a'], match['team_b'])
    except Exception as e:
        return jsonify({'error': f'Prediction failed: {str(e)}'}), 500

    return jsonify({
        'team_a': pred['team_a'],
        'team_b': pred['team_b'],
        'elo_a': pred['elo_a'],
        'elo_b': pred['elo_b'],
        'xg_a': pred['xg_a'],
        'xg_b': pred['xg_b'],
        'match_time': match['match_time'] or '',
        'group_name': match['group_name'] or '',
        'handicap': match['handicap'],
        'locked': not is_match_unlocked(get_sid(), match_id),
    })


@app.route('/api/matches/<int:match_id>/full')
def api_match_full(match_id):
    """Full prediction - FREE for all users"""
    match = get_match(match_id)
    if not match:
        return jsonify({'error': 'Match not found'}), 404

    modules_str = request.args.get('modules', 'all')
    modules = set(modules_str.split(',')) if modules_str != 'all' else {'all'}

    try:
        pred = engine.predict(match['team_a'], match['team_b'])
        upset = engine.upset_analysis(match['team_a'], match['team_b'], {
            'is_first_match': True, 'expansion_format': True
        })
    except Exception as e:
        return jsonify({'error': f'Engine error: {str(e)}'}), 500

    result = {'team_a': pred['team_a'], 'team_b': pred['team_b'],
              'match_time': match['match_time'] or '', 'group_name': match['group_name'] or '',
              'free_mode': True}

    if 'all' in modules or 'basic' in modules:
        result['final'] = pred['final']; result['top_scores'] = pred['top_scores']
        result['poisson'] = pred['poisson']; result['combined'] = pred['combined']
        result['elo_expected'] = round(pred['elo_expected_a'] * 100, 1)
        sa = engine.team_stats.get(match['team_a'], {'avg_goals':1.35,'avg_conceded':1.35})
        sb = engine.team_stats.get(match['team_b'], {'avg_goals':1.35,'avg_conceded':1.35})
        result['team_stats'] = {
            'a': {'goals': sa['avg_goals'], 'conceded': sa['avg_conceded'],
                  'attack_index': round(sa['avg_goals']/1.35,2), 'defense_index': round(sa['avg_conceded']/1.35,2)},
            'b': {'goals': sb['avg_goals'], 'conceded': sb['avg_conceded'],
                  'attack_index': round(sb['avg_goals']/1.35,2), 'defense_index': round(sb['avg_conceded']/1.35,2)}}
        tg = {}
        for t in range(9):
            p = sum(engine.poisson_prob(pred['xg_a'],a)*engine.poisson_prob(pred['xg_b'],t-a)
                    for a in range(min(t+1,8)) if 0 <= t-a < 8)
            tg[str(t if t<8 else '8+')] = round(p*100,1)
        result['total_goals_dist'] = tg

    if 'all' in modules or 'upset' in modules:
        result['upset'] = {'favorite':upset['favorite'],'underdog':upset['underdog'],
            'elo_gap':upset['elo_gap'],'adjusted_upset_prob':upset['adjusted_upset_prob'],
            'upset_combined':upset['upset_combined'],'tier':upset['tier'],'base_draw_prob':upset['base_draw_prob']}

    if 'all' in modules or 'handicap' in modules:
        xa, xb = pred['xg_a'], pred['xg_b']; H = match.get('handicap',-1) or -1
        w = sum(engine.poisson_prob(xa,a)*engine.poisson_prob(xb,b) for a in range(8) for b in range(8) if a+H > b)
        d = sum(engine.poisson_prob(xa,a)*engine.poisson_prob(xb,b) for a in range(8) for b in range(8) if a+H == b)
        l = sum(engine.poisson_prob(xa,a)*engine.poisson_prob(xb,b) for a in range(8) for b in range(8) if a+H < b)
        result['handicap'] = {'line':H,'cover':round(w*100,1),'push':round(d*100,1),'lose':round(l*100,1)}

    return jsonify(result)


# -- Card operations --

@app.route('/api/cards/redeem', methods=['POST'])
def api_redeem():
    """Redeem a card code"""
    data = request.get_json()
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'success': False, 'error': '请输入卡密'})

    sid = get_sid()
    result = redeem_card(code, sid)

    if result['success']:
        # Transfer credits to this session
        flask_session['credits'] = flask_session.get('credits', 0) + result['credits']
        # Store session mapping for credits
        flask_session['card_code'] = code

    return jsonify(result)


@app.route('/api/session/credits')
def api_credits():
    """Get current session credits"""
    sid = get_sid()
    credits = get_session_credits(sid)
    return jsonify({'credits': credits})


@app.route('/api/matches/<int:match_id>/unlock', methods=['POST'])
def api_unlock(match_id):
    """Unlock a match using 1 credit"""
    match = get_match(match_id)
    if not match:
        return jsonify({'success': False, 'error': '比赛不存在'}), 404

    sid = get_sid()
    result = unlock_match(sid, match_id)

    return jsonify(result)


@app.route('/api/matches/<int:match_id>/locked')
def api_check_locked(match_id):
    """Check if a match is unlocked"""
    sid = get_sid()
    return jsonify({
        'locked': not is_match_unlocked(sid, match_id)
    })


# -- QR Scan Payment routes --

@app.route('/api/pay/submit', methods=['POST'])
def api_pay_submit():
    """User paid via QR, submits nickname to claim credits"""
    data = request.get_json()
    nickname = data.get('nickname', '').strip()
    credits = int(data.get('credits', 1))  # How many matches they paid for

    if not nickname:
        return jsonify({'success': False, 'error': '请输入你的微信/支付宝昵称'})

    price = calc_price(credits)

    sid = get_sid()
    pid = create_payment(sid, nickname, credits)

    return jsonify({
        'success': True,
        'message': f'提交成功！已选{credits}场，需付¥{price}，等待管理员确认到账',
        'payment_id': pid,
        'credits': credits,
        'price': price,
    })


@app.route('/api/pay/status')
def api_pay_status():
    """Check if this session has a pending payment"""
    sid = get_sid()
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute(
        'SELECT * FROM payments WHERE session_id = ? ORDER BY created_at DESC LIMIT 1',
        (sid,)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({'status': 'none'})

    return jsonify({
        'status': row['status'],
        'nickname': row['nickname'],
        'credits': get_session_credits(sid),
    })


@app.route('/api/results')
def api_results():
    """Get past match results with prediction accuracy comparison"""
    date_filter = request.args.get('date', '')

    conn = get_db()
    cursor = conn.cursor()
    if date_filter:
        rows = cursor.execute(
            "SELECT * FROM matches WHERE status='finished' AND score IS NOT NULL AND match_date = ? ORDER BY match_time",
            (date_filter,)
        ).fetchall()
    else:
        rows = cursor.execute(
            "SELECT * FROM matches WHERE status='finished' AND score IS NOT NULL ORDER BY match_date DESC, match_time"
        ).fetchall()
    conn.close()

    results = []
    for m in rows:
        match = dict(m)
        try:
            pred = engine.predict(match['team_a'], match['team_b'])
        except:
            continue
        actual = match['score']
        parts = actual.split('-')
        actual_a = int(parts[0])
        actual_b = int(parts[1])
        if actual_a > actual_b:
            actual_result = 'win_a'
        elif actual_a == actual_b:
            actual_result = 'draw'
        else:
            actual_result = 'win_b'
        pred_result = max(pred['final'], key=pred['final'].get)
        matched = (pred_result == actual_result)
        results.append({
            'id': match['id'],
            'team_a': match['team_a'],
            'team_b': match['team_b'],
            'group_name': match['group_name'] or '',
            'score': match['score'],
            'actual_result': actual_result,
            'predicted_result': pred_result,
            'matched': matched,
            'predicted_probs': {k: round(v,1) for k,v in pred['final'].items()},
        })
    return jsonify({'results': results})


# -- Admin routes --

@app.route('/api/admin/generate', methods=['POST'])
def api_admin_generate():
    """Admin: generate card codes"""
    token = request.headers.get('X-Admin-Token', '')
    if token != ADMIN_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    tier_key = data.get('tier', 'single')
    tier = PRICE_TIERS.get(tier_key, PRICE_TIERS['single'])
    count = data.get('count', 1)

    codes = []
    for _ in range(count):
        code = create_card(tier['credits'])
        codes.append({
            'code': code,
            'credits': tier['credits'],
            'label': tier['label'],
        })

    return jsonify({'success': True, 'cards': codes})


@app.route('/api/admin/payments/pending')
def api_admin_pending():
    """Admin: get pending payments to approve"""
    token = request.headers.get('X-Admin-Token', '')
    if token != ADMIN_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    payments = get_pending_payments()
    return jsonify({'payments': payments})


@app.route('/api/admin/payments/<int:pid>/approve', methods=['POST'])
def api_admin_approve(pid):
    """Admin: approve a payment"""
    token = request.headers.get('X-Admin-Token', '')
    if token != ADMIN_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    result = approve_payment(pid)
    return jsonify(result)


@app.route('/api/admin/payments/all')
def api_admin_all_payments():
    """Admin: get all payments"""
    token = request.headers.get('X-Admin-Token', '')
    if token != ADMIN_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    payments = get_all_payments()
    return jsonify({'payments': payments})
def api_admin_generate():
    """Admin: generate card codes"""
    token = request.headers.get('X-Admin-Token', '')
    if token != ADMIN_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    tier_key = data.get('tier', 'single')
    tier = PRICE_TIERS.get(tier_key, PRICE_TIERS['single'])
    count = data.get('count', 1)

    codes = []
    for _ in range(count):
        code = create_card(tier['credits'])
        codes.append({
            'code': code,
            'credits': tier['credits'],
            'label': tier['label'],
        })

    return jsonify({'success': True, 'cards': codes})


@app.route('/api/admin/cards')
def api_admin_cards():
    """Admin: list all cards"""
    token = request.headers.get('X-Admin-Token', '')
    if token != ADMIN_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    cards = get_all_cards()
    return jsonify({'cards': cards})


@app.route('/api/admin/matches/add', methods=['POST'])
def api_admin_add_match():
    """Admin: add a match"""
    token = request.headers.get('X-Admin-Token', '')
    if token != ADMIN_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    match_id = add_match(
        team_a=data['team_a'],
        team_b=data['team_b'],
        match_date=data['match_date'],
        match_time=data.get('match_time', ''),
        group_name=data.get('group_name', ''),
        handicap=data.get('handicap', 0),
        status=data.get('status', 'upcoming'),
        score=data.get('score'),
    )
    return jsonify({'success': True, 'id': match_id})


# ── Boot ──

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    print(f"Engine loaded: {len(engine.elo_ratings)} teams")
    app.run(host='0.0.0.0', port=port, debug=False)
