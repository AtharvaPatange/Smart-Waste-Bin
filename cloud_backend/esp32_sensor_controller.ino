/*
  Sortyx Medical Waste Bin - ESP32 Sensor Controller
  
  Features:
  - Ultrasonic sensors for bin level monitoring (4 bins)
  - Temperature and humidity monitoring
  - WiFi connectivity to cloud backend
  - LED indicators for bin status
  - Real-time data transmission
  
  Hardware Requirements:
  - ESP32 DevKit
  - 4x HC-SR04 Ultrasonic sensors
  - DHT22 temperature/humidity sensor
  - 4x WS2812B RGB LEDs (NeoPixel)
  - Buzzer for alerts
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <Adafruit_NeoPixel.h>
#include <EEPROM.h>

// WiFi Configuration
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Cloud Backend Configuration
const char* serverURL = "https://your-cloud-backend.herokuapp.com"; // Replace with your actual server URL
const char* apiEndpoint = "/sensor/update";

// Hardware Pin Definitions
// Ultrasonic Sensors (Trigger, Echo pairs)
#define TRIG_PIN_1 12  // Yellow bin (General-Biomedical)
#define ECHO_PIN_1 13
#define TRIG_PIN_2 14  // Red bin (Infectious)
#define ECHO_PIN_2 27
#define TRIG_PIN_3 26  // Blue bin (Sharp)
#define ECHO_PIN_3 25
#define TRIG_PIN_4 33  // Black bin (Pharmaceutical)  
#define ECHO_PIN_4 32

// DHT22 Sensor
#define DHT_PIN 4
#define DHT_TYPE DHT22

// LEDs and Buzzer
#define LED_PIN 5
#define LED_COUNT 4
#define BUZZER_PIN 18

// System Configuration
#define BIN_HEIGHT_CM 50  // Height of bins in centimeters
#define MEASUREMENT_INTERVAL 5000  // 5 seconds between measurements
#define UPLOAD_INTERVAL 30000  // 30 seconds between uploads
#define MAX_RETRIES 3

// Bin Configuration
struct Bin {
  String id;
  String name;
  int trigPin;
  int echoPin;
  float level;
  String status;
  uint32_t ledColor;
};

// Initialize sensors and components
DHT dht(DHT_PIN, DHT_TYPE);
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

// Bin definitions
Bin bins[4] = {
  {"yellow_bin", "General-Biomedical", TRIG_PIN_1, ECHO_PIN_1, 0, "normal", strip.Color(255, 255, 0)},
  {"red_bin", "Infectious", TRIG_PIN_2, ECHO_PIN_2, 0, "normal", strip.Color(255, 0, 0)},
  {"blue_bin", "Sharp", TRIG_PIN_3, ECHO_PIN_3, 0, "normal", strip.Color(0, 0, 255)},
  {"black_bin", "Pharmaceutical", TRIG_PIN_4, ECHO_PIN_4, 0, "normal", strip.Color(128, 128, 128)}
};

// System variables
unsigned long lastMeasurement = 0;
unsigned long lastUpload = 0;
float temperature = 0;
float humidity = 0;
bool wifiConnected = false;
int uploadFailures = 0;

void setup() {
  Serial.begin(115200);
  Serial.println("Sortyx Medical Waste Bin - ESP32 Controller Starting...");
  
  // Initialize EEPROM for storing configuration
  EEPROM.begin(512);
  
  // Initialize hardware
  initializeHardware();
  initializeWiFi();
  initializeSensors();
  
  Serial.println("System initialization complete!");
  
  // Initial LED test
  testLEDs();
  playStartupTone();
  
  Serial.println("Ready for operation");
}

void loop() {
  unsigned long currentTime = millis();
  
  // Check WiFi connection
  checkWiFiConnection();
  
  // Measure sensor data at regular intervals
  if (currentTime - lastMeasurement >= MEASUREMENT_INTERVAL) {
    measureAllSensors();
    updateLEDStatus();
    lastMeasurement = currentTime;
  }
  
  // Upload data to cloud at regular intervals
  if (currentTime - lastUpload >= UPLOAD_INTERVAL && wifiConnected) {
    uploadSensorData();
    lastUpload = currentTime;
  }
  
  // Handle alerts and notifications
  handleAlerts();
  
  delay(100); // Small delay to prevent watchdog issues
}

void initializeHardware() {
  Serial.println("Initializing hardware...");
  
  // Initialize ultrasonic sensor pins
  for (int i = 0; i < 4; i++) {
    pinMode(bins[i].trigPin, OUTPUT);
    pinMode(bins[i].echoPin, INPUT);
  }
  
  // Initialize buzzer
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  
  // Initialize NeoPixel strip
  strip.begin();
  strip.clear();
  strip.show();
  
  Serial.println("Hardware initialized successfully");
}

void initializeWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.println();
    Serial.println("WiFi connected successfully!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    Serial.print("Signal strength: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
  } else {
    wifiConnected = false;
    Serial.println();
    Serial.println("WiFi connection failed!");
  }
}

void initializeSensors() {
  Serial.println("Initializing sensors...");
  
  // Initialize DHT22
  dht.begin();
  
  // Test all ultrasonic sensors
  for (int i = 0; i < 4; i++) {
    float distance = measureDistance(bins[i].trigPin, bins[i].echoPin);
    bins[i].level = calculateLevel(distance);
    Serial.printf("Bin %d (%s): %.1f%% full\n", i+1, bins[i].name.c_str(), bins[i].level);
  }
  
  // Read initial temperature and humidity
  temperature = dht.readTemperature();
  humidity = dht.readHumidity();
  
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("Warning: DHT22 sensor not responding properly");
    temperature = 25.0;  // Default values
    humidity = 50.0;
  } else {
    Serial.printf("Environmental conditions: %.1f°C, %.1f%% humidity\n", temperature, humidity);
  }
  
  Serial.println("Sensors initialized successfully");
}

void measureAllSensors() {
  // Read environmental sensors
  float newTemp = dht.readTemperature();
  float newHum = dht.readHumidity();
  
  if (!isnan(newTemp) && !isnan(newHum)) {
    temperature = newTemp;
    humidity = newHum;
  }
  
  // Measure all bin levels
  for (int i = 0; i < 4; i++) {
    float distance = measureDistance(bins[i].trigPin, bins[i].echoPin);
    bins[i].level = calculateLevel(distance);
    
    // Update bin status based on level
    if (bins[i].level >= 90) {
      bins[i].status = "full";
    } else if (bins[i].level >= 75) {
      bins[i].status = "warning";
    } else {
      bins[i].status = "normal";
    }
  }
  
  // Print sensor readings to serial monitor
  Serial.printf("Temp: %.1f°C, Humidity: %.1f%%, Bins: [%.1f%%, %.1f%%, %.1f%%, %.1f%%]\n",
    temperature, humidity, bins[0].level, bins[1].level, bins[2].level, bins[3].level);
}

float measureDistance(int trigPin, int echoPin) {
  // Send ultrasonic pulse
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  // Read echo time
  long duration = pulseIn(echoPin, HIGH, 30000); // 30ms timeout
  
  if (duration == 0) {
    Serial.printf("Warning: Ultrasonic sensor timeout on pins %d/%d\n", trigPin, echoPin);
    return BIN_HEIGHT_CM; // Return maximum distance as fallback
  }
  
  // Calculate distance (speed of sound = 343 m/s)
  float distance = (duration * 0.0343) / 2;
  
  // Validate reading
  if (distance < 2 || distance > BIN_HEIGHT_CM + 10) {
    Serial.printf("Warning: Invalid distance reading %.1fcm on pins %d/%d\n", distance, trigPin, echoPin);
    return BIN_HEIGHT_CM; // Return maximum as fallback
  }
  
  return distance;
}

float calculateLevel(float distance) {
  // Convert distance to fill level percentage
  float level = ((BIN_HEIGHT_CM - distance) / BIN_HEIGHT_CM) * 100.0;
  
  // Constrain between 0-100%
  if (level < 0) level = 0;
  if (level > 100) level = 100;
  
  return level;
}

void updateLEDStatus() {
  for (int i = 0; i < 4; i++) {
    uint32_t color = bins[i].ledColor;
    
    // Modify brightness based on status
    if (bins[i].status == "full") {
      // Blinking red for full bins
      color = (millis() % 1000 < 500) ? strip.Color(255, 0, 0) : strip.Color(0, 0, 0);
    } else if (bins[i].status == "warning") {
      // Orange/amber for warning
      color = strip.Color(255, 165, 0);
    } else {
      // Dim the normal color for normal status
      uint8_t r = (color >> 16) & 0xFF;
      uint8_t g = (color >> 8) & 0xFF;
      uint8_t b = color & 0xFF;
      color = strip.Color(r/4, g/4, b/4); // 25% brightness for normal
    }
    
    strip.setPixelColor(i, color);
  }
  
  strip.show();
}

void uploadSensorData() {
  if (!wifiConnected) {
    Serial.println("Cannot upload: WiFi not connected");
    return;
  }
  
  HTTPClient http;
  http.begin(String(serverURL) + apiEndpoint);
  http.addHeader("Content-Type", "application/json");
  
  // Upload data for each bin
  for (int i = 0; i < 4; i++) {
    StaticJsonDocument<300> doc;
    doc["sensor_id"] = bins[i].id;
    doc["distance"] = BIN_HEIGHT_CM - (bins[i].level * BIN_HEIGHT_CM / 100.0);
    doc["bin_level"] = bins[i].level;
    doc["temperature"] = temperature;
    doc["humidity"] = humidity;
    doc["location"] = "main_facility";
    doc["timestamp"] = String(millis());
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    int httpResponseCode = http.POST(jsonString);
    
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.printf("Bin %s uploaded successfully (HTTP %d)\n", bins[i].name.c_str(), httpResponseCode);
      uploadFailures = 0; // Reset failure counter on success
    } else {
      Serial.printf("Upload failed for bin %s (HTTP %d)\n", bins[i].name.c_str(), httpResponseCode);
      uploadFailures++;
    }
    
    delay(100); // Small delay between uploads
  }
  
  http.end();
  
  // Handle upload failures
  if (uploadFailures >= MAX_RETRIES) {
    Serial.println("Multiple upload failures detected - checking WiFi connection");
    wifiConnected = false;
    uploadFailures = 0;
  }
}

void handleAlerts() {
  bool anyBinFull = false;
  bool anyBinWarning = false;
  
  for (int i = 0; i < 4; i++) {
    if (bins[i].status == "full") {
      anyBinFull = true;
    } else if (bins[i].status == "warning") {
      anyBinWarning = true;
    }
  }
  
  // Sound alerts for full bins
  static unsigned long lastAlert = 0;
  if (anyBinFull && millis() - lastAlert > 10000) { // Alert every 10 seconds
    playAlertTone();
    lastAlert = millis();
    Serial.println("ALERT: One or more bins are full!");
  }
}

void checkWiFiConnection() {
  if (WiFi.status() != WL_CONNECTED && wifiConnected) {
    Serial.println("WiFi connection lost - attempting reconnect");
    wifiConnected = false;
    WiFi.reconnect();
  } else if (WiFi.status() == WL_CONNECTED && !wifiConnected) {
    Serial.println("WiFi reconnected successfully");
    wifiConnected = true;
  }
}

void testLEDs() {
  Serial.println("Testing LEDs...");
  
  // Cycle through each LED with its designated color
  for (int i = 0; i < 4; i++) {
    strip.clear();
    strip.setPixelColor(i, bins[i].ledColor);
    strip.show();
    delay(500);
  }
  
  // All LEDs on briefly
  for (int i = 0; i < 4; i++) {
    strip.setPixelColor(i, bins[i].ledColor);
  }
  strip.show();
  delay(1000);
  
  // Turn off
  strip.clear();
  strip.show();
  
  Serial.println("LED test complete");
}

void playStartupTone() {
  // Play a pleasant startup melody
  int melody[] = {262, 330, 392, 523}; // C4, E4, G4, C5
  for (int i = 0; i < 4; i++) {
    tone(BUZZER_PIN, melody[i], 200);
    delay(250);
  }
  noTone(BUZZER_PIN);
}

void playAlertTone() {
  // Play alert sound for full bins
  for (int i = 0; i < 3; i++) {
    tone(BUZZER_PIN, 1000, 200);
    delay(200);
    noTone(BUZZER_PIN);
    delay(100);
  }
}

// Function to handle over-the-air updates (optional)
void handleOTA() {
  // Implementation for OTA updates would go here
  // This allows remote firmware updates without physical access
}

// Function to save configuration to EEPROM
void saveConfig() {
  // Save WiFi credentials and server settings to EEPROM
  // Implementation would depend on specific requirements
}

// Function to load configuration from EEPROM  
void loadConfig() {
  // Load saved configuration from EEPROM
  // Implementation would depend on specific requirements
}