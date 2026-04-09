import json
from collections import Counter

def find_user_duplicates(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        profiles = data.get("detected_profiles", [])
        
        # Собираем все имена пользователей в один список
        usernames = [p.get("user") for p in profiles if p.get("user")]
        
        # Считаем вхождения каждого имени
        counts = Counter(usernames)
        
        # Фильтруем тех, кто встречается больше 1 раза
        duplicates = {name: count for name, count in counts.items() if count > 1}
        
        # Сортируем по убыванию частоты
        sorted_duplicates = sorted(duplicates.items(), key=lambda item: item[1], reverse=True)

        if not sorted_duplicates:
            print("✅ Дубликатов по именам пользователей не найдено.")
            return

        print(f"{'Username':<25} | {'Повторов'}")
        print("-" * 40)
        for user, count in sorted_duplicates:
            print(f"@{user:<24} | {count}")
            
        print(f"\nВсего уникальных пользователей: {len(counts)}")
        print(f"Всего записей в базе: {len(usernames)}")

    except FileNotFoundError:
        print("❌ Файл не найден.")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    find_user_duplicates("threads_base.json")