#include <HCSR04.h>
#include <ArduinoBLE.h>
#include <string>

// change to the appropriate pins
byte triggerPin = 3;
byte echoPin = 2;

// Define the custom service and characteristic UUIDs
#define SERVICE_UUID           "180D"
#define CHARACTERISTIC_UUID    "2A37"

// Create the BLE service and characteristic
BLEService customService(SERVICE_UUID);
BLEStringCharacteristic customCharacteristic(CHARACTERISTIC_UUID, BLERead | BLENotify, 20);

void setup() {
  Serial.begin(9600);
  while (!Serial);

  // initialise HCSR sensor
  HCSR04.begin(triggerPin, echoPin);
  // Initialize BLE
  if (!BLE.begin()) {
    Serial.println("starting Bluetooth® Low Energy module failed!");
    while (1);
  }

  // Set the local name and advertise the service
  BLE.setLocalName("Nano33IoT");
  BLE.setAdvertisedService(customService);

  // Add the characteristic to the service
  customService.addCharacteristic(customCharacteristic);
  BLE.addService(customService);

  // Start advertising
  BLE.advertise();
  Serial.println("Bluetooth® device active, waiting for connections...");
}

void loop() {
  // Wait for a BLE central to connect
  BLEDevice central = BLE.central();

  // If a central is connected
  if (central) {
    Serial.print("Connected to central: ");
    Serial.println(central.address());

    while (central.connected()) {
      // Create the data to send
      double* distances = HCSR04.measureDistanceCm();
      String dataToSend (distances[0]);
      Serial.print("Sending: ");
      Serial.println(dataToSend);
      
      // Write the value to the characteristic
      customCharacteristic.writeValue(dataToSend);
      delay(1000); // Delay between notifications
    }

    Serial.print("Disconnected from central: ");
    Serial.println(central.address());
  }
}
