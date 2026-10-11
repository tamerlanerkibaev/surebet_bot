import asyncio
import logging
import aiohttp
from datetime import datetime, timezone
from config import ODDS_API_KEY
from calculator import calculate_surebet
from database import get_user_settings

REGION = "eu"

# Широкий диапазон профита для отслеживания всех расхождений
MIN_PROFIT_PERCENT = 0.0
MAX_PROFIT_PERCENT = 20.0

# Пустой список разрешает ВСЕ БК, доступные в API
ALLOWED_BOOKMAKERS = []

CLONE_GROUPS = [
    {"1xBet", "1xStavka", "Melbet", "BetWinner"},
    {"Unibet", "888sport", "LeoVegas"}
]

sent_surebets_cache = set()

def is_clone_pair(bk1: str, bk2: str) -> bool:
    for group in CLONE_GROUPS:
        if bk1 in group and bk2 in group:
            return True
    return False

def is_allowed_bookmaker(bk_name: str) -> bool:
    if not ALLOWED_BOOKMAKERS:
        return True
    return any(allowed.lower() in bk_name.lower() for allowed in ALLOWED_BOOKMAKERS)

async def fetch_real_odds(bot, target_chat_id: int):
    url = "https://api.the-odds-api.com/v4/sports/upcoming/odds/"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": REGION,
        "markets": "totals",
        "dateFormat": "iso"
    }
    
    try:
        logging.info("🌐 Отправка запроса к The Odds API...")
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as resp:
                logging.info(f"📡 Статус ответа API: {resp.status}")
                
                if resp.status == 200:
                    data = await resp.json()
                    logging.info(f"✅ Получено событий от API: {len(data)}")
                    return data
                elif resp.status in (401, 429):
                    err_msg = f"⚠️ **Ошибка API ({resp.status}):** Превышен лимит или неверный API_KEY!"
                    logging.error(err_msg)
                    await bot.send_message(target_chat_id, err_msg)
                    return []
                else:
                    logging.warning(f"⚠️ Нетипичный ответ API: {resp.status}")
                    return []
    except Exception as e:
        logging.error(f"❌ Ошибка подключения к API: {e}")
        return []

async def start_scanning(bot, target_chat_id: int):
    logging.info(f"🔎 Сканер запущен для chat_id: {target_chat_id}")
    loop_count = 0
    
    while True:
        try:
            loop_count += 1
            if loop_count % 50 == 0:
                sent_surebets_cache.clear()
                
            data = await fetch_real_odds(bot, target_chat_id)
            
            if data:
                bank, step = await get_user_settings(target_chat_id, 100000.0, 500)
                surebets_found = 0
                
                for event in data:
                    match_name = f"{event.get('home_team')} — {event.get('away_team')}"
                    bookmakers = event.get("bookmakers", [])
                    
                    if len(bookmakers) < 2:
                        continue

                    # Словарь с группировкой строго по конкретному значению тотала (например "2.5")
                    totals_map = {}

                    for bk in bookmakers:
                        bk_name = bk.get("title", "")
                        if not is_allowed_bookmaker(bk_name):
                            continue

                        markets = bk.get("markets", [])
                        if not markets:
                            continue

                        outcomes = markets[0].get("outcomes", [])
                        for outcome in outcomes:
                            name = outcome.get("name")
                            price = float(outcome.get("price", 0))
                            point = outcome.get("point")

                            if point is None:
                                continue

                            point_str = str(point)
                            if point_str not in totals_map:
                                totals_map[point_str] = {"Over": (0, ""), "Under": (0, "")}

                            if name == "Over" and price > totals_map[point_str]["Over"][0]:
                                totals_map[point_str]["Over"] = (price, bk_name)
                            elif name == "Under" and price > totals_map[point_str]["Under"][0]:
                                totals_map[point_str]["Under"] = (price, bk_name)

                    # Сравнение происходит СТРОГО внутри одного тотала (например, ТБ 2.5 vs ТМ 2.5)
                    for point_val, outcomes in totals_map.items():
                        best_over = outcomes["Over"]
                        best_under = outcomes["Under"]

                        if best_over[0] > 0 and best_under[0] > 0:
                            bk1_name = best_over[1]
                            bk2_name = best_under[1]

                            if bk1_name == bk2_name or is_clone_pair(bk1_name, bk2_name):
                                continue

                            res = calculate_surebet(
                                best_over[0], 
                                best_under[0], 
                                bank, 
                                round_step=step, 
                                min_profit_percent=MIN_PROFIT_PERCENT
                            )

                            if res.has_surebet and (MIN_PROFIT_PERCENT <= res.profit_percent <= MAX_PROFIT_PERCENT):
                                event_key = f"{match_name}_{point_val}_{bk1_name}_{bk2_name}"
                                
                                if event_key not in sent_surebets_cache:
                                    sent_surebets_cache.add(event_key)
                                    surebets_found += 1
                                    
                                    alert_text = (
                                        f"🚨 **ВИЛКА НАЙДЕНА ({res.profit_percent}%)**\n\n"
                                        f"🏆 **Матч:** {match_name}\n"
                                        f"📌 **1. {bk1_name} (ТБ {point_val}):** K = `{res.k1}` ➔ Ставка: *{res.s1:,} ₸*\n"
                                        f"📌 **2. {bk2_name} (ТМ {point_val}):** K = `{res.k2}` ➔ Ставка: *{res.s2:,} ₸*\n\n"
                                        f"💰 **Затраты:** *{res.total_spent:,} ₸*\n"
                                        f"💵 **Чистая прибыль:** *{res.profit:,} ₸*"
                                    ).replace(",", " ")

                                    try:
                                        await bot.send_message(target_chat_id, alert_text, parse_mode="Markdown")
                                    except Exception as send_err:
                                        logging.error(f"Ошибка отправки сообщения: {send_err}")

                logging.info(f"📊 Проверка завершена. Отправлено новых вилок: {surebets_found}")

        except Exception as global_e:
            logging.error(f"❌ Ошибка в цикле сканера: {global_e}")

        await asyncio.sleep(60)
