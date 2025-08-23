import pyautogui
import time
import json
import random
import math
import os
from pynput.keyboard import Key, Listener

# ===========================================================
# FAST MODE SUPPORT  (only added, no existing code changed)
# ===========================================================
fast_mode = True   # <- set to False for normal behavior

# keep originals
ORIGINAL_SLEEP = time.sleep
ORIGINAL_UNIFORM = random.uniform

def fast_sleep(sec):
    # globally replace sleep with 0.1 when fast_mode=True
    if fast_mode:
        ORIGINAL_SLEEP(0.1)
    else:
        ORIGINAL_SLEEP(sec)

def fast_uniform(a,b):
    # durations => always 0.1 when in fast mode
    if fast_mode:
        return 0.1
    return ORIGINAL_UNIFORM(a,b)

# monkey-patch
time.sleep = fast_sleep
random.uniform = fast_uniform
# ===========================================================

pyautogui.useImageNotFoundException(False)

from core.state import check_support_card, check_failure, check_turn, check_mood, check_current_year, check_criteria
from core.logic import do_something
from utils.constants import MOOD_LIST, G1_DATES
from core.recognizer import is_infirmary_active, match_template
from utils.scenario import ura

with open("config.json", "r", encoding="utf-8") as file:
  config = json.load(file)

MAX_FAILURE = config["maximum_failure"]
MINIMUM_MOOD = config["minimum_mood"]
PRIORITIZE_G1_RACE = config["prioritize_g1_race"]

# Globals for pause/exit
paused = False
exit_triggered = False

def on_press(key):
  global paused, exit_triggered
  try:
    if hasattr(key, 'char') and key.char == '=':
      print("[EMERGENCY] '=' key pressed. Exiting immediately.")
      exit_triggered = True
      os._exit(1)
  except AttributeError:
    pass

def on_release(key):
  global paused
  if hasattr(key, 'char') and key.char == '0':
    paused = not paused
    if paused:
      print("[INFO] Paused. Press Left Alt again to resume.")
    else:
      print("[INFO] Resumed.")

def wait_if_paused():
  while paused:
    print("[INFO] Waiting... (Paused)")
    ORIGINAL_SLEEP(3)

def start_emergency_listener():
  listener = Listener(on_press=on_press, on_release=on_release)
  listener.daemon = True
  listener.start()

def jitter_click(x, y, clicks=1, duration=None, jitter_x=45, jitter_y=15):
    if duration is None:
        duration = random.uniform(0.12, 0.2)

    jittered_x = x + random.randint(-jitter_x, jitter_x)
    jittered_y = y + random.randint(-jitter_y, jitter_y)

    pyautogui.moveTo(jittered_x, jittered_y, duration=duration)
    pyautogui.click(clicks=clicks)

def click(img, confidence = 0.8, minSearch = 2, click = 1, text = ""):
  btn = pyautogui.locateCenterOnScreen(img, confidence=confidence, minSearchTime=minSearch)
  if btn:
    if text:
      print(text)
    move_duration = random.uniform(0.12, 0.2)
    pyautogui.moveTo(btn, duration=move_duration)
    jitter_click(btn.x, btn.y, clicks=click)
    return True
  
  return False

def go_to_training():
  return click("assets/buttons/training_btn.png")


def check_training():
  training_types = {
    "spd": "assets/icons/train_spd.png",
    "sta": "assets/icons/train_sta.png",
    "pwr": "assets/icons/train_pwr.png",
    "guts": "assets/icons/train_guts.png",
    "wit": "assets/icons/train_wit.png"
  }
  results = {}

  support_count = 0
  skip_all = False
  wit_only = False
  duration = 0.2

  for key, icon_path in training_types.items():
    pos = pyautogui.locateCenterOnScreen(icon_path, confidence=0.8)
    if pos:
      wait_if_paused()

      if skip_all:
        continue
      elif wit_only and key != "wit":
        continue

      pyautogui.moveTo(pos, duration=0.1)
      pyautogui.mouseDown()

      failure_chance = check_failure()

      if int(failure_chance) > MAX_FAILURE + 3:
        print(f"[INFO] Fail too high... SKIPPING")
        wit_only = True
        duration = 0.5
        continue

      support_counts = check_support_card()
      total_support = sum(support_counts.values())
      results[key] = {
        "support": support_counts,
        "total_support": total_support,
        "failure": failure_chance
      }
      print(f"[{key.upper()}] → {support_counts}, Fail: {failure_chance}%")

      support_count += total_support
      if key != "wit" and support_count >= 6:
        print(f"[INFO] Found all 6 supports... skipping all further training types.")
        time.sleep(0.1)
        skip_all = True
      time.sleep(0.1)
  pyautogui.mouseUp()
  return results


def do_train(train):
  train_btn = pyautogui.locateCenterOnScreen(f"assets/icons/train_{train}.png", confidence=0.8)
  if train_btn:
    for _ in range(3):
      jitter_click(train_btn.x, train_btn.y)
      time.sleep(0.1)

def do_rest():
  rest_btn = pyautogui.locateCenterOnScreen("assets/buttons/rest_btn.png", confidence=0.8)
  rest_summber_btn = pyautogui.locateCenterOnScreen("assets/buttons/rest_summer_btn.png", confidence=0.8)

  if rest_btn:
    pyautogui.moveTo(rest_btn, duration=0.35)
    jitter_click(rest_btn.x, rest_btn.y)
  elif rest_summber_btn:
    pyautogui.moveTo(rest_summber_btn, duration=0.35)
    jitter_click(rest_summber_btn.x, rest_summber_btn.y)

def do_recreation():
  recreation_btn = pyautogui.locateCenterOnScreen("assets/buttons/recreation_btn.png", confidence=0.8)
  recreation_summer_btn = pyautogui.locateCenterOnScreen("assets/buttons/rest_summer_btn.png", confidence=0.8)

  if recreation_btn:
    pyautogui.moveTo(recreation_btn, duration=0.3)
    jitter_click(recreation_btn.x, recreation_btn.y)
  elif recreation_summer_btn:
    pyautogui.moveTo(recreation_summer_btn, duration=0.5)
    jitter_click(recreation_summer_btn.x, recreation_summer_btn.y)

def do_race(prioritize_g1 = False):
  wait_if_paused()
  click(img="assets/buttons/races_btn.png", minSearch=10)
  wait_if_paused()
  click(img="assets/buttons/ok_btn.png", minSearch=0.7)
  wait_if_paused()
  found = race_select(prioritize_g1=prioritize_g1)
  wait_if_paused()
  if not found:
    print("[INFO] No race found.")
    return False

  race_prep()
  time.sleep(1)
  after_race()
  return True

def race_day():
  wait_if_paused()
  click(img="assets/buttons/race_day_btn.png", minSearch=10)
  wait_if_paused()
  click(img="assets/buttons/ok_btn.png", minSearch=0.7)
  time.sleep(0.5)
  wait_if_paused()
  for i in range(2):
    click(img="assets/buttons/race_btn.png", minSearch=2)
    time.sleep(0.5)
  wait_if_paused()
  race_prep()
  time.sleep(1)
  after_race()

def race_select(prioritize_g1 = False):
  pyautogui.moveTo(x=560, y=680)

  time.sleep(0.2)

  if prioritize_g1:
    print("[INFO] Looking for G1 race.")
    for i in range(2):
      race_card = match_template("assets/ui/g1_race.png", threshold=0.9)

      if race_card:
        for x, y, w, h in race_card:
          region = (x, y, 310, 90)
          match_aptitude = pyautogui.locateCenterOnScreen("assets/ui/match_track.png", confidence=0.8, minSearchTime=0.7, region=region)
          if match_aptitude:
            print("[INFO] G1 race found.")
            pyautogui.moveTo(match_aptitude, duration=0.2)
            x, y = pyautogui.position()
            jitter_click(x, y)
            for i in range(2):
              race_btn = pyautogui.locateCenterOnScreen("assets/buttons/race_btn.png", confidence=0.8, minSearchTime=2)
              if race_btn:
                pyautogui.moveTo(race_btn, duration=0.5)
                jitter_click(race_btn.x, race_btn.y)
                time.sleep(0.5)
            return True
      
      for i in range(4):
        pyautogui.scroll(-300)
    
    return False
  else:
    print("[INFO] Looking for race.")
    for i in range(4):
      match_aptitude = pyautogui.locateCenterOnScreen("assets/ui/match_track.png", confidence=0.8, minSearchTime=0.7)
      if match_aptitude:
        print("[INFO] Race found.")
        pyautogui.moveTo(match_aptitude, duration=0.5)
        jitter_click(match_aptitude.x, match_aptitude.y)

        for i in range(2):
          race_btn = pyautogui.locateCenterOnScreen("assets/buttons/race_btn.png", confidence=0.8, minSearchTime=2)
          if race_btn:
            pyautogui.moveTo(race_btn, duration=0.5)
            jitter_click(race_btn.x, race_btn.y)
            time.sleep(0.5)
        return True
      
      for i in range(4):
        pyautogui.scroll(-300)
    
    return False

def race_prep():
  wait_if_paused()
  view_result_btn = pyautogui.locateCenterOnScreen("assets/buttons/view_results.png", confidence=0.8, minSearchTime=20)
  wait_if_paused()
  if view_result_btn:
    jitter_click(view_result_btn.x, view_result_btn.y)
    time.sleep(0.5)
    for i in range(3):
      pyautogui.tripleClick(interval=0.2)
      time.sleep(0.5)

def after_race():
  click(img="assets/buttons/next_btn.png", minSearch=5)
  time.sleep(0.3)
  x, y = pyautogui.position()
  jitter_click(x, y)
  click(img="assets/buttons/next2_btn.png", minSearch=5)

def career_lobby():
  start_emergency_listener()
  # Program start
  while True:
    wait_if_paused()
    # First check, event
    if click(img="assets/icons/event_choice_1.png", minSearch=0.2, text="[INFO] Event found, automatically select top choice."):
      continue

    if click(img="assets/buttons/next2_btn.png", minSearch=0.2, text="[INFO] Race Finished."):
      continue

    # Second check, inspiration
    if click(img="assets/buttons/inspiration_btn.png", minSearch=0.2, text="[INFO] Inspiration found."):
      continue

    if click(img="assets/buttons/next_btn.png", minSearch=0.2):
      continue

    if click(img="assets/buttons/cancel_btn.png", minSearch=0.2):
      continue

    if click(img="assets/buttons/teamtrial_skip_btn.png", minSearch=0.2):
      continue

    # Check if current menu is in career lobby
    tazuna_hint = pyautogui.locateCenterOnScreen("assets/ui/tazuna_hint.png", confidence=0.8, minSearchTime=0.2)

    if tazuna_hint is None:
      print("[INFO] Should be in career lobby.")
      continue

    time.sleep(0.5)

    # Check if there is debuff status
    debuffed = pyautogui.locateOnScreen("assets/buttons/infirmary_btn2.png", confidence=0.9, minSearchTime=1)
    if debuffed:
      if is_infirmary_active((debuffed.left, debuffed.top, debuffed.width, debuffed.height)):
        jitter_click(debuffed.left + debuffed.width // 2, debuffed.top + debuffed.height // 2)
        print("[INFO] Character has debuff, go to infirmary instead.")
        continue

    mood = check_mood()
    mood_index = MOOD_LIST.index(mood)
    minimum_mood = MOOD_LIST.index(MINIMUM_MOOD)
    turn = check_turn()
    year = check_current_year()
    criteria = check_criteria()
    
    print("\n=======================================================================================\n")
    print(f"Year: {year}")
    print(f"Mood: {mood}")
    print(f"Turn: {turn}\n")

    # URA SCENARIO
    wait_if_paused()
    if year == "Finale Season" and turn == "Race Day":
      print("[INFO] URA Finale")
      ura()
      for i in range(2):
        if click(img="assets/buttons/race_btn.png", minSearch=2):
          time.sleep(0.5)
      
      race_prep()
      time.sleep(1)
      after_race()
      continue

    # If calendar is race day, do race
    if turn == "Race Day" and year != "Finale Season":
      print("[INFO] Race Day.")
      race_day()
      continue

    # Mood check
    if mood_index < minimum_mood:
      print("[INFO] Mood is low, trying recreation to increase mood")
      do_recreation()
      continue

    # Check if goals is not met criteria AND it is not Pre-Debut AND turn is less than 10 AND Goal is already achieved
    if criteria.split(" ")[0] != "criteria" and year != "Junior Year Pre-Debut" and turn < 10 and criteria != "Goal Achievedl":
      race_found = do_race()
      if race_found:
        continue
      else:
        # If there is no race matching to aptitude, go back and do training instead
        click(img="assets/buttons/back_btn.png", text="[INFO] Race not found. Proceeding to training.")
        time.sleep(0.5)

    year_parts = year.split(" ")
    # If Prioritize G1 Race is true, check G1 race every turn
    if PRIORITIZE_G1_RACE and year in G1_DATES:
      g1_race_found = do_race(PRIORITIZE_G1_RACE)
      wait_if_paused()
      if g1_race_found:
        continue
      else:
        # If there is no G1 race, go back and do training
        click(img="assets/buttons/back_btn.png", text="[INFO] G1 race not found. Proceeding to training.")
        time.sleep(1)
    
    # Check training button
    if not go_to_training():
      print("[INFO] Training button is not found.")
      continue

    # Last, do training
    time.sleep(random.uniform(0.3, 0.5))
    results_training = check_training()
    wait_if_paused()
    
    best_training = do_something(results_training)

    if best_training:
      time.sleep(random.uniform(0.4, 0.6))
      do_train(best_training)
    else:
      click(img="assets/buttons/back_btn.png")
      time.sleep(random.uniform(0.3, 0.5))
      do_rest()
    time.sleep(1)

if __name__ == "__main__":
    start_emergency_listener()

    while not exit_triggered:
        if not paused:
            print("[INFO] Starting career_lobby loop.")
            career_lobby()
        else:
            print("[INFO] Script is paused.")
            time.sleep(0.5)

