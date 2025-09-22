import time
import sys
import os
import pygetwindow as gw
import pyautogui
import pyperclip
from elevenlabs import ElevenLabs
import pytesseract
import librosa
from playsound import playsound

# =======================
# ⚙️  Cấu hình
# =======================
ELEVEN_API_KEY = "sk_31b5d4cf5f551c00741db0e39462b316d4f7480dd6164947"
OUTPUT_MP3 = "output_jpn.mp3"
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

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

def ocr_region(region):
    # region = (left, top, width, height)
    screenshot = pyautogui.screenshot(region=region)
    text = pytesseract.image_to_string(screenshot, lang="jpn")
    return text.strip()

    
# =======================
# 1️⃣  Tìm cửa sổ Firefox
# =======================
def find_firefox_window():
    wins = [w for w in gw.getWindowsWithTitle("") if "Mozilla Firefox" in w.title]
    if not wins:
        print("❌ Không tìm thấy cửa sổ Firefox đang mở.")
        sys.exit(1)
    win = wins[0]
    win.activate()
    time.sleep(0.7)
    return win

# =======================
# 2️⃣  Click theo phần trăm
# =======================
def click_relative(win, x_ratio, y_ratio):
    """
    Click vị trí theo % trong cửa sổ.
    x_ratio, y_ratio: 0.0 – 1.0
    """
    x = win.left + int(win.width * x_ratio)
    y = win.top + int(win.height * y_ratio)
    pyautogui.moveTo(x, y, duration=0.6)
    pyautogui.click()
    print(f"👉 Click tại ({x}, {y})")

# =======================
# 3️⃣  Copy text hiển thị
# =======================
def copy_visible_text(win):
   
    x = win.left + int(win.width * 0.350226)
    y = win.top  + int(win.height * 0.363243)
    w = int(win.width * 0.449322)
    h = int(win.height * 0.405405)
   
    img = pyautogui.screenshot(region=(x, y, w, h))
    text = pytesseract.image_to_string(img, lang="jpn")
    return text.strip()


# =======================
# 4️⃣  Đọc TTS
# =======================
def tts_and_play(full_text: str):
    client = ElevenLabs(api_key=ELEVEN_API_KEY)

    # Tạo TTS
    audio_stream = client.text_to_speech.convert(
        text=full_text,
        voice_id="zrHiDhphv9ZnVXBqCLjz",   # voice đa ngôn ngữ
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )

    # Lưu file mp3
    with open(OUTPUT_MP3, "wb") as f:
        for chunk in audio_stream:
            f.write(chunk)
    print("Saved TTS to", OUTPUT_MP3)

    # Phát và lấy thời lượng để biết khi nào stop recording
    play_audio(OUTPUT_MP3)

    # duration cho bạn biết chính xác thời gian phát

    time.sleep(0.1)  # buffer nhỏ nếu cần
    # stop_recording()  # <-- Gọi hàm stop ghi âm tại đây
    # 🔹 6. Click "Stop Recording"
    win = find_firefox_window()
    click_relative(win, 0.581343, 0.808108)
    time.sleep(2)

    # 🔹 7. Click "Submit recording"
    click_relative(win, 0.50, 0.95)
    print("✅ Hoàn tất!")

# =======================
# 5️⃣  Quy trình tự động
# =======================
def main():
    win = find_firefox_window()
    print(f"✅ Tìm thấy: {win.title} | Kích thước: {win.width}x{win.height}")

    # 🔹 1. Click "Start campaign" (thay toạ độ tỉ lệ cho phù hợp)
    click_relative(win, 0.43522 , 0.4963)
    time.sleep(2)

    # 🔹 2. Click "I'm ready!"
    click_relative(win, 0.50, 0.80)
    time.sleep(2)

    # 🔹 3. Click "Start Recording"
    click_relative(win, 0.50, 0.80)
    time.sleep(2)  # đợi text xuất hiện

    # 🔹 4. Click vùng text để focus, sau đó copy
    click_relative(win, 0.50, 0.40)
    time.sleep(1)
    full_text = copy_visible_text(win)
    print("📜 Text lấy được:\n", full_text)

    # 🔹 5. Đọc TTS
    tts_and_play(full_text)



if __name__ == "__main__":
    main()
