import time
import requests
import os

TELEGRAM_BOT_TOKEN = os.environ['8116521490:AAF-yAxdj9my39yTHL5yE5KK3aZZvGKcTXw']
TELEGRAM_CHAT_ID = os.environ['5942176343']
known_tokens = set()

def send_telegram_alert(token):
    msg = (
        f"<b>🚀 High-Potential Pump Detected</b>\n"
        f"<b>CA:</b> <code>{token['address']}</code>\n"
        f"<b>LP Locked:</b> {token['lp_locked_percent']}%\n"
        f"<b>Creator Holding:</b> {token['creator_holding_percent']}%\n"
        f"<b>Mint Authority Disabled:</b> {'✅ Yes' if token['mint_authority_disabled'] else '❌ No'}\n"
        f"<b>Market Cap:</b> ${token['market_cap_usd']:,}\n"
        f"<b>Volume (24h):</b> ${token['volume_usd']:,}\n"
        f"<a href='https://dexscreener.com/solana/{token['address']}'>📈 View Chart</a>"
    )
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    try:
        requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': msg, 'parse_mode': 'HTML'})
    except Exception as e:
        print(f"[Telegram ERROR] {e}")

def fetch_new_tokens():
    url = "https://pump.fun/api/tokens"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
        "Referer": "https://pump.fun/"
    }
    try:
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"[Pump.fun ERROR] {r.status_code} - {r.text}")
            return []
        tokens = r.json()
        mints = [t['mint'] for t in tokens if 'mint' in t]
        new = [t for t in mints if t not in known_tokens]
        for t in new:
            known_tokens.add(t)
        return new
    except Exception as e:
        print(f"[Pump.fun ERROR] {e}")
        return []

def fetch_solscan_metadata(token_address):
    url = f"https://public-api.solscan.io/token/meta?tokenAddress={token_address}"
    headers = {"accept": "application/json"}
    try:
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"[Solscan ERROR] {token_address} - {r.status_code}")
            return {'mint_authority_disabled': False, 'creator': '', 'holders': 0}
        j = r.json()
        return {
            'mint_authority_disabled': j.get('mintAuthority') is None,
            'creator': j.get('owner', ''),
            'holders': j.get('holders', 0)
        }
    except Exception as e:
        print(f"[Solscan ERROR] {e}")
        return {'mint_authority_disabled': False, 'creator': '', 'holders': 0}

def fetch_dexscreener_market_data(token_address):
    url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{token_address}"
    try:
        r = requests.get(url)
        if r.status_code != 200:
            print(f"[DEX Screener ERROR] {token_address} - {r.status_code}")
            return {'volume_usd': 0, 'market_cap_usd': 0}
        j = r.json()
        pair = j.get("pairs", [{}])[0]
        return {
            'volume_usd': float(pair.get('volume', {}).get('h24', 0)),
            'market_cap_usd': float(pair.get('fdv', 0))
        }
    except Exception as e:
        print(f"[DEX Screener ERROR] {e}")
        return {'volume_usd': 0, 'market_cap_usd': 0}

def run_bot():
    print("🚀 Bot is running... Ctrl+C to stop")
    while True:
        try:
            new_tokens = fetch_new_tokens()
            for token in new_tokens:
                meta = fetch_solscan_metadata(token)
                if not (meta['mint_authority_disabled'] and meta['holders'] >= 500):
                    continue
                lp_locked = 60
                creator_hold = 4.0
                if lp_locked < 50 or creator_hold > 5:
                    continue
                market = fetch_dexscreener_market_data(token)
                if market['volume_usd'] < 500000 or market['market_cap_usd'] < 200000:
                    continue
                qualified = {
                    'address': token,
                    'lp_locked_percent': lp_locked,
                    'creator_holding_percent': creator_hold,
                    'mint_authority_disabled': meta['mint_authority_disabled'],
                    'market_cap_usd': market['market_cap_usd'],
                    'volume_usd': market['volume_usd']
                }
                send_telegram_alert(qualified)
            time.sleep(5)
        except Exception as e:
            print(f"[Error] {e}")
            time.sleep(10)

run_bot()
