#!/usr/bin/env python3
import time
import subprocess
import threading
import sys
import wiringpi
import os
import signal

# ==================== НАСТРОЙКИ =====================
def find_sound(name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    content_dir = os.path.join(base_dir, "content")

    for ext in [".mp3", ".wav"]:
        path = os.path.join(content_dir, f"{name}{ext}")
        if os.path.isfile(path):
            return path
    raise FileNotFoundError(f"Файл {name}.mp3 или {name}.wav не найден")

BUTTON_LINES = [2]  # wiringPi номер пина (1 кнопка)

SOUNDS = [find_sound("1")]

DEBOUNCE_TIME = 0.25
LOCK_TIMEOUT = 1.5


# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====================

audio_lock = threading.Lock()
last_play_time = 0.0
current_player = None

# ==================== ФУНКЦИИ =====================
def get_player(sound_file):

    if sound_file.endswith(".mp3"):
        return ["mpg123", sound_file]

    if sound_file.endswith(".wav"):
        return ["aplay", sound_file]

    return ["ffplay", "-nodisp", "-autoexit", sound_file]

def stop_sound():
    global current_player

    with audio_lock:
        if current_player is None:
            return
        try:
            os.killpg(current_player.pid, signal.SIGTERM)
            current_player.wait(timeout=0.5)
        except:
            pass
        finally:
            current_player = None

def play_sound(sound_file, index):

    global last_play_time, current_player

    now = time.time()

    with audio_lock:

        if now - last_play_time < LOCK_TIMEOUT:
            print(f"   Игнор — слишком быстро ({now - last_play_time:.2f} сек)")
            return

        last_play_time = now

        print(f"   → Запускаю: {sound_file}")

        # останавливаем старый звук
        if current_player is not None:
            try:
                os.killpg(current_player.pid, signal.SIGTERM)
                current_player.wait(timeout=0.5)
            except:
                pass

        # запускаем звук
        current_player = subprocess.Popen(
            get_player(sound_file),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid
        )

    # ждём окончания звука

        player = current_player
    
    # ждём окончания
    player.wait()

    with audio_lock:
        if current_player == player:
            current_player = None
# ==================== ОСНОВНОЙ КОД =====================

def main():

    print("Запуск плеера кнопок (WiringPi)")
    print(f"Линии кнопок: {BUTTON_LINES}")

    for i, s in enumerate(SOUNDS):
        print(f"  Кнопка {i+1}: {s}")

    print("Нажмите Ctrl+C для выхода")

    # инициализация wiringPi
    wiringpi.wiringPiSetup()

    # настройка пинов
    for pin in BUTTON_LINES:
        wiringpi.pinMode(pin, wiringpi.INPUT)
        wiringpi.pullUpDnControl(pin, wiringpi.PUD_UP)

    prev_values = [1] * len(BUTTON_LINES)
    last_change_times = [0.0] * len(BUTTON_LINES)

    try:
        while True:

            for i, pin in enumerate(BUTTON_LINES):

                val = wiringpi.digitalRead(pin)
                now = time.time()
                # нажатие (1 -> 0)
                if val == 0 and prev_values[i] == 1 and (now - last_change_times[i] > DEBOUNCE_TIME):

                    last_change_times[i] = now
                    sound = SOUNDS[i]

                    threading.Thread(
                        target=play_sound,
                        args=(sound, i),
                        daemon=True
                    ).start()

                # отжатие (0 -> 1) — гасим звук с антидребезгом
                if val == 1 and prev_values[i] == 0 and (now - last_change_times[i] > DEBOUNCE_TIME):
                    last_change_times[i] = now
                    stop_sound()

                prev_values[i] = val

            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nВыход")


if __name__ == "__main__":
    main()
