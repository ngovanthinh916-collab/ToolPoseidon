import os
import time
import random
import sys
import math
import librosa
import sounddevice as sd
from playsound import playsound

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

from elevenlabs.client import ElevenLabs

# ===============================
# Cấu hình
# ===============================
ELEVEN_API_KEY = "sk_31b5d4cf5f551c00741db0e39462b316d4f7480dd6164947"
PROFILE_PATH = r"C:\Users\LENOVO\AppData\Roaming\Mozilla\Firefox\Profiles\3appt8ik.default-release"
GECKODRIVER_PATH = r"C:\geckodriver\geckodriver.exe"
TARGET_URL = "https://app.psdn.ai/campaigns/0d800fe2-d8b8-4078-99f0-311cf365c649"
OUT_MP3 = "output_jpn.mp3"

# Delay config (tweak these to make interactions slower/faster)
MIN_ACTION_DELAY = 0.8   # minimal random pause before actions (seconds)
MAX_ACTION_DELAY = 2.2   # maximal random pause before actions (seconds)
MOVE_STEP_DELAY = 0.03   # pause between small mouse move steps (seconds)
MOVE_STEPS = 18          # number of intermediate mouse steps when moving

# ===============================
# Khởi tạo ElevenLabs
# ===============================
client = ElevenLabs(api_key=ELEVEN_API_KEY)

# ===============================
# HELPER: human-like delays & mouse movement
# ===============================
def human_delay(min_s=MIN_ACTION_DELAY, max_s=MAX_ACTION_DELAY):
    """Ngẫu nhiên delay giữa các thao tác để giống người."""
    t = random.uniform(min_s, max_s)
    # thêm chút jitter cho realism
    jitter = random.uniform(-0.15, 0.15)
    t = max(0.0, t + jitter)
    print(f"[human_delay] sleeping {t:.2f}s")
    time.sleep(t)

def get_element_center(driver, element):
    """
    Trả về (x, y) center của element trên viewport (relative to window).
    Dùng JS để lấy boundingClientRect.
    """
    rect = driver.execute_script("""
        const r = arguments[0].getBoundingClientRect();
        return {left: r.left, top: r.top, width: r.width, height: r.height, x: r.x, y: r.y};
    """, element)
    cx = rect["left"] + rect["width"] / 2
    cy = rect["top"] + rect["height"] / 2
    return int(cx), int(cy)

def human_move_to_element(driver, element, steps=MOVE_STEPS, step_delay=MOVE_STEP_DELAY):
    """
    Mô phỏng rê chuột theo nhiều bước nhỏ tới center của element.
    Sử dụng ActionChains.move_by_offset nhiều lần (relative moves).
    """
    try:
        actions = ActionChains(driver)
        # move mouse to somewhere near current position first (no guarantee of current pos),
        # we start by moving to element directly using move_to_element to get a baseline cursor pos,
        # then perform small relative moves to the center to simulate human movement.
        # NOTE: move_to_element may jump; we then perform micro-steps to center.
        actions.move_to_element(element).perform()
        human_delay(0.05, 0.18)

        # compute target center in viewport coordinates and current pointer approximation
        target_x, target_y = get_element_center(driver, element)

        # We can't reliably read actual OS cursor position from Selenium.
        # So simulate smooth micro-movements by moving by small offsets relative to element.
        # We'll perform a spiral-ish approach: start from an offset circle and step inward.
        radius = max(10, min(120, int(max(20, target_x * 0.02))))  # heuristic radius
        for i in range(steps):
            # angle decreasing to approach center
            angle = (i / float(max(1, steps))) * (2 * math.pi) * (0.5 + random.random() * 0.5)
            r = radius * (1 - (i / float(steps))) * (0.6 + random.random() * 0.4)
            offset_x = int(r * math.cos(angle))
            offset_y = int(r * math.sin(angle))
            try:
                # move relative to element center
                actions.move_to_element_with_offset(element, offset_x, offset_y).perform()
            except Exception:
                # fallback to simple move_to_element
                try:
                    actions.move_to_element(element).perform()
                except Exception:
                    pass
            time.sleep(step_delay * (0.8 + random.random() * 0.6))
        # final precise move to center
        try:
            actions.move_to_element_with_offset(element, 0, 0).perform()
        except Exception:
            try:
                actions.move_to_element(element).perform()
            except Exception:
                pass
        human_delay(0.05, 0.18)
    except Exception as e:
        print("[human_move_to_element] warning, move failed:", e)
        # ignore and continue — we'll still attempt to click

# ===============================
# Hàm phát âm thanh
# ===============================
def play_audio(filepath: str):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"{filepath} not found")
    try:
        print("▶ Playing with playsound:", filepath)
        playsound(filepath)
        return
    except Exception as e:
        print("playsound failed:", e)
    # fallback với sounddevice + librosa
    try:
        data, sr = librosa.load(filepath, sr=None)
        print(f"Fallback playback: {librosa.get_duration(y=data, sr=sr):.2f}s, sr={sr}")
        sd.play(data, sr)
        sd.wait()
    except Exception as e:
        print("Fallback playback also failed:", e)
        raise

# ===============================
# Cấu hình Firefox
# ===============================
service = Service(executable_path=GECKODRIVER_PATH)
profile = FirefoxProfile(PROFILE_PATH)
options = Options()
options.profile = profile

options.set_preference("dom.webdriver.enabled", False)
options.set_preference("useAutomationExtension", False)
options.set_preference("webdriver_enable.native_events", False)
options.set_preference("toolkit.telemetry.reportingpolicy.firstRun", False)
options.add_argument("--disable-blink-features=AutomationControlled")
options.set_preference(
    "general.useragent.override",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"
)

# ===============================
# Flow chính
# ===============================
driver = None
try:
    driver = webdriver.Firefox(service=service, options=options)
    print("Current profile directory (moz:profile):", driver.capabilities.get("moz:profile"))
    driver.get(TARGET_URL)

    # Kiểm tra login (nếu có)
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[type='password']"))
        )
        print("Login page detected. Please login manually in that browser profile and rerun.")
        raise SystemExit("Login required")
    except Exception:
        print("No login page detected. Proceeding to task...")

    # ===== Click "Start campaign" (human-like) =====
    human_delay()
    start_campaign_btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'inline-flex') and contains(text(), 'Start campaign')]"))
    )
    human_move_to_element(driver, start_campaign_btn)
    human_delay(0.25, 0.6)
    start_campaign_btn.click()
    print("Clicked Start campaign")
    human_delay()

    # ===== Click "I'm ready!" =====
    ready_btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'inline-flex') and contains(text(), \"I'm ready!\")]"))
    )
    human_move_to_element(driver, ready_btn)
    human_delay(0.2, 0.7)
    ready_btn.click()
    print("Clicked I'm ready!")
    human_delay()

    # ===== Click "Start Recording" =====
    start_recording_btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'inline-flex') and contains(text(), 'Start Recording')]"))
    )
    human_move_to_element(driver, start_recording_btn)
    human_delay(0.3, 1.0)
    start_recording_btn.click()
    print("Clicked Start Recording")
    human_delay(2.0, 3.0)  # chờ lâu hơn để nội dung load

    # ==== Đợi text tiếng Nhật thực sự render ====
    jpn_xpath = (
        "//div[contains(@class,'text-white') "
        "and contains(@class,'text-[24px]') "
        "and contains(@class,'font-normal') "
        "and contains(@class,'leading-normal')]"
    )
    # đợi một ký tự đặc trưng tiếng Nhật (dấu '。') xuất hiện
    WebDriverWait(driver, 40).until(
        EC.text_to_be_present_in_element((By.XPATH, jpn_xpath), "。")
    )
    element = driver.find_element(By.XPATH, jpn_xpath)
    # Before reading, do a small human-like move + delay to the element
    human_move_to_element(driver, element)
    human_delay(0.5, 1.2)
    full_text = element.text.strip()
    print("Extracted Japanese text length:", len(full_text))
    print("Extracted Japanese text:", full_text)

    # ===============================
    # TTS ElevenLabs
    # ===============================
    print("Generating TTS...")
    audio_stream = client.text_to_speech.convert(
        text=full_text,
        voice_id="pNInz6obpgDQGcFmaJgB",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )
    with open(OUT_MP3, "wb") as f:
        for chunk in audio_stream:
            f.write(chunk)
    print("Saved TTS to", OUT_MP3)

    # Phát audio
    play_audio(OUT_MP3)
    human_delay(0.6, 1.6)

    # Click "Stop Recording" (mô phỏng)
    stop_btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH,
            "//button[contains(@class, 'inline-flex') and contains(@class, 'border') and .//div[contains(@class, 'animate-pulse')]]"
        ))
    )
    human_move_to_element(driver, stop_btn)
    human_delay(0.2, 0.8)
    stop_btn.click()
    print("Clicked Stop Recording")
    human_delay(1.0, 2.0)

    # Click "Submit recording"
    submit_btn = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Submit recording')]"))
    )
    human_move_to_element(driver, submit_btn)
    human_delay(0.3, 0.9)
    submit_btn.click()
    print("Clicked Submit recording")
    human_delay(1.5, 2.5)

    # chờ xíu rồi kết thúc
    time.sleep(1.2)

except SystemExit as se:
    print("Exiting:", se)
except Exception as main_e:
    print("Error occurred:", main_e)
finally:
    if driver:
        driver.quit()
