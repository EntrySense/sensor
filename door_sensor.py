import RPi.GPIO as GPIO
import time

LED_PIN = 17  # GPIO17 (pin 11)
REED_PIN = 27 # GPIO27 (pin 13)

GPIO.setmode(GPIO.BCM)

# Setup pins
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(REED_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Door sensor running. Press CTRL+C to exit.")

try:
    while True:
        door_state = GPIO.input(REED_PIN)

        if door_state == GPIO.LOW:
            # Door closed (magnet together)
            GPIO.output(LED_PIN, GPIO.LOW)
            print("Door CLOSED → LED OFF")
        else:
            # Door open (magnet separated)
            GPIO.output(LED_PIN, GPIO.HIGH)
            print("Door OPEN → LED ON")

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nExiting program...")

finally:
    GPIO.cleanup()
