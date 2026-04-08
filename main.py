import io
import json
import os
import requests
import time
from ppadb.client import Client as AdbClient
from PIL import Image
import Vision
import Quartz
import warnings

# Скрываем лишние предупреждения
warnings.filterwarnings("ignore")

# Настройки LM Studio
URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL_NAME = "qwen2.5-7b-instruct"

def apple_vision_ocr(pil_image):
    """Распознавание текста через нативный Apple Vision Framework"""
    # 1. Подготовка изображения
    img_byte_arr = io.BytesIO()
    pil_image.save(img_byte_arr, format='PNG')
    img_data = img_byte_arr.getvalue()

    # 2. Создание запроса к Vision
    data = Quartz.NSData.dataWithBytes_length_(img_data, len(img_data))
    handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(data, None)

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(True)
    
    # Добавляем поддержку русского и английского
    request.setRecognitionLanguages_(["ru-RU", "en-US"])

    # 3. Выполнение
    success, error = handler.performRequests_error_([request], None)
    if not success:
        print(f"[-] Ошибка Vision: {error}")
        return ""

    # 4. Сбор текста
    results = request.results()
    text_out = []
    for observation in results:
        top_candidate = observation.topCandidates_(1)[0]
        text_out.append(top_candidate.string())

    return "\n".join(text_out)

def get_text_from_screen():
    # 1. Коннект
    client = AdbClient(host="127.0.0.1", port=5037)
    devices = client.devices()
    if not devices:
        print("[-] Телефон не найден")
        return None, None
    device = devices[0]

    # 2. Скриншот
    print("[*] Снимаю экран (ADB)...")
    raw_img = device.screencap()
    img = Image.open(io.BytesIO(raw_img))

    # 3. Родной Apple OCR (быстрый)
    print("[*] Распознаю через Apple Vision...")
    start_time = time.time()
    full_text = apple_vision_ocr(img)
    print(f"[+] Распознано за {time.time() - start_time:.2f} сек.")
    
    return full_text, device

def ask_qwen(raw_text):
    print("[*] Отправляя в Qwen...")
    
    prompt = f"""Ты — эксперт по анализу социальных сетей и OSINT. Перед тобой сырой текст (OCR) из Threads. 
    Очисти его от мусора и структурируй данные.

    ИНСТРУКЦИИ:
    1. Идентифицируй отдельных пользователей и их посты. 
    2. Игнорируй системные элементы (кнопки "Ответить", "Нравится", время, рекламу).
    3. Для каждого поста составь JSON-объект:
   - "user": Никнейм/имя профиля.
   - "post_content": Полный текст сообщения не добавляя "\n".
   - "personal_intelligence": Список фактов (питомцы, растения, локации, работа, хобби, семья). Если фактов нет — "не обнаружено".
   - "vibe": Настроение поста (позитив, нытье, экспертность, агрессия).

    ВЕРНИ ОТВЕТ СТРОГО В ФОРМАТЕ JSON:
    {{"detected_profiles": [ {{ "user": "...", "post_content": "...", "personal_intelligence": "...", "vibe": "..." }} ]}}

    Текст для анализа:
    {raw_text}"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Ты — помощник, который преобразует текст в JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }

    try:
        response = requests.post(URL, json=payload, timeout=60)
        data = response.json()
        if 'choices' not in data:
            return f"Ошибка API: {data}"
            
        ans = data['choices'][0]['message']['content']
        # Очистка от markdown
        return ans.strip().replace('```json', '').replace('```', '').strip()
    except Exception as e:
        return f"Ошибка связи с Qwen: {e}"

if __name__ == "__main__":
     
    iteration = 0
    print("[!] Цикл запущен. Нажми Ctrl+C для остановки.")

    while True:
        iteration += 1
        print(f"\n>>> Итерация №{iteration}")

        # Шаг 1: Получаем текст и объект устройства
        full_text, device = get_text_from_screen()
        
        if full_text:
            print("\n--- ЧТО УВИДЕЛ APPLE VISION ---")
            print(full_text)
            print("--------------------------------\n")

            # Шаг 2: Шлем в нейронку
            json_result = ask_qwen(full_text)
            
            file_path = "settings_test.json"

            # Пытаемся распарсить ответ
            try:
                new_data = json.loads(json_result)

                # Если файл существует — читаем
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        try:
                            data = json.load(f)
                        except json.JSONDecodeError:
                            data = {"detected_profiles": []}
                else:
                    data = {"detected_profiles": []}

                # Добавляем новые записи
                data["detected_profiles"].extend(new_data.get("detected_profiles", []))

                # Перезаписываем файл
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                
                print("[+] Результат сохранен в settings_test.json")
            
            except Exception as e:
                print(f"[-] Ошибка обработки JSON: {e}")

            print("\n--- ОТВЕТ НЕЙРОНКИ ---")
            print(json_result)
            
        else:
            print("[-] Не удалось получить текст.")

        # Общий блок для свайпа
        if device:
            print(f"[*] Свайп (1080x2160)... Следующая страница через 2 сек.")
            time.sleep(2)
            device.shell("input swipe 540 1900 540 200 500")
            print("[+] Команда свайпа отправлена.")
        else:
            print("[-] Устройство не найдено. Выход из цикла.")
            break