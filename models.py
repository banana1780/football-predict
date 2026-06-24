"""SQLite database models for Football Predict App"""
import sqlite3
import random
import string
from datetime import datetime
from config import DATABASE_PATH, CARD_PREFIX, CARD_SEGMENTS


def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            credits INTEGER NOT NULL,
            used_by_ip TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activated_at TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_a TEXT NOT NULL,
            team_b TEXT NOT NULL,
            match_date TEXT NOT NULL,
            match_time TEXT,
            group_name TEXT,
            handicap INTEGER DEFAULT 0,
            status TEXT DEFAULT 'upcoming',
            score TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unlocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            match_id INTEGER NOT NULL,
            card_id INTEGER,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            nickname TEXT NOT NULL,
            credits INTEGER NOT NULL DEFAULT 1,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


# ── Card operations ──

def generate_card_code():
    """Generate a card code like FP-XXXX-XXXX-XXXX"""
    segments = []
    for _ in range(CARD_SEGMENTS):
        seg = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        segments.append(seg)
    return CARD_PREFIX + '-' + '-'.join(segments)


def create_card(credits: int) -> str:
    """Create a new card and return its code"""
    conn = get_db()
    cursor = conn.cursor()
    code = generate_card_code()
    cursor.execute(
        'INSERT INTO cards (code, credits) VALUES (?, ?)',
        (code, credits)
    )
    conn.commit()
    conn.close()
    return code


def redeem_card(code: str, session_id: str) -> dict:
    """Redeem a card code. Returns dict with success/error."""
    conn = get_db()
    cursor = conn.cursor()

    card = cursor.execute(
        'SELECT * FROM cards WHERE code = ?', (code.upper(),)
    ).fetchone()

    if not card:
        conn.close()
        return {'success': False, 'error': '卡密无效'}

    if card['activated_at']:
        conn.close()
        return {'success': False, 'error': '卡密已被使用'}

    cursor.execute(
        'UPDATE cards SET used_by_ip = ?, activated_at = ? WHERE id = ?',
        (session_id, datetime.now().isoformat(), card['id'])
    )
    conn.commit()
    conn.close()

    return {
        'success': True,
        'credits': card['credits'],
        'code': card['code']
    }


def get_session_credits(session_id: str) -> int:
    """Get remaining credits for a session"""
    conn = get_db()
    cursor = conn.cursor()

    # Total credits from cards redeemed by this session
    cards_credits = cursor.execute(
        'SELECT COALESCE(SUM(c.credits), 0) as total FROM cards c '
        'WHERE c.used_by_ip = ? AND c.activated_at IS NOT NULL',
        (session_id,)
    ).fetchone()['total']

    # Credits used (matches unlocked)
    used = cursor.execute(
        'SELECT COUNT(*) as cnt FROM unlocks WHERE session_id = ?',
        (session_id,)
    ).fetchone()['cnt']

    conn.close()
    return cards_credits - used


def unlock_match(session_id: str, match_id: int, card_id: int = None) -> dict:
    """Unlock a match for a session. Returns dict with success/error."""
    credits = get_session_credits(session_id)
    if credits <= 0:
        return {'success': False, 'error': '余额不足，请先充值'}

    conn = get_db()
    cursor = conn.cursor()

    # Check if already unlocked
    existing = cursor.execute(
        'SELECT id FROM unlocks WHERE session_id = ? AND match_id = ?',
        (session_id, match_id)
    ).fetchone()

    if existing:
        conn.close()
        return {'success': True, 'message': '已解锁，无需重复付费'}

    cursor.execute(
        'INSERT INTO unlocks (session_id, match_id, card_id) VALUES (?, ?, ?)',
        (session_id, match_id, card_id)
    )
    conn.commit()
    conn.close()

    remaining = get_session_credits(session_id)
    return {'success': True, 'remaining_credits': remaining}


def is_match_unlocked(session_id: str, match_id: int) -> bool:
    """Check if a match is unlocked for this session"""
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute(
        'SELECT id FROM unlocks WHERE session_id = ? AND match_id = ?',
        (session_id, match_id)
    ).fetchone()
    conn.close()
    return row is not None


# ── Match operations ──

def get_today_matches(date_str: str = None) -> list:
    """Get matches for a given date (default: today)"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    conn = get_db()
    cursor = conn.cursor()
    matches = cursor.execute(
        'SELECT * FROM matches WHERE match_date = ? ORDER BY match_time',
        (date_str,)
    ).fetchall()
    conn.close()
    return [dict(m) for m in matches]


def get_match(match_id: int) -> dict:
    """Get a single match by ID"""
    conn = get_db()
    cursor = conn.cursor()
    match = cursor.execute(
        'SELECT * FROM matches WHERE id = ?', (match_id,)
    ).fetchone()
    conn.close()
    return dict(match) if match else None


def add_match(team_a: str, team_b: str, match_date: str,
              match_time: str = None, group_name: str = None,
              handicap: int = 0, status: str = 'upcoming',
              score: str = None) -> int:
    """Add a match and return its ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO matches (team_a, team_b, match_date, match_time, '
        'group_name, handicap, status, score) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (team_a, team_b, match_date, match_time, group_name,
         handicap, status, score)
    )
    match_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return match_id


def get_all_cards() -> list:
    """Admin: get all cards"""
    conn = get_db()
    cursor = conn.cursor()
    cards = cursor.execute(
        'SELECT * FROM cards ORDER BY created_at DESC'
    ).fetchall()
    conn.close()
    return [dict(c) for c in cards]


# ── Payment operations (QR scan flow) ──

def create_payment(session_id: str, nickname: str, credits: int = 1) -> int:
    """User scanned QR and paid, submits nickname. Returns payment ID."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO payments (session_id, nickname, credits) VALUES (?, ?, ?)',
        (session_id, nickname.strip(), credits)
    )
    pid = cursor.lastrowid
    conn.commit()
    conn.close()
    return pid


def approve_payment(payment_id: int) -> dict:
    """Admin approves a payment. Credits go to the user's session."""
    conn = get_db()
    cursor = conn.cursor()

    payment = cursor.execute(
        'SELECT * FROM payments WHERE id = ?', (payment_id,)
    ).fetchone()

    if not payment:
        conn.close()
        return {'success': False, 'error': '订单不存在'}

    if payment['status'] == 'approved':
        conn.close()
        return {'success': False, 'error': '已处理过'}

    cursor.execute(
        'UPDATE payments SET status = ?, approved_at = ? WHERE id = ?',
        ('approved', datetime.now().isoformat(), payment_id)
    )
    conn.commit()
    conn.close()

    return {
        'success': True,
        'session_id': payment['session_id'],
        'credits': payment['credits'],
        'nickname': payment['nickname'],
    }


def get_session_credits(session_id: str) -> int:
    """Get remaining credits for a session (cards + approved payments)"""
    conn = get_db()
    cursor = conn.cursor()

    # From cards
    cards_credits = cursor.execute(
        'SELECT COALESCE(SUM(c.credits), 0) as total FROM cards c '
        'WHERE c.used_by_ip = ? AND c.activated_at IS NOT NULL',
        (session_id,)
    ).fetchone()['total']

    # From approved payments
    pay_credits = cursor.execute(
        'SELECT COALESCE(SUM(p.credits), 0) as total FROM payments p '
        'WHERE p.session_id = ? AND p.status = ?',
        (session_id, 'approved')
    ).fetchone()['total']

    # Used
    used = cursor.execute(
        'SELECT COUNT(*) as cnt FROM unlocks WHERE session_id = ?',
        (session_id,)
    ).fetchone()['cnt']

    conn.close()
    return cards_credits + pay_credits - used


def get_pending_payments() -> list:
    """Admin: get all pending payments"""
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute(
        'SELECT * FROM payments WHERE status = ? ORDER BY created_at DESC',
        ('pending',)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_payments() -> list:
    """Admin: get all payments"""
    conn = get_db()
    cursor = conn.cursor()
    rows = cursor.execute(
        'SELECT * FROM payments ORDER BY created_at DESC LIMIT 100'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
