import time, os
from dotenv import load_dotenv
from datetime import datetime, timezone

import RPi.GPIO as GPIO
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

load_dotenv()

REED_PIN = 27
LED_PIN = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(REED_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN, GPIO.OUT)

CHANNEL = os.getenv("PUBNUB_CHANNEL")
DEVICE_ID = os.getenv("PUBNUB_DEVICE_ID")

pnconfig = PNConfiguration()
pnconfig.publish_key = os.getenv("PUBNUB_PUBLISH_KEY")
pnconfig.subscribe_key = os.getenv("PUBNUB_SUBSCRIBE_KEY")
pnconfig.user_id = DEVICE_ID
pubnub = PubNub(pnconfig)

def is_open() -> bool:
    return GPIO.input(REED_PIN) == GPIO.HIGH

def publish_event(open_now: bool):
    msg = {
        "device_id": DEVICE_ID,
        "event": "open" if open_now else "close",
        "is_open": open_now,
        "ts": datetime.now(timezone.utc).isoformat()
    }
    env = pubnub.publish().channel(CHANNEL).message(msg).sync()
    print("Published:", msg, "timetoken:", env.result.timetoken)

def stable_read(delay=0.03) -> bool:
    a = is_open()
    time.sleep(delay)
    b = is_open()
    return a if a == b else b

try:
    last = stable_read()
    GPIO.output(LED_PIN, GPIO.HIGH if last else GPIO.LOW)
    print("Door sensor running. Press CTRL+C to exit.")

    while True:
        cur = stable_read()
        if cur != last:
            GPIO.output(LED_PIN, GPIO.HIGH if cur else GPIO.LOW)
            publish_event(cur)
            last = cur
        time.sleep(0.05)
except KeyboardInterrupt:
	print("\nExiting program...")
finally:
    GPIO.cleanup()
