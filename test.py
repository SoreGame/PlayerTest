#!/usr/bin/env python3
import subprocess
import os
import sys
import argparse

# ------------------- НАСТРОЙКИ -------------------
# Если файл не передан аргументом, ищем такой же набор, как у вас:
DEFAULT_SOUNDS = {
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
}
CONTENT_DIR = "/content"   # папка, где лежат звуки

def find_sound(name, directory=CONTENT_DIR):
    """Ищет файл name.mp3 или name.wav в указанной папке"""
    for ext in [".mp3", ".wav"]:
        path = os.path.join(directory, name + ext)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"Файл {name}.mp3 или {name}.wav не найден")

def get_player(sound_file):
    """Возвращает команду для воспроизведения"""
    if sound_file.endswith(".mp3"):
        return ["mpg123", sound_file]
    elif sound_file.endswith(".wav"):
        return ["aplay", sound_file]
    else:
        # любой другой формат пробуем через ffplay
        return ["ffplay", "-nodisp", "-autoexit", sound_file]

def play_sound(sound_file):
    """Проигрывает один звуковой файл и ждёт завершения"""
    cmd = get_player(sound_file)
    print(f"Играю: {sound_file}")
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ------------------- ОСНОВНАЯ ЧАСТЬ -------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Простой плеер для Orange Pi Zero 2")
    parser.add_argument("sound", nargs="?", help="Имя звука (без расширения) или полный путь к файлу")
    args = parser.parse_args()

    # Если звук не указан – выводим список доступных и просим ввести с клавиатуры
    if args.sound:
        # Может быть полный путь или просто ключ из DEFAULT_SOUNDS
        if os.path.isfile(args.sound):
            sound_file = args.sound
        else:
            sound_file = find_sound(args.sound)
    else:
        # Интерактивный выбор
        print("Доступные звуки:")
        for key, name in DEFAULT_SOUNDS.items():
            path = find_sound(name)
            print(f"  {key} -> {path}")
        choice = input("Введите номер (1-4) или полный путь к файлу: ").strip()
        if choice in DEFAULT_SOUNDS:
            sound_file = find_sound(DEFAULT_SOUNDS[choice])
        elif os.path.isfile(choice):
            sound_file = choice
        else:
            print("Некорректный выбор. Выход.")
            sys.exit(1)

    play_sound(sound_file)
