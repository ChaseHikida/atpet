import time
import board
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import psutil
import subprocess

i2c = busio.I2C(board.SCL, board.SDA)
display = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)
display.fill(0)
display.show()

image = Image.new('1', (display.width, display.height))
draw = ImageDraw.Draw(image)
font = ImageFont.load_default()

def get_cpu_temp():
    temp = subprocess.check_output(['vcgencmd', 'measure_temp'])
    return temp.decode('utf-8').replace("temp=","").replace("'C\n","") + "C"

def get_connected_clients():
    try:
        result = subprocess.check_output(['iw', 'dev', 'wlan0', 'station', 'dump'])
        return result.decode('utf-8').count('Station')
    except:
        return 0

def get_pihole_stats():
    try:
        result = subprocess.check_output(['pihole', '-c', '-j'])
        import json
        data = json.loads(result)
        return data.get('ads_blocked_today', 0)
    except:
        return 0

def get_ip(interface):
    try:
        result = subprocess.check_output(['ip', 'addr', 'show', interface])
        for line in result.decode('utf-8').split('\n'):
            if 'inet ' in line:
                return line.split()[1].split('/')[0]
    except:
        return "N/A"

print("OLED display starting...")

try:
    while True:
        draw.rectangle((0, 0, display.width, display.height), outline=0, fill=0)

        cpu_temp = get_cpu_temp()
        clients = get_connected_clients()
        blocked = get_pihole_stats()
        lte_ip = get_ip('wwan0')
        wifi_ip = get_ip('wlan0')
        ram = psutil.virtual_memory().percent

        draw.text((0, 0),  f"Temp: {cpu_temp}",       font=font, fill=255)
        draw.text((0, 10), f"RAM:  {ram:.0f}%",        font=font, fill=255)
        draw.text((0, 20), f"Clients: {clients}",      font=font, fill=255)
        draw.text((0, 30), f"Blocked: {blocked}",      font=font, fill=255)
        draw.text((0, 40), f"LTE: {lte_ip[:15]}",      font=font, fill=255)
        draw.text((0, 50), f"WiFi: {wifi_ip}",         font=font, fill=255)

        display.image(image)
        display.show()
        time.sleep(5)

except KeyboardInterrupt:
    display.fill(0)
    display.show()
    print("\nStopped")