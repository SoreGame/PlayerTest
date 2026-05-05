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

BUTTON_LINES = [2, 6, 17, 8]  # wiringPi номера пинов
LED_LINES = [16, 13, 10, 9]

SOUNDS = [
    find_sound("1"),
    find_sound("2"),
    find_sound("3"),
    find_sound("4")
]

ON_DELAY_SEC = 0.5
POLL_INTERVAL_SEC = 0.02


# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====================

audio_lock = threading.Lock()
current_player = None
current_led = None
current_index = None

# ==================== ФУНКЦИИ =====================
def get_player(sound_file):

    if sound_file.endswith(".mp3"):
        return ["mpg123", "--loop", "-1", sound_file]

    if sound_file.endswith(".wav"):
        return ["aplay", "--loop=-1", sound_file]

    return ["ffplay", "-nodisp", "-autoexit", "-stream_loop", "-1", sound_file]

def _stop_locked():
    global current_player, current_led, current_index

    if current_player is not None:
        try:
            os.killpg(current_player.pid, signal.SIGTERM)
            current_player.wait(timeout=0.5)
        except Exception:
            pass
        current_player = None

    if current_led is not None:
        try:
            wiringpi.digitalWrite(current_led, 0)
        except Exception:
            pass
        current_led = None

    current_index = None


def start_sound(index):

    global current_player, current_led, current_index

    sound_file = SOUNDS[index]
    led_pin = LED_LINES[index]

    with audio_lock:
        if current_index == index and current_player is not None:
            return

        _stop_locked()

        try:
            wiringpi.digitalWrite(led_pin, 1)
        except Exception:
            pass
        current_led = led_pin
        current_index = index

        current_player = subprocess.Popen(
            get_player(sound_file),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )


def stop_sound():
    with audio_lock:
        _stop_locked()
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
        
    for pin in LED_LINES:
        wiringpi.pinMode(pin, wiringpi.OUTPUT)
        wiringpi.digitalWrite(pin, 0)

    press_start_times = [None] * len(BUTTON_LINES)  # when stable "pressed" started

    try:
        while True:
            now = time.time()

            active_index = None
            for i, pin in enumerate(BUTTON_LINES):
                val = wiringpi.digitalRead(pin)
                pressed = (val == 0)  # PUD_UP => pressed pulls low

                if pressed:
                    if press_start_times[i] is None:
                        press_start_times[i] = now
                    if active_index is None:
                        active_index = i
                else:
                    press_start_times[i] = None

            # no signal => audio off immediately
            if active_index is None:
                stop_sound()
                time.sleep(POLL_INTERVAL_SEC)
                continue

            # signal exists, but turn on only after stable ON_DELAY_SEC
            if press_start_times[active_index] is not None and (now - press_start_times[active_index] >= ON_DELAY_SEC):
                start_sound(active_index)

            # if currently playing some track but its button signal is gone => stop immediately
            with audio_lock:
                idx = current_index
            if idx is not None:
                # still pressed?
                val = wiringpi.digitalRead(BUTTON_LINES[idx])
                if val != 0:
                    stop_sound()

            time.sleep(POLL_INTERVAL_SEC)

    except KeyboardInterrupt:
        print("\nВыход")
        stop_sound()


if __name__ == "__main__":
    main()
