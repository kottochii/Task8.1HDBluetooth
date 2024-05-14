from bluepy import btle
import time
import threading
import RPi.GPIO as GPIO

LED_PIN = 7
SOUND_PIN = 5

#init pins
GPIO.setmode(GPIO.BOARD)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(SOUND_PIN, GPIO.OUT)

#pin cleanup routine
def cleanup():
    GPIO.cleanup(LED_PIN)
    GPIO.cleanup(SOUND_PIN)

#var that actually is setting the interval of the led/sound
#set to None to turn off
interval = None

#sets pins to the given state
prev_state = None
def set_pins_state(state):
    global prev_state
    if not(prev_state == state):
        prev_state = state
        GPIO.output(LED_PIN, state)
        GPIO.output(SOUND_PIN, state)
set_pins_state(False)

#actual controller, calls the top when required
class IndicatorControllingThread:
    _state = False
    def __init__(self):
        #making asynchronous task
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run)

    def _run(self):
        global interval
        #runs until stopped
        while not self._stop_event.is_set():
            #turn state to false if needs to sleep
            if interval == None:
                self._state = False
                set_pins_state(False)
                continue
            self._state = not self._state
            set_pins_state(self._state)
            time.sleep(interval)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()
        

# distance to time interval conversion
# the greater the distance the longer the interrval if
def distance_to_interval(distance):
    if distance < 0: # faulty connection
        return None
    if distance < 3:
        return 0.2
    if distance < 6:
        return 0.5
    if distance < 13:
        return 0.8
    if distance < 20: # from 20 no interval is required
        return 1
    return None

#the event handler on message
class MainDelegate(btle.DefaultDelegate):
    def __init__(self):
        btle.DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data):
        global interval
        try:
            #decode the message
            decoded = data.decode('utf-8')
            print(f"Received: {decoded}")
            # get the interval, affects the global interval
            # so also sets the indicator controller
            interval = distance_to_interval(float(decoded))
            #print out so could be seen
            print("Interval: " + str(interval) + ";Distance: " + str(decoded))
        finally:
            return

def receive_data(target_address):
    print(f"Connecting to {target_address}...")
    try:
        # Connect to the device
        peripheral = btle.Peripheral(target_address)
        peripheral.setDelegate(MainDelegate())

        print("Connected. Waiting for notifications...")

        # Enable notifications for the characteristic
        service_uuid = "180D"
        characteristic_uuid = "2A37"
        
        service = peripheral.getServiceByUUID(service_uuid)
        characteristic = service.getCharacteristics(characteristic_uuid)[0]
        
        # Enable notifications
        setup_data = b'\x01\x00'
        characteristic_handle = characteristic.getHandle() + 1
        peripheral.writeCharacteristic(characteristic_handle, setup_data, withResponse=True)

        while True:
            if peripheral.waitForNotifications(1.0):
                # Notification received
                continue
            print("Waiting...")
    except btle.BTLEDisconnectError as e:
        set_pins_state(False)
        print(f"Disconnected: {e}")
        if peripheral:
            peripheral.disconnect()
        print("Retrying in 5 seconds...")
        time.sleep(5)
        receive_data(target_address)
    except KeyboardInterrupt:
        print("Exiting.")
        if peripheral:
            peripheral.disconnect()


if __name__ == "__main__":
    try:
        # start controls of indicator
        indicator_controller = IndicatorControllingThread()
        indicator_controller.start()
        target_address = ""  # Replace with your Arduino's MAC address!
        receive_data(target_address)
    finally:
        GPIO.cleanup()
        indicator_controller.stop()