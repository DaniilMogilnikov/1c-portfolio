import requests
import time
import json

TOKEN = "vk1.a.8QYMd-AdBCXNtpfKNbmBi5EXx2N8Ce_OVmg9aLiInCkYf9ggT0-4r3uEFDrQo9laK8RfiXJs72HdSTDXyHBPOmN-VV2pw5u5E-WG7gibSo5AG2hi2dGmIuRODZE8Tyxff1OZLoTK-_F0IdYWH0W-J1fKhKowQtE-qTFjDr002TVT8X538XX5r_iwU92U4mr4J4BPET3vl3WYkgLs50rLLw"
VERSION = "5.131"
URL_1C = "http://localhost/InfoBase/hs/api/"

waiting_for_order = set()
waiting_for_phone = set()

def send_message(user_id, text, keyboard=None):
    payload = {
        "user_id": user_id,
        "message": text,
        "access_token": TOKEN,
        "v": VERSION,
        "random_id": int(time.time() * 1000)
    }
    if keyboard:
        payload["keyboard"] = json.dumps(keyboard, ensure_ascii=False)
    try:
        res = requests.post("https://api.vk.com/method/messages.send", data=payload).json()
        if "error" in res:
            print(f"Ошибка VK: {res['error']['error_msg']}")
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def get_main_keyboard():
    return {
        "one_time": False,
        "buttons": [
            [
                {
                    "action": {
                        "type": "text",
                        "label": "📦 Узнать статус заказа",
                        "payload": '{"command": "status"}'
                    },
                    "color": "primary"
                }
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "📋 Мои заказы",
                        "payload": '{"command": "orders"}'
                    },
                    "color": "primary"
                }
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "❓ Помощь",
                        "payload": '{"command": "help"}'
                    },
                    "color": "secondary"
                }
            ]
        ]
    }

def init_bots_long_poll():
    print("Получение настроек Long Poll...")
    
    group_res = requests.post("https://api.vk.com/method/groups.getById", data={
        "access_token": TOKEN,
        "v": VERSION
    }).json()
    
    if "error" in group_res:
        raise Exception(f"Ошибка ID группы: {group_res['error']['error_msg']}")
    
    group_id = group_res["response"][0]["id"]
    print(f"ID группы: {group_id}")
    
    response = requests.post("https://api.vk.com/method/groups.getLongPollServer", data={
        "group_id": group_id,
        "access_token": TOKEN,
        "v": VERSION
    }).json()
    
    if "error" in response:
        raise Exception(f"Long Poll не включен: {response['error']['error_msg']}")
    
    res = response["response"]
    return res["server"], res["key"], res["ts"]

def check_updates(server, key, ts):
    try:
        lp_response = requests.get(server, params={
            "act": "a_check",
            "key": key,
            "ts": ts,
            "wait": 25,
            "mode": 2,
            "version": 3
        }, timeout=30).json()
    except Exception as e:
        print(f"Ошибка Long Poll: {e}")
        return ts, []

    if "failed" in lp_response:
        return None, [] 
        
    messages = []
    if "updates" in lp_response:
        for update in lp_response["updates"]:
            if update.get("type") == "message_new":
                msg_data = update["object"]["message"]
                user_id = msg_data["from_id"]
                text = msg_data["text"].strip()
                messages.append((user_id, text))
                    
    return lp_response.get("ts", ts), messages

def get_status_from_1c(order_number):
    try:
        response = requests.get(URL_1C + "status/" + order_number, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return f"📋 Заказ {order_number}: {data.get('статус', 'неизвестно')}"
        elif response.status_code == 404:
            return "❌ Заказ не найден"
        else:
            return f"⚠️ Ошибка: {response.status_code}"
    except Exception as e:
        return f"❌ Не удалось подключиться: {e}"

def get_orders_by_phone(phone):
    try:
        response = requests.get(URL_1C + "orders/" + phone, timeout=5)
        if response.status_code == 200:
            data = response.json()
            orders = data.get("заказы", [])
            if not orders:
                return "📭 У вас нет заказов."
            
            text = "📋 Ваши заказы:\n\n"
            for order in orders[:10]:
                text += f"🔹 Заказ {order['номер']}\n"
                text += f"   📅 {order['дата']}\n"
                text += f"   📌 {order['статус']}\n\n"
            return text
        elif response.status_code == 404:
            return "📭 По этому номеру телефона заказы не найдены."
        else:
            return f"⚠️ Ошибка: {response.status_code}"
    except Exception as e:
        return f"❌ Не удалось получить заказы: {e}"

# --- СТАРТ ---
try:
    server, key, ts = init_bots_long_poll()
    print("Бот запущен!")
except Exception as e:
    print(f"\n[ОШИБКА]\n{e}\n")
    exit(1)

while True:
    try:
        new_ts, messages = check_updates(server, key, ts)
        
        if new_ts is None:
            server, key, ts = init_bots_long_poll()
            continue
            
        ts = new_ts

        for user_id, text in messages:
            print(f"Получено: {user_id}: '{text}'")
            text_lower = text.lower().strip()
            
            if user_id in waiting_for_order:
                waiting_for_order.remove(user_id)
                result = get_status_from_1c(text)
                send_message(user_id, result, get_main_keyboard())
                continue
            
            if user_id in waiting_for_phone:
                waiting_for_phone.remove(user_id)
                result = get_orders_by_phone(text)
                send_message(user_id, result, get_main_keyboard())
                continue
            
            if text_lower in ["привет", "начать"]:
                send_message(user_id, "Здравствуйте! Веломастерская приветствует вас.", get_main_keyboard())
            
            elif text_lower.startswith("/help") or text_lower == "❓ помощь":
                send_message(user_id, "Выберите действие на кнопке:", get_main_keyboard())
            
            elif text_lower.startswith("/status"):
                parts = text.split()
                if len(parts) > 1:
                    order_number = parts[1]
                    result = get_status_from_1c(order_number)
                    send_message(user_id, result, get_main_keyboard())
                else:
                    waiting_for_order.add(user_id)
                    send_message(user_id, "Введите номер заказа:")
            
            elif text_lower == "📦 узнать статус заказа":
                waiting_for_order.add(user_id)
                send_message(user_id, "Введите номер заказа:")
            
            elif text_lower.startswith("/orders"):
                parts = text.split()
                if len(parts) > 1:
                    phone = parts[1]
                    result = get_orders_by_phone(phone)
                    send_message(user_id, result, get_main_keyboard())
                else:
                    waiting_for_phone.add(user_id)
                    send_message(user_id, "Введите номер телефона (например, 89171234567):")
            
            elif text_lower == "📋 мои заказы":
                waiting_for_phone.add(user_id)
                send_message(user_id, "Введите номер телефона (например, 89171234567):")
            
            else:
                send_message(user_id, "Используйте кнопки меню.", get_main_keyboard())
                
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        time.sleep(5)
    
    time.sleep(0.1)