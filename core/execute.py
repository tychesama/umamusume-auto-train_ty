import pyautogui
import time
import json
import random
import math


pyautogui.useImageNotFoundException(False)

from core.state import check_support_card, check_failure, check_turn, check_mood, check_current_year, check_criteria
from core.logic import do_something
from utils.constants import MOOD_LIST
from core.recognizer import is_infirmary_active, match_template
from utils.scenario import ura

with open("config.json", "r", encoding="utf-8") as file:
  config = json.load(file)

MAX_FAILURE = config["maximum_failure"]
MINIMUM_MOOD = config["minimum_mood"]
PRIORITIZE_G1_RACE = config["prioritize_g1_race"]

def curved_move(start_x, start_y, end_x, end_y, duration=0.4, steps=20):
  """Move in a curved, human-like arc from (start_x, start_y) to (end_x, end_y)."""
  for i in range(steps + 1):
    t = i / steps
    # Sine-based easing for a slightly curved motion
    intermediate_x = start_x + (end_x - start_x) * t + math.sin(t * math.pi) * random.randint(-10, 10)
    intermediate_y = start_y + (end_y - start_y) * t + math.cos(t * math.pi) * random.randint(-10, 10)
    pyautogui.moveTo(intermediate_x, intermediate_y, duration / steps)


def random_mouse_wiggle(wiggles=5, max_distance=100, max_delay=2.5):
  """
  Simulate random mouse movements around the current cursor position.

  Parameters:
  - wiggles: number of movements
  - max_distance: maximum distance (in pixels) to move in any direction
  - max_delay: maximum delay between movements (seconds)
  """
  screen_width, screen_height = pyautogui.size()
  start_x, start_y = pyautogui.position()

  for _ in range(wiggles):
    # Random offset within max_distance bounds
    dx = random.randint(-max_distance, max_distance)
    dy = random.randint(-max_distance, max_distance)

    # Make sure the movement stays on screen
    new_x = max(0, min(start_x + dx, screen_width - 1))
    new_y = max(0, min(start_y + dy, screen_height - 1))

    # Use curved movement
    curved_move(start_x, start_y, new_x, new_y, duration=random.uniform(0.3, 0.8))

    # Random pause to simulate idle fidgeting
    time.sleep(random.uniform(0.5, max_delay))

    # Update current position
    start_x, start_y = new_x, new_y

def jitter_click(x, y, clicks=1, duration=None, jitter_x=55, jitter_y=15):
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

  need_wit = False
  duration = 0.2

  for key, icon_path in training_types.items():
    pos = pyautogui.locateCenterOnScreen(icon_path, confidence=0.8)
    if pos:
      if need_wit == False or key == "wit":
        pyautogui.moveTo(pos, duration=0.2)
        pyautogui.mouseDown()
      else:
        continue

      failure_chance = check_failure()

      if int(failure_chance) > MAX_FAILURE + 5:
        print(f"Fail too high, SKIPPING")
        # set the value of spd sta pwr guts to fail 99
        need_wit = True
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
  click(img="assets/buttons/races_btn.png", minSearch=10)
  click(img="assets/buttons/ok_btn.png", minSearch=0.7)

  found = race_select(prioritize_g1=prioritize_g1)
  if not found:
    print("[INFO] No race found.")
    return False

  race_prep()
  time.sleep(1)
  after_race()
  return True

def race_day():
  click(img="assets/buttons/race_day_btn.png", minSearch=10)
  
  click(img="assets/buttons/ok_btn.png", minSearch=0.7)
  time.sleep(0.5)

  for i in range(2):
    click(img="assets/buttons/race_btn.png", minSearch=2)
    time.sleep(0.5)

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
  view_result_btn = pyautogui.locateCenterOnScreen("assets/buttons/view_results.png", confidence=0.8, minSearchTime=20)
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
  # Program start
  while True:
    # First check, event
    if click(img="assets/icons/event_choice_1.png", minSearch=0.2, text="[INFO] Event found, automatically select top choice."):
      continue

    # Second check, inspiration
    if click(img="assets/buttons/inspiration_btn.png", minSearch=0.2, text="[INFO] Inspiration found."):
      continue

    if click(img="assets/buttons/next_btn.png", minSearch=0.2):
      continue

    if click(img="assets/buttons/cancel_btn.png", minSearch=0.2):
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
    if PRIORITIZE_G1_RACE and year_parts[0] != "Junior" and len(year_parts) > 3 and year_parts[3] not in ["Jul", "Aug"]:
      g1_race_found = do_race(PRIORITIZE_G1_RACE)
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
    
    best_training = do_something(results_training)

    if best_training:
      time.sleep(random.uniform(0.4, 0.6))
      do_train(best_training)
    else:
      click(img="assets/buttons/back_btn.png")
      time.sleep(random.uniform(0.3, 0.5))
      do_rest()
    time.sleep(1)

    if random.random() < 0.01:
      print("[DEBUG] Simulating random mouse wiggle.")
      random_mouse_wiggle(wiggles=2, max_distance=500, max_delay=2)



