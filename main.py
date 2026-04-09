import subprocess
import xml.etree.ElementTree as ET
import os
import json
import time

def scrape_iteration(file_path):
    # 1. Дамп через ADB по сети
    subprocess.run(["adb", "shell", "uiautomator", "dump", "/sdcard/view.xml"], capture_output=True)
    subprocess.run(["adb", "pull", "/sdcard/view.xml", "view.xml"], capture_output=True)
    
    if not os.path.exists("view.xml"): return

    tree = ET.parse("view.xml")
    root = tree.getroot()

    texts, authors = [], []

    for node in root.iter('node'):
        t, c, rid = node.get('text', '').strip(), node.get('content-desc', '').strip(), node.get('resource-id', '')
        
        if " фото профиля" in c:
            name = c.replace(" фото профиля", "").strip()
            if name not in ["Профиль", "Действия"]: authors.append(name)
        elif t and not rid and len(t) > 5:
            if t not in ["Ответить", "Репост", "Поделиться", "Лента", "Для вас", "Подписки"]:
                texts.append(t)

    # Загружаем базу
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            db = json.load(f)
    else:
        db = {"detected_profiles": []}

    # Склеиваем по индексам
    count = 0
    for i in range(min(len(texts), len(authors))):
        new_entry = {
            "user": authors[i],
            "post_content": texts[i]
        }
        
        # Проверка на дубликаты в базе
        is_duplicate = any(d['post_content'] == new_entry['post_content'] for d in db['detected_profiles'])
        
        if not is_duplicate:
            db['detected_profiles'].append(new_entry)
            count += 1
            print(f"✅ Добавлен: @{authors[i]}")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
    
    return count

if __name__ == "__main__":
    PATH = "threads_base.json"
    iteration = 0
    total_scraped = 0

    print(f"\n{'='*40}")
    print("🚀 СТАРТ ПАРСИНГА THREADS")
    print(f"{'='*40}")

    try:
        while True:
            iteration += 1
            print(f"\n🔄 ИТЕРАЦИЯ №{iteration}")
            
            added = scrape_iteration(PATH)
            total_scraped += added
            
            print(f"✅ Добавлено: {added} | Всего в базе: {total_scraped}")
            
            # Свайп
            print("[*] Свайп экрана...")
            subprocess.run(["adb", "shell", "input", "swipe", "540", "1900", "540", "200", "500"])
            
            # 1 секунда может быть маловато для прогрузки XML, 
            # если данных много, лучше держать 1.5-2 сек.
            time.sleep(1.5) 

    except KeyboardInterrupt:
        print(f"\n\n{'='*40}")
        print("🛑 СБОР ОСТАНОВЛЕН ПОЛЬЗОВАТЕЛЕМ")
        print(f"Итого итераций: {iteration}")
        print(f"Итого новых постов: {total_scraped}")
        print(f"{'='*40}")
