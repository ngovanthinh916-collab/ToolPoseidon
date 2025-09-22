from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from elevenlabs.client import ElevenLabs
from playsound import playsound
import librosa
import sounddevice as sd
import os
import time
import sys

# ===============================
# Cấu hình
# ===============================
ELEVEN_API_KEY = "sk_31b5d4cf5f551c00741db0e39462b316d4f7480dd6164947"
PROFILE_PATH = r"C:\Users\LENOVO\AppData\Roaming\Mozilla\Firefox\Profiles\3appt8ik.default-release"
GECKODRIVER_PATH = r"C:\geckodriver\geckodriver.exe"
TARGET_URL = "https://app.psdn.ai/campaigns/0d800fe2-d8b8-4078-99f0-311cf365c649"
OUT_MP3 = "output_jpn.mp3"

client = ElevenLabs(api_key=ELEVEN_API_KEY)

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

def play_audio(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"{filepath} not found")
    try:
        print("Playing with playsound:", filepath)
        playsound(filepath)
        return
    except Exception as e:
        print("playsound failed:", e)
    try:
        data, sr = librosa.load(filepath, sr=None)
        print(f"Fallback playback: {librosa.get_duration(y=data, sr=sr):.2f}s, sr={sr}")
        sd.play(data, sr)
        sd.wait()
    except Exception as e:
        print("Fallback playback also failed:", e)
        raise

driver = None
try:
    driver = webdriver.Firefox(service=service, options=options)
    print("Current profile directory (moz:profile):", driver.capabilities.get("moz:profile"))
    driver.get(TARGET_URL)

    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[type='password']"))
        )
        print("Login page detected. Please login manually.")
        raise SystemExit("Login required")
    except Exception:
        print("No login page detected. Proceeding to task...")

    # Click các nút theo thứ tự
    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'inline-flex') and contains(text(), 'Start campaign')]"))
    ).click()
    print("Clicked Start campaign")

    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), \"I'm ready!\")]"))
    ).click()
    print("Clicked I'm ready!")

    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Start Recording')]"))
    ).click()
    print("Clicked Start Recording")

    # ==== SỬA QUAN TRỌNG: đợi text tiếng Nhật thực sự render ====
    jpn_xpath = (
        "//div[contains(@class,'text-white') "
        "and contains(@class,'text-[24px]') "
        "and contains(@class,'font-normal') "
        "and contains(@class,'leading-normal')]"
    )
    text_element = WebDriverWait(driver, 30).until(
        EC.text_to_be_present_in_element(
            (By.XPATH, jpn_xpath),
            "。"
        )
    )  # đợi có ít nhất một ký tự tiếng Nhật (dấu chấm '。' giúp phân biệt)
    # Lấy element sau khi đã có nội dung
    element = driver.find_element(By.XPATH, jpn_xpath)
    full_text = element.text.strip()
    print("Extracted Japanese text length:", len(full_text))
    print("Extracted Japanese text:", full_text)
    # ============================================================

    # TTS ElevenLabs
    audio_stream = client.text_to_speech.convert(
        text=full_text,
        voice_id="pNInz6obpgDQGcFmaJgB",     # dùng voice hỗ trợ đa ngôn ngữ
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )
    with open(OUT_MP3, "wb") as f:
        for chunk in audio_stream:
            f.write(chunk)
    print("Saved TTS to", OUT_MP3)

    play_audio(OUT_MP3)
    time.sleep(0.3)

    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'inline-flex') and contains(@class, 'border') and .//div[contains(@class, 'animate-pulse')]]"))
    ).click()
    print("Clicked Stop Recording")

    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Submit recording')]"))
    ).click()
    print("Clicked Submit recording")

    time.sleep(2)

except SystemExit as se:
    print("Exiting:", se)
except Exception as main_e:
    print("Error occurred:", main_e)
finally:
    if driver:
        driver.quit()
