"""
Persistent SSH tunnel with auto-reconnect
Run: python tunnel.py
"""
import subprocess
import time
import os
import sys

URL_FILE = os.path.join(os.path.dirname(__file__), '当前网址.txt')
APP_FILE = os.path.join(os.path.dirname(__file__), 'miniprogram', 'app.js')


def start_flask():
    """Start Flask in background"""
    subprocess.Popen(
        [sys.executable, 'app.py'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=os.path.dirname(__file__)
    )


def run_tunnel():
    """Run SSH tunnel and return the URL"""
    proc = subprocess.Popen(
        ['ssh', '-o', 'StrictHostKeyChecking=no',
         '-o', 'ServerAliveInterval=30',
         '-o', 'ServerAliveCountMax=3',
         '-R', '80:localhost:5000',
         'nokey@localhost.run'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    url = None
    for line in proc.stdout:
        if 'lhr.life' in line and 'https://' in line:
            for part in line.split():
                if part.startswith('https://') and 'lhr.life' in part:
                    url = part.rstrip(',')
                    break
            if url:
                break

    return proc, url


def save_url(url):
    """Save URL and update all dependent files"""
    base_dir = os.path.dirname(__file__)

    # Save to text file
    with open(URL_FILE, 'w') as f:
        f.write(url)

    # Update QR code
    try:
        import qrcode
        qr_path = os.path.join(base_dir, 'static', '网站二维码.png')
        qrcode.make(url).save(qr_path)
        print("  QR code updated")
    except ImportError:
        pass

    # Update mini program URL
    appjs = os.path.join(base_dir, 'miniprogram', 'app.js')
    if os.path.exists(appjs):
        with open(appjs, 'r', encoding='utf-8') as f:
            content = f.read()
        # Find and replace the old URL
        import re
        content = re.sub(r"apiBase:\s*'https://[^']+'", f"apiBase: '{url}'", content)
        with open(appjs, 'r', encoding='utf-8') as f:
            content = f.read()
        new_content = re.sub(r"apiBase:\s*'https://[^']+'", f"apiBase: '{url}'", content)
        with open(appjs, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("  Mini program URL updated")


if __name__ == '__main__':
    print("=" * 50)
    print("  世界杯预测平台 - 自动重连模式")
    print("=" * 50)
    print()

    # Start Flask once
    print("[1/2] Starting Flask...")
    start_flask()
    time.sleep(3)

    # Tunnel with auto-reconnect
    print("[2/2] Starting tunnel (auto-reconnect)...")
    print()

    reconnect_count = 0
    while True:
        print(f"  Connecting... (第{reconnect_count+1}次)")
        proc, url = run_tunnel()

        if url:
            save_url(url)
            print(f"  URL: {url}")
            print(f"  Saved to 当前网址.txt")
            print()

            # Monitor the connection
            try:
                while proc.poll() is None:
                    time.sleep(5)
            except KeyboardInterrupt:
                print("\nShutting down...")
                proc.terminate()
                break

        print("  Tunnel disconnected. Reconnecting in 5 seconds...")
        time.sleep(5)
        reconnect_count += 1
        try:
            proc.terminate()
        except:
            pass
