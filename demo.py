import time
from wifi_config import connect
from sensors import (
    measure_distance_cm, read_ldr, set_pump, set_led, set_buzzer,
    LDR_LIGHT_THRESHOLD, TANK_HIGH_CM, DRAIN_OVERFLOW_CM, is_daytime
)
from iot_client import send_to_thingspeak

# Connect Wi-Fi
if not connect():
    pass  # proceed even if offline; system still controls locally

# main control parameters
PUMP_ENABLED = True
PUMP_HYSTERESIS_CM = 2
last_pump_state = False
last_send = 0
SEND_INTERVAL = 30  # seconds

def control_logic():
    global last_pump_state
    dist = measure_distance_cm()
    ldr_val = read_ldr()
    # handle distance None
    if dist is None:
        dist = -1
    # Pump control: if tank low (distance > TANK_HIGH_CM) turn pump ON
    # (Assumes sensor mounted at top; larger distance -> lower water level)
    pump_on = False
    if PUMP_ENABLED and dist >= 0:
        if dist > TANK_HIGH_CM + PUMP_HYSTERESIS_CM:
            pump_on = True
        elif dist < TANK_HIGH_CM - PUMP_HYSTERESIS_CM:
            pump_on = False
        else:
            pump_on = last_pump_state
    set_pump(pump_on)
    last_pump_state = pump_on

    # Streetlight control (LDR + RTC). If dark OR night -> LED on
    dark = ldr_val < LDR_LIGHT_THRESHOLD
    led_on = dark or (not is_daytime())
    set_led(led_on)

    # Drainage overflow: if distance below overflow threshold (close to sensor)
    overflow = (dist >= 0 and dist < DRAIN_OVERFLOW_CM)
    set_buzzer(overflow)

    return {
        "distance_cm": dist,
        "ldr": ldr_val,
        "pump": int(pump_on),
        "led": int(led_on),
        "buzzer": int(overflow),
    }

# run loop
while True:
    data = control_logic()
    now = time.time()
    if now - last_send >= SEND_INTERVAL:
        # map fields to ThingSpeak field1..5 (added buzzer to field5)
        fields = {
            "field1": data["distance_cm"],
            "field2": data["ldr"],
            "field3": data["pump"],
            "field4": data["led"],
            "field5": data["buzzer"],  # Added buzzer status to data sent
        }
        ok = send_to_thingspeak(fields)
        last_send = now
    time.sleep(1)
