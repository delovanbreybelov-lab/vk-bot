import time
import requests
import random
import os
# --- НАСТРОЙКИ VK ---
VK_TOKEN = os.getenv ("VK_TOKEN")
USER_ID = [521249117, 308573644]

# --- НАСТРОЙКИ КОШЕЛЬКА ---
WALLET = "0x394845e570718bbe1654e84487b55c99b29adf3b"
API_URL = "https://api.hyperliquid.xyz/info"

def send_vk(text):
    url = "https://api.vk.com/method/messages.send"
    success = True
    for uid in USER_ID:
        params = {
            "user_id": uid,
            "message": text,
            "random_id": random.randint(1, 1_000_000),
            "access_token": VK_TOKEN,
            "v": "5.131"
        }
        try:
            r = requests.post(url, params=params, timeout=10)
            res = r.json()
            if "error" in res:
                print(f"❌ Ошибка VK API для ID {uid}: {res['error']['error_msg']}")
                success = False
        except Exception as e:
            print(f"❌ Ошибка сети при отправке пользователю {uid}: {e}")
            success = False
    return success

def get_hyper_data():
    try:
        # Увеличил timeout до 15, чтобы не было ошибки Read timed out
        pos_data = requests.post(API_URL, json={"type": "clearinghouseState", "user": WALLET}, timeout=15).json()
        ord_data = requests.post(API_URL, json={"type": "openOrders", "user": WALLET}, timeout=15).json()
        return pos_data, (ord_data if isinstance(ord_data, list) else [])
    except Exception as e:
        print(f"❌ Ошибка API Hyperliquid (проблема с инетом): {e}")
        return None, None

def monitor():
    print("⚡️ МОНИТОРИНГ ВК ЗАПУЩЕН (Интервал: 1 сек)")
    
    if send_vk("🚀 Бот запущен!"):
        print("✅ Тестовое сообщение отправлено в ВК")
    else:
        print("❌ ОШИБКА: Сообщение не ушло.")

    history = {} 
    known_orders = set()

    while True:
        data, orders = get_hyper_data()
        
        if data:
            positions = data.get("assetPositions", [])
            current_coins = []
            
            for p in positions:
                pos = p.get("position", {})
                coin = pos.get("coin")
                szi = float(pos.get("szi", 0))
                if szi == 0: continue
                
                amount = abs(szi)
                side = "LONG" if szi > 0 else "SHORT"
                entry_price = float(pos.get("entryPx", 0))
                mark_price = float(pos.get("returnPx", 0))
                liq_price = float(pos.get("liquidationPx", 0)) if pos.get("liquidationPx") else 0
                
                current_coins.append(coin)
                liq_dist = abs(((mark_price - liq_price) / mark_price) * 100) if mark_price > 0 and liq_price > 0 else 100

                if coin not in history:
                    msg = f"🆕 ОТКРЫТА ПОЗИЦИЯ: {coin}\nНаправление: {side}\nВход: {entry_price}\nОбъем: {amount}"
                    send_vk(msg)
                    history[coin] = {'side': side, 'amount': amount}
                else:
                    if history[coin]['side'] != side:
                        msg = f"🔄 СМЕНА НАПРАВЛЕНИЯ: {coin}\nБыло: {history[coin]['side']} -> Стало: {side}"
                        send_vk(msg)
                        history[coin]['side'] = side

                    if amount < (history[coin]['amount'] * 0.98):
                        drop = ((history[coin]['amount'] - amount) / history[coin]['amount']) * 100
                        msg = f"📉 ФИКСАЦИЯ ОБЪЕМА: {coin}\nУпал на: -{drop:.1f}%"
                        send_vk(msg)
                        history[coin]['amount'] = amount

                    if liq_dist < 3:
                        msg = f"🆘 КРИТИЧЕСКИЙ РИСК: {coin}\nДо ликв: {liq_dist:.1f}%\nЦена ликв: {liq_price}"
                        send_vk(msg)

            for old_coin in list(history.keys()):
                if old_coin not in current_coins:
                    send_vk(f"🏁 ПОЗИЦИЯ ПОЛНОСТЬЮ ЗАКРЫТА: {old_coin}")
                    del history[old_coin]

        if orders:
            for o in orders:
                oid = o.get("oid")
                if oid not in known_orders:
                    msg = f"📝 НОВЫЙ ОРДЕР: {o.get('coin')}\nРазмер: {o.get('sz')}\nЦена: {o.get('limitPx')}"
                    send_vk(msg)
                    known_orders.add(oid)

        # Сделал паузу чуть больше, чтобы соединение не обрывалось
        time.sleep(1.0)

if __name__ == "__main__":
   while True:
        try:
            monitor()
        except Exception as e:
            print("CRASH:", e)
            time.sleep(5)
