#!/usr/bin/env python3
import os
import sys
import signal
import random
import time
import threading
import subprocess
import contextlib
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
import cursor
from pynput import keyboard
with contextlib.redirect_stdout(None):
    import pygame
import mutagen

@dataclass
class Bindings:
    pause = keyboard.Key.space
    seekBwd = keyboard.Key.left
    seekFwd = keyboard.Key.right
    next = keyboard.Key.tab
    stop = keyboard.Key.esc

@dataclass
class UI:
    is_stop=False
    no_clear = False
    box_width = 46
    playIdx = 6
    file_pos = 0

    box = [("----", False),
           ("", True),
           ("░"*box_width, True),
           ("", True),
           ("--:--", True),
           ("", True),
           ("██████    ██  ██    █  ▄██    ██▄  █    █ ▄███", True),
           ("██████    ██  ██    █ ████    ████ █      ██  ", True),
           ("██████    ██  ██    █  ▀██    ██▀  █    ███▀ █", True),
           ("", True),
           ("CTRL+C     F10        F8        F9       F12  ", True)]

    play = ["██▄▄  ",
            "██████",
            "██▀▀  "]

    pause = ["██  ██",
             "██  ██",
             "██  ██"]


@dataclass
class Files:
    m_file = ""

def resize_handler(signum, frame):
    global UI
    UI.box[2] = (update_bar(), True)
    UI.box[4] = (update_bar_txt(), True)
    redraw()


def swap_symbol(symbols):
    global UI

    for i, symbol in enumerate(symbols):

        line = UI.box[UI.playIdx+i][0][0:10] \
            + symbol \
            + UI.box[UI.playIdx+i][0][16:]

        UI.box[UI.playIdx+i] = (line, True)


def redraw():
    """
    Clears the screen and redraws the ui.
    """

    @lru_cache
    def interface(lines, box_width):
        """
        Creates a box of the terminal size, enclosing the lines
        passed in as a list of tuples.

        Args:
            lines (list): A list of tuples, each containing a line and a bool.
            The line is the text to be displayed, and the boolean is whether
            the line should be centered.

        Returns:
            str: A string of the box with the lines fitted in.
        """
        term_size = os.get_terminal_size()
        term_width = term_size.columns
        term_height = term_size.lines
        string = "\n" * (int(term_height/2) - int(len(lines)/2))
        dots = "..."

        # Limit according to terminal height
        lines = lines[:term_height-1]

        # Create the body
        for tupl in lines:
            line = tupl[0]
            line_len = len(line)

            # Shorten the line if it is too long
            if line_len > min(box_width, term_width):
                line = line[:min(box_width, term_width) - len(dots)] + dots

            if tupl[1]:
                # Center the line
                formatted_line = line.center(min(box_width, term_width))

            else:
                # Left justify the line
                formatted_line = line.ljust(min(box_width, term_width))

            # Center the final line
            formatted_line = formatted_line.center(term_width)
            string += formatted_line

        if UI.no_clear:
            string += "\n" * (int(term_height/2) - int(len(lines)/2) - 2)

        return string

    if not UI.no_clear:
        subprocess.call(['tput', 'reset'])

    cursor.hide()

    print(interface(tuple(UI.box), UI.box_width), flush=True)


def update_bar():
    """
    Updates a song's progress bar calling the bar_parser function with the
    current and total seconds of the song.

    Returns:
        str: Song progress bar string.
    """

    def bar_parser(percentage, max_width):
        """
        Creates a bar of the given percentage.
        Args:
            percentage (float): The percentage of the bar to be filled.
            max_width (int): The maximum width of the bar.
        Returns:
            str: A string of the bar.
        """
        bar_width = int(percentage * max_width)
        bar_txt = "█" * bar_width + "░" * (max_width - bar_width)

        return bar_txt

    # Load the audio file to mutagen
    audio = mutagen.File(Files.m_file)

    # Obtain current and total times
    curr_time = UI.file_pos / 1000
    total_time = max(int(audio.info.length), 1)

    # Calculate the percentage of the song that is played
    percentage = curr_time / total_time

    # Get the progress bar
    progress_bar = bar_parser(percentage, UI.box_width)
    return progress_bar


def update_bar_txt():
    """
    Updates a song_info string calling song_info_parser with the current
    time and total time of the song and returning the updated string.

    Returns:
        str: bar text string.
    """

    def song_info_parser(current_secs, total_secs, max_width):
        """
        Parses the current time and total time of the song.
        Args:
            current_secs (int): The current seconds of the song.
            total_secs (int): The total seconds of the song.
            max_width (int): The maximum width of the line.
        Returns:
            str: A string of the bar text.
        """
        # Convert the seconds to minutes and seconds
        current_mins, current_secs = divmod(current_secs, 60)
        total_mins, total_secs = divmod(total_secs, 60)

        # Format the time
        current_time = "{:02d}:{:02d}".format(current_mins, current_secs)
        total_time = "{:02d}:{:02d}".format(total_mins, total_secs)

        # Format the final info string
        half_width = int(max_width / 2)
        line = current_time.ljust(half_width) + total_time.rjust(half_width)
        return line

    # Load the audio file to mutagen
    audio = mutagen.File(Files.m_file)

    # Obtain current and total times
    curr_time = int(UI.file_pos / 1000)
    total_time = int(audio.info.length)

    # Call song_info_parser to get the bar text
    song_info = song_info_parser(curr_time, total_time, UI.box_width)
    return song_info


def poll_interface(poll_interval):
    """
    Updates the progress bar and the song time info every interval.
    The thread is blocked updating the bar until the song is finished.
    """
    global UI

    if UI.no_clear:
        os.system("clear")

    while True and not UI.is_stop:

        # Update bar and bar text and redraw
        UI.box[2] = (update_bar(), True)
        UI.box[4] = (update_bar_txt(), True)
        redraw()

        # Sleep until the screen has to be updated again
        time.sleep(poll_interval)
        if pygame.mixer.music.get_busy():
            UI.file_pos += poll_interval * 1000


def strip_path_from_filename(path):
    """
    Removes the path from the filename.

    Args:
        path (str): Full path to the file.

    Returns:
        str: The filename without the path.
    """
    if "/" in path:
        filename = path.split("/")[-1]
        return filename
    return path


def strip_filename_from_path(path):
    """
    Removes the filename from the path.

    Args:
        path (str): Full path to the file.

    Returns:
        str: The path without the filename.
    """
    if "/" not in path:
        return os.getcwd()
    words = path.split("/")
    words = words[:-1]
    new_path = "/".join(words)
    return new_path + "/"


def random_file(path):
    old_filename = strip_path_from_filename(path)
    stripped_path = strip_filename_from_path(path)

    # Consider only music files in the directory
    ext = (".mp3", ".wav", ".ogg", ".flac", ".opus")
    files = os.listdir(stripped_path)
    music_files = [f for f in files if f.endswith(ext) and f != old_filename]
    music_files += [old_filename] if len(music_files) == 0 else []

    try:
        r_file = random.choice(music_files)
    except (IndexError, ValueError) as esc:
        raise pygame.error(f"No music files found in the directory.\n{esc}")

    return os.path.join(stripped_path, r_file)
def do_random_play(UI,Files):
    try:
        # Get a random file, load it and play it
        Files.m_file = random_file(Files.m_file)
        pygame.mixer.music.load(Files.m_file)
        pygame.mixer.music.play()

        # Update the song title, info and bar
        UI.file_pos = 0
        UI.box[0] = (strip_path_from_filename(Files.m_file), False)
        UI.box[2] = (update_bar(), True)
        UI.box[4] = (update_bar_txt(), True)
        swap_symbol(UI.pause)
        redraw()

    except pygame.error:
        # Rewind the current song if no random file is found
        pygame.mixer.music.rewind()
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.unpause()

            # Update the bar text and bar
            UI.file_pos = 0
            UI.box[2] = (update_bar(), True)
            UI.box[4] = (update_bar_txt(), True)
            swap_symbol(UI.pause)
            redraw()

def keyboard_listener():
    global UI, Files
    last_time = 0
    press_or_release = defaultdict(lambda: 0)
    with keyboard.Events() as events:
        for event in events:
            # (Clear user input)
            print(" "*16 + "\r", end="")

            # (Check only for key presses)
            press_or_release[event.key] += 1
            if not press_or_release[event.key] % 2:
                continue

            if isinstance(event, keyboard.Events.Press):
                if event.key==keyboard.KeyCode.from_char('d'):
                    current_time=time.time()
                    if last_key=='d' and (current_time - last_time) < 0.5:
                        #删除文件
                        os.remove(Files.m_file)
                        do_random_play(UI,Files)
                    last_key='d'
                    last_time=current_time
                else:
                    # 如果按下的不是 'd'，重置上一次按键的信息
                    last_key = None
                    last_time = 0

            # -- Handle key presses --
            if event.key == Bindings.pause:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.pause()
                    swap_symbol(UI.play)
                    redraw()
                else:
                    pygame.mixer.music.unpause()
                    swap_symbol(UI.pause)
                    redraw()
            elif event.key == Bindings.seekBwd:
                song_length = 1000 * mutagen.File(Files.m_file).info.length
                skip_amount = 0.025 * song_length

                next_pos = UI.file_pos - skip_amount
                start_pos = 0
                UI.file_pos = max(next_pos, start_pos)
                pygame.mixer.music.play(start=UI.file_pos/1000)

                UI.box[2] = (update_bar(), True)
                UI.box[4] = (update_bar_txt(), True)
                swap_symbol(UI.pause)
                redraw()
            elif event.key == Bindings.seekFwd:
                song_length = 1000 * mutagen.File(Files.m_file).info.length
                skip_amount = 0.025 * song_length

                next_pos = UI.file_pos + skip_amount
                end_pos = song_length
                UI.file_pos = min(next_pos, end_pos)
                pygame.mixer.music.play(start=UI.file_pos/1000)

                UI.box[2] = (update_bar(), True)
                UI.box[4] = (update_bar_txt(), True)
                swap_symbol(UI.pause)
                redraw()
            elif event.key == Bindings.next:
                do_random_play(UI,Files)
            elif event.key == Bindings.stop:
                pygame.mixer.music.stop()
                os.system("clear")
                cursor.show()
                UI.is_stop=True
                break



signal.signal(signal.SIGWINCH, resize_handler)
pygame.init()

def play(file_path):
    global UI, Files
    UI.is_stop=False
    UI.file_pos = 0
    update_interval = 1/2         # Default value: 2 fps
    Files.m_file = file_path
    try:
        pygame.mixer.music.load(Files.m_file)
        UI.box[0] = (strip_path_from_filename(Files.m_file), False)
        pygame.mixer.music.play()

        MUSIC_END = pygame.USEREVENT+1
        pygame.mixer.music.set_endevent(MUSIC_END)
    except pygame.error:
        print(f"不能加载文件或目录：'{Files.m_file}'.")
        UI.is_stop=True
    th=threading.Thread(target=keyboard_listener)
    th.daemon=True;th.start()
    poll_interface(update_interval)


