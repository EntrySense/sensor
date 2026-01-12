import time, os
import RPi.GPIO as GPIO
from dotenv import load_dotenv
from datetime import datetime, timezone
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.callbacks import SubscribeCallback

load_dotenv()

REED_PIN = 27
LED_PIN = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(REED_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN, GPIO.OUT)

CHANNEL = os.getenv("PUBNUB_CHANNEL")
DEVICE_ID = int(os.getenv("PUBNUB_DEVICE_ID"))
CMD_CHANNEL = f"device.{DEVICE_ID}.cmd"

pnconfig = PNConfiguration()
pnconfig.publish_key = os.getenv("PUBNUB_PUBLISH_KEY")
pnconfig.subscribe_key = os.getenv("PUBNUB_SUBSCRIBE_KEY")
pnconfig.user_id = f"pi-device-{DEVICE_ID}"
pubnub = PubNub(pnconfig)

armed = True

class CommandListener(SubscribeCallback):
    def message(self, pubnub, event):
        global armed
        cmd = event.message.get("cmd")
        armed = (cmd == "arm")
        print("Device is", "armed" if armed else "disarmed")

pubnub.add_listener(CommandListener())
pubnub.subscribe().channels(CMD_CHANNEL).execute()

print("Listening for commands on", CMD_CHANNEL)

def is_open() -> bool:
    return GPIO.input(REED_PIN) == GPIO.HIGH

def publish_event(open_now: bool):
    msg = {
        "device_id": DEVICE_ID,
        "event": "open" if open_now else "close",
        "armed": armed,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    pubnub.publish().channel(CHANNEL).message(msg).sync()
    print("Published:", msg)

try:
    last = is_open()
    GPIO.output(LED_PIN, GPIO.HIGH if last else GPIO.LOW)

    while True:
        cur = is_open()
        if cur != last:
            GPIO.output(LED_PIN, GPIO.HIGH if cur else GPIO.LOW)
            publish_event(cur)
            last = cur
        time.sleep(0.05)
finally:
    GPIO.cleanup()

while True:
    time.sleep(60)
