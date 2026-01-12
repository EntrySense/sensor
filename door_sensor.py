import os, time, json, requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import RPi.GPIO as GPIO
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.callbacks import SubscribeCallback
from pubnub.enums import PNStatusCategory

load_dotenv()

REED_PIN = int(os.getenv("REED_PIN"))
LED_PIN  = int(os.getenv("LED_PIN"))

DEVICE_ID = int(os.getenv("PUBNUB_DEVICE_ID"))

API_BASE = os.getenv("API_BASE").rstrip("/")
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY")

EVENTS_CHANNEL = os.getenv("PUBNUB_CHANNEL")
SUBSCRIBE_KEY = os.getenv("PUBNUB_SUBSCRIBE_KEY")
PUBLISH_KEY = os.getenv("PUBNUB_PUBLISH_KEY")
DEVICE_PUBNUB_ID = os.getenv("PUBNUB_DEVICE_ID", f"device-{DEVICE_ID}")

CMD_CHANNEL = f"device.{DEVICE_ID}.cmd"

if not EVENTS_CHANNEL:
    raise RuntimeError("Missing PUBNUB_CHANNEL in .env")

if not SUBSCRIBE_KEY or not PUBLISH_KEY:
    raise RuntimeError("Missing PUBNUB_SUBSCRIBE_KEY / PUBNUB_PUBLISH_KEY in .env")

def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def fetch_arm_status() -> bool:
    """
    Fetch current arm_status from backend.
    Endpoint expected: GET /devices/<device_id>/status with header X-Device-Key
    """
    if not DEVICE_API_KEY:
        print("[WARN] DEVICE_API_KEY not set. Defaulting to DISARMED.")
        return False

    url = f"{API_BASE}/devices/{DEVICE_ID}/status"
    try:
        r = requests.get(url, headers={"X-Device-Key": DEVICE_API_KEY}, timeout=5)
        data = r.json() if r.content else {}
        if not r.ok:
            print(f"[WARN] Status fetch failed {r.status_code}: {data}")
            return False
        return bool(data.get("armed", False))
    except Exception as e:
        print("[WARN] Status fetch error:", e)
        return False

def publish_event(pubnub: PubNub, event_name: str):
    msg = {
        "device_id": DEVICE_ID,
        "event": event_name,
        "ts": iso_now(),
    }
    pubnub.publish().channel(EVENTS_CHANNEL).message(msg).sync()
    print("[PUB] sent:", msg)

armed = False

class CommandListener(SubscribeCallback):
    def message(self, pubnub, event):
        global armed
        msg = event.message

        cmd = msg.get("cmd")
        if cmd == "arm":
            armed = True
            print("Device is", "armed" if armed else "disarmed")
        elif cmd == "disarm":
            armed = False
            print("Device is", "armed" if armed else "disarmed")
        else:
            print("[CMD] ignored:", msg)

    def status(self, pubnub, status):
        if status.category == PNStatusCategory.PNConnectedCategory:
            print("[PUBNUB] Connected (subscribed)")
        elif status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
            print("[PUBNUB] Unexpected disconnect")
        elif status.category == PNStatusCategory.PNReconnectedCategory:
            print("[PUBNUB] Reconnected")

pnconfig = PNConfiguration()
pnconfig.subscribe_key = SUBSCRIBE_KEY
pnconfig.publish_key = PUBLISH_KEY
pnconfig.user_id = DEVICE_PUBNUB_ID
pubnub = PubNub(pnconfig)

pubnub.add_listener(CommandListener())
pubnub.subscribe().channels([CMD_CHANNEL]).execute()

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(REED_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN, GPIO.OUT)

armed = fetch_arm_status()
print("Boot status:", "armed" if armed else "disarmed")

def read_door_open() -> bool:
    return GPIO.input(REED_PIN) == GPIO.HIGH

last_open = None

try:
    # initialize state
    last_open = read_door_open()
    GPIO.output(LED_PIN, GPIO.HIGH if last_open else GPIO.LOW)
    publish_event(pubnub, "open" if last_open else "close")

    while True:
        is_open = read_door_open()

        # LED reflects physical door state (independent of armed)
        GPIO.output(LED_PIN, GPIO.HIGH if is_open else GPIO.LOW)

        if is_open != last_open:
            last_open = is_open
            publish_event(pubnub, "open" if is_open else "close")

        time.sleep(0.1)

except KeyboardInterrupt:
    print("Exiting...")

finally:
    GPIO.cleanup()
