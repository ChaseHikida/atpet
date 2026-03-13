#!/usr/bin/env python3
import RPi.GPIO as GPIO
import subprocess
import time

FAN_PIN = 18      # GPIO18 = Pin 12
TEMP_LOW  = 50    # Below this: fan at minimum speed
TEMP_HIGH = 70    # Above this: fan at maximum speed
PWM_FREQ  = 25000 # 25kHz PWM frequency

GPIO.setmode(GPIO.BCM)
GPIO.setup(FAN_PIN, GPIO.OUT)
pwm = GPIO.PWM(FAN_PIN, PWM_FREQ)
pwm.start(0)

def get_temp():
    result = subprocess.check_output(['vcgencmd', 'measure_temp'])
    temp_str = result.decode('utf-8').replace("temp=","").replace("'C\n","")
    return float(temp_str)

def temp_to_duty(temp):
    if temp <= TEMP_LOW:
        return 100   # Minimum speed (not 0 — keeps fan alive)
    elif temp >= TEMP_HIGH:
        return 100  # Full speed
    else:
        # Linear scale between low and high
        return int(30 + (temp - TEMP_LOW) / (TEMP_HIGH - TEMP_LOW) * 70)

print("Fan control running...")

try:
    while True:
        temp = get_temp()
        duty = temp_to_duty(temp)
        pwm.ChangeDutyCycle(duty)
        print(f"Temp: {temp}C  Fan: {duty}%")
        time.sleep(10)

except KeyboardInterrupt:
    pwm.stop()
    GPIO.cleanup()
    print("\nStopped")