#!/usr/bin/env python3
import json
import subprocess
import threading
import time

import RPi.GPIO as GPIO
import board
import busio
import psutil
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
FAN_PIN    = 18      # GPIO18 = physical pin 12
TEMP_LOW   = 50      # °C — fan at minimum duty below this
TEMP_HIGH  = 70      # °C — fan at full speed above this
DUTY_MIN   = 30      # % — keeps fan alive at low temps
DUTY_MAX   = 100     # %
PWM_FREQ   = 25_000  # Hz

POLL_FAN     = 10    # seconds between fan updates
POLL_DISPLAY = 5     # seconds between display refreshes


# ---------------------------------------------------------------------------
class FanController:
    """Reads CPU temperature and drives a PWM fan via GPIO."""

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(FAN_PIN, GPIO.OUT)
        self._pwm = GPIO.PWM(FAN_PIN, PWM_FREQ)
        self._pwm.start(DUTY_MIN)
        self.duty  = DUTY_MIN   # current duty cycle (shared read by display)
        self.temp  = 0.0        # current temperature
        self._stop = threading.Event()

    # ------------------------------------------------------------------
    def _read_temp(self) -> float:
        raw = subprocess.check_output(["vcgencmd", "measure_temp"])
        return float(raw.decode().replace("temp=", "").replace("'C\n", ""))

    def _temp_to_duty(self, temp: float) -> int:
        if temp <= TEMP_LOW:
            return DUTY_MIN
        if temp >= TEMP_HIGH:
            return DUTY_MAX
        ratio = (temp - TEMP_LOW) / (TEMP_HIGH - TEMP_LOW)
        return int(DUTY_MIN + ratio * (DUTY_MAX - DUTY_MIN))

    # ------------------------------------------------------------------
    def run(self):
        print("Fan controller started.")
        while not self._stop.is_set():
            try:
                self.temp = self._read_temp()
                self.duty = self._temp_to_duty(self.temp)
                self._pwm.ChangeDutyCycle(self.duty)
            except Exception as exc:
                print(f"[fan] error: {exc}")
            self._stop.wait(POLL_FAN)

    def stop(self):
        self._stop.set()
        self._pwm.stop()
        GPIO.cleanup()
        print("Fan controller stopped.")


# ---------------------------------------------------------------------------
class OLEDDisplay:
    """Renders system stats on a 128×64 SSD1306 OLED over I²C."""

    def __init__(self, fan: FanController):
        self._fan = fan
        i2c = busio.I2C(board.SCL, board.SDA)
        self._disp = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)
        self._disp.fill(0)
        self._disp.show()
        self._image = Image.new("1", (self._disp.width, self._disp.height))
        self._draw  = ImageDraw.Draw(self._image)
        self._font  = ImageFont.load_default()
        self._stop  = threading.Event()

    # ------------------------------------------------------------------
    @staticmethod
    def _get_clients() -> int:
        try:
            out = subprocess.check_output(["iw", "dev", "wlan0", "station", "dump"])
            return out.decode().count("Station")
        except Exception:
            return 0

    @staticmethod
    def _get_pihole_blocked() -> int:
        try:
            raw  = subprocess.check_output(["pihole", "-c", "-j"])
            data = json.loads(raw)
            return data.get("ads_blocked_today", 0)
        except Exception:
            return 0

    @staticmethod
    def _get_ip(iface: str) -> str:
        try:
            out = subprocess.check_output(["ip", "addr", "show", iface])
            for line in out.decode().splitlines():
                if "inet " in line:
                    return line.split()[1].split("/")[0]
        except Exception:
            pass
        return "N/A"

    # ------------------------------------------------------------------
    def _render(self):
        d = self._draw
        W, H = self._disp.width, self._disp.height

        # Clear
        d.rectangle((0, 0, W, H), outline=0, fill=0)

        temp     = self._fan.temp
        duty     = self._fan.duty
        ram      = psutil.virtual_memory().percent
        clients  = self._get_clients()
        blocked  = self._get_pihole_blocked()
        lte_ip   = self._get_ip("wwan0")
        wifi_ip  = self._get_ip("wlan0")

        rows = [
            f"Temp:    {temp:.1f}C  Fan:{duty}%",
            f"RAM:     {ram:.0f}%",
            f"Clients: {clients}",
            f"Blocked: {blocked}",
            f"LTE:  {lte_ip[:16]}",
            f"WiFi: {wifi_ip[:16]}",
        ]
        for i, text in enumerate(rows):
            d.text((0, i * 10), text, font=self._font, fill=255)

        self._disp.image(self._image)
        self._disp.show()

    # ------------------------------------------------------------------
    def run(self):
        print("OLED display started.")
        while not self._stop.is_set():
            try:
                self._render()
            except Exception as exc:
                print(f"[oled] error: {exc}")
            self._stop.wait(POLL_DISPLAY)

    def stop(self):
        self._stop.set()
        self._disp.fill(0)
        self._disp.show()
        print("OLED display stopped.")


# ---------------------------------------------------------------------------
def main():
    fan     = FanController()
    display = OLEDDisplay(fan)

    fan_thread     = threading.Thread(target=fan.run,     daemon=True)
    display_thread = threading.Thread(target=display.run, daemon=True)

    fan_thread.start()
    display_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        display.stop()
        fan.stop()


if __name__ == "__main__":
    main()
