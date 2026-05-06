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

    for ext in (".mp3", ".wav"):
        path = os.path.join(content_dir, f"{name}{ext}")
        if os.path.isfile(path):
            return path
    raise FileNotFoundError(f"Файл {name}.mp3 или {name}.wav не найден")

# Одна кнопка, одна дорожка.
BUTTON_PIN = 2
SOUND_FILE = find_sound("1")

LOCK_TIMEOUT = 1.5
ON_CONFIRM_TIME = 1.0


# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ =====================

audio_lock = threading.Lock()
last_play_time = 0.0
current_player = None
pending_play = False  # "звук должен стартовать", даже если процесс ещё не поднялся

# ==================== ФУНКЦИИ =====================

def get_player(sound_file):
    if sound_file.endswith(".mp3"):
        return ["mpg123", sound_file]

    if sound_file.endswith(".wav"):
        return ["aplay", sound_file]

    return ["ffplay", "-nodisp", "-autoexit", sound_file]

def _stop_player_locked(timeout_s=0.5):
    """Остановить текущий плеер.

    Важно: запускаем плеер в отдельной process group (`setsid`), чтобы можно было
    убить *всю* группу (ffplay/mpg123 могут порождать дочерние процессы).
    """
    global current_player

    if current_player is None:
        return
    try:
        os.killpg(current_player.pid, signal.SIGTERM)
        current_player.wait(timeout=timeout_s)
    except Exception:
        pass
    finally:
        current_player = None

def is_playing():
    with audio_lock:
        # pending_play нужен, чтобы отпускание кнопки могло отменить старт
        # (иначе при дребезге OFF в момент запуска звук может всё равно начаться).
        return current_player is not None or pending_play

def stop_sound():
    global current_player, last_play_time, pending_play

    with audio_lock:
        pending_play = False
        _stop_player_locked()
        # Разрешаем быстрое повторное включение после отжатия кнопки
        last_play_time = 0.0

def play_sound(sound_file):
    global last_play_time, current_player, pending_play

    now = time.monotonic()

    with audio_lock:
        # Если кнопку уже отпустили (или был дребезг OFF) — отменяем старт.
        if not pending_play:
            return

        # Защита от слишком частых перезапусков только пока звук реально играет.
        # Нужна, чтобы дребезг/флаттер не спамил запуском процессов.
        if current_player is not None and (now - last_play_time < LOCK_TIMEOUT):
            print(f"   Игнор — слишком быстро ({now - last_play_time:.2f} сек)")
            return

        last_play_time = now

        print(f"   → Запускаю: {sound_file}")

        # Останавливаем предыдущий звук, если он ещё играет.
        _stop_player_locked()

        try:
            current_player = subprocess.Popen(
                get_player(sound_file),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid
            )
        except Exception as e:
            current_player = None
            pending_play = False
            print(f"   Ошибка запуска плеера: {e}", file=sys.stderr)
            return

        player = current_player
        pending_play = False
    
    # Ждём окончания вне lock, чтобы основной цикл мог читать кнопку и стопать звук.
    player.wait()

    with audio_lock:
        if current_player == player:
            current_player = None
# ==================== ОСНОВНОЙ КОД =====================

def main():
    print("Запуск плеера кнопок (WiringPi)")
    print(f"Пин кнопки: {BUTTON_PIN}")
    print(f"Звук: {SOUND_FILE}")

    print("Нажмите Ctrl+C для выхода")

    # инициализация wiringPi
    wiringpi.wiringPiSetup()

    # настройка пинов
    wiringpi.pinMode(BUTTON_PIN, wiringpi.INPUT)
    wiringpi.pullUpDnControl(BUTTON_PIN, wiringpi.PUD_UP)

    press_start_time = None
    on_fired = False

    try:
        while True:

            val = wiringpi.digitalRead(BUTTON_PIN)
            now = time.monotonic()

            # Включение: подтверждаем "ON" только если val==0 держится непрерывно
            # больше ON_CONFIRM_TIME (чтобы отфильтровать дребезг).
            if not is_playing():
                if val == 0:
                    if press_start_time is None:
                        press_start_time = now
                    if (not on_fired) and (now - press_start_time >= ON_CONFIRM_TIME):
                        on_fired = True
                        with audio_lock:
                            # Помечаем как "в процессе старта", чтобы OFF мог отменить запуск.
                            global pending_play
                            pending_play = True
                        threading.Thread(
                            target=play_sound,
                            args=(SOUND_FILE,),
                            daemon=True
                        ).start()
                else:
                    press_start_time = None
                    on_fired = False

            # Выключение: как только увидели "OFF" (val==1) — сразу останавливаем.
            else:
                if val == 1:
                    stop_sound()
                    press_start_time = None
                    on_fired = False

            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\nВыход")
        stop_sound()


if __name__ == "__main__":
    main()
