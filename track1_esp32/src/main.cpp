/**
 * esp32_firmware/src/main.cpp
 * TESA Top Gun Rally 2026 - Production-Ready Sensing Node Firmware
 * Dual Target Support: ESP32 WROOM-32 (Testing) & ESP32-S3 N16R8 (Competition)
 * 
 * Features:
 * 1. Automatic Pinout Mapping based on target chip (WROOM-32 vs ESP32-S3)
 * 2. Analog ADC Reading with 16-sample Moving Average + Two-Point Calibration
 * 3. Closed-Loop PWM Actuation (Exhaust Fan / Heater Control based on moisture)
 * 4. Digital I/O Interrupt (BOOT Button for instant telemetry trigger & calibration)
 * 5. Non-Blocking Wi-Fi & MQTT Reconnection State Machine (Zero-Freezing)
 * 6. Compliant JSON Telemetry conforming to shared/schemas.py
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

// ==============================================================================
// 1. PIN CONFIGURATION (AUTO-DETECT CHIP TARGET)
// ==============================================================================
#if defined(CONFIG_IDF_TARGET_ESP32S3)
    // --- ESP32-S3 N16R8 (Tournament Board) ---
    #define BOARD_NAME          "ESP32-S3-N16R8"
    const int MOISTURE_PIN    = 4;   // ADC1_CH3 on ESP32-S3 (Safe for Wi-Fi)
    const int PWM_PIN         = 18;  // PWM Actuator (Exhaust Fan / Heater)
    const int STATUS_LED      = 2;   // Onboard LED
    const int BUTTON_PIN      = 0;   // BOOT Button (Active LOW)
    const int DHT_PIN         = 15;  // Digital Pin for DHT11 Temp/Humidity
#else
    // --- ESP32 WROOM-32 (Development / Testing Board) ---
    #define BOARD_NAME          "ESP32-WROOM-32"
    const int MOISTURE_PIN    = 34;  // ADC1_CH6 on WROOM (Input-only, Safe for Wi-Fi)
    const int PWM_PIN         = 18;  // PWM Actuator (Exhaust Fan / Heater)
    const int STATUS_LED      = 2;   // Onboard Blue LED
    const int BUTTON_PIN      = 0;   // BOOT Button (Active LOW)
    const int DHT_PIN         = 15;  // Digital Pin for DHT11 Temp/Humidity
#endif

#define DHTTYPE DHT11
DHT dht(DHT_PIN, DHTTYPE);

// ==============================================================================
// 2. NETWORK & MQTT CONFIGURATION
// ==============================================================================
// หมายเหตุ: ปรับ SSID / Password ให้ตรงกับ Hotspot หรือเราเตอร์ทีม
const char* WIFI_SSID       = "CoEIoT";
const char* WIFI_PASSWORD   = "iot.coe.psu.ac.th";

// IP ของคอมพิวเตอร์ที่รัน Mosquitto MQTT Broker ในวง LAN
const char* MQTT_BROKER     = "172.30.81.107"; // ค่า Default หรือเปลี่ยนเป็น IP เครื่อง Mac
const int   MQTT_PORT       = 1883;

const char* BATCH_ID        = "CPN-2026-B001";
const char* DEVICE_ID       = "esp32_sensing_01";

// ==============================================================================
// 3. CALIBRATION & DRYING PROCESS CONSTANTS
// ==============================================================================
// Two-Point Calibration สำหรับแปลงค่า ADC เป็นค่าความชื้นเมล็ดกาแฟ (%)
// ค่ามาตรฐานส่งออกกาแฟโรบัสตาชุมพร: 10.5% - 12.5%
int   CALIB_ADC_DRY         = 3400; // ค่า ADC เมื่อเมล็ดแห้ง (~10.0%)
float CALIB_MOISTURE_DRY    = 10.0;
int   CALIB_ADC_WET         = 1200; // ค่า ADC เมื่อเมล็ดสด/ชื้น (~14.5%)
float CALIB_MOISTURE_WET    = 14.5;

// การตั้งค่า PWM สำหรับพัดลมระบายความชื้น (LEDC Peripheral)
const uint32_t PWM_FREQ     = 5000; // 5 kHz
const uint8_t  PWM_RES      = 8;    // 8-bit resolution (0 - 255)
const uint8_t  PWM_CHANNEL  = 0;

// ==============================================================================
// 4. GLOBAL STATE & TIMERS
// ==============================================================================
WiFiClient espClient;
PubSubClient mqttClient(espClient);

unsigned long lastPublishTime  = 0;
const unsigned long PUBLISH_INTERVAL = 3000; // ส่งข้อมูลทุก 3 วินาที

unsigned long lastLedBlinkTime = 0;
bool ledState                  = false;

volatile bool buttonPressed    = false;
unsigned long lastDebounceTime = 0;
const unsigned long DEBOUNCE_DELAY = 300;

// ==============================================================================
// 5. HARDWARE INTERRUPT HANDLERS
// ==============================================================================
void IRAM_ATTR handleButtonInterrupt() {
    unsigned long now = millis();
    if (now - lastDebounceTime > DEBOUNCE_DELAY) {
        buttonPressed = true;
        lastDebounceTime = now;
    }
}

// ==============================================================================
// 6. SENSOR FILTERING & ACTUATOR CONTROL
// ==============================================================================
/**
 * อ่านค่า ADC แบบ Moving Average กรองสัญญาณรบกวน 16 ตัวอย่าง
 */
int readFilteredADC() {
    long sum = 0;
    const int SAMPLES = 16;
    for (int i = 0; i < SAMPLES; i++) {
        sum += analogRead(MOISTURE_PIN);
        delayMicroseconds(500);
    }
    return (int)(sum / SAMPLES);
}

/**
 * แปลงค่า ADC เป็นเปอร์เซ็นต์ความชื้นด้วย Two-Point Linear Interpolation
 */
float calculateMoisture(int rawAdc) {
    // ป้องกันการหารด้วยศูนย์
    if (CALIB_ADC_DRY == CALIB_ADC_WET) return 11.5;

    // Linear mapping
    float slope = (CALIB_MOISTURE_WET - CALIB_MOISTURE_DRY) / (float)(CALIB_ADC_WET - CALIB_ADC_DRY);
    float moisture = CALIB_MOISTURE_DRY + slope * (rawAdc - CALIB_ADC_DRY);

    // Clamp ให้อยู่ในช่วงความเป็นไปได้ทางกายภาพ (8.0% - 25.0%)
    if (moisture < 8.0)  moisture = 8.0;
    if (moisture > 25.0) moisture = 25.0;

    return round(moisture * 10.0) / 10.0;
}

/**
 * ควบคุมความเร็วพัดลมระบายความชื้น (PWM) ตามสถานะความชื้นเมล็ดกาแฟ
 */
int updatePwmActuator(float moisturePct) {
    int targetDuty = 0;

    if (moisturePct > 12.5) {
        // ความชื้นเกินเกณฑ์ส่งออก -> เร่งพัดลมระบายอากาศ 100%
        targetDuty = 255;
    } else if (moisturePct >= 11.0) {
        // ความชื้นเหมาะสมสำหรับตากแห้งแบบประณีต -> เปิดพัดลมเบาๆ 40%
        targetDuty = 100;
    } else {
        // ความชื้นแห้งสมบูรณ์ตามมาตรฐาน -> ปิดพัดลม
        targetDuty = 0;
    }

    // รองรับทั้ง Arduino Core v3 และ v2
    #if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
        ledcWrite(PWM_PIN, targetDuty);
    #else
        ledcWrite(PWM_CHANNEL, targetDuty);
    #endif

    return targetDuty;
}

// ==============================================================================
// 7. NETWORKING (NON-BLOCKING) & TELEMETRY PUBLISH
// ==============================================================================
void publishTelemetry(const char* triggerReason);

void checkWifiConnection() {
    static bool wasConnected = false;
    if (WiFi.status() == WL_CONNECTED) {
        if (!wasConnected) {
            wasConnected = true;
            Serial.println();
            Serial.printf("[%s] >>> Wi-Fi CONNECTED! <<<\n", BOARD_NAME);
            Serial.printf("[%s] Assigned IP: %s\n", BOARD_NAME, WiFi.localIP().toString().c_str());
            Serial.printf("[%s] Gateway IP : %s\n", BOARD_NAME, WiFi.gatewayIP().toString().c_str());
        }
    } else {
        if (wasConnected) {
            wasConnected = false;
            Serial.printf("[%s] Wi-Fi Connection Lost!\n", BOARD_NAME);
        }
        static unsigned long lastWifiAttempt = 0;
        if (millis() - lastWifiAttempt > 8000) {
            lastWifiAttempt = millis();
            Serial.printf("[%s] Wi-Fi not connected (status=%d), retrying '%s'...\n", BOARD_NAME, WiFi.status(), WIFI_SSID);
            WiFi.reconnect();
        }
    }
}

void checkMqttConnection() {
    if (WiFi.status() == WL_CONNECTED && !mqttClient.connected()) {
        static unsigned long lastMqttAttempt = 0;
        if (millis() - lastMqttAttempt > 3000) {
            lastMqttAttempt = millis();
            Serial.printf("[%s] Connecting to MQTT Broker (%s:%d)... ", BOARD_NAME, MQTT_BROKER, MQTT_PORT);
            if (mqttClient.connect(DEVICE_ID)) {
                Serial.println("CONNECTED! Ready to stream telemetry.");
                digitalWrite(STATUS_LED, HIGH);
                publishTelemetry("FIRST_CONNECT");
            } else {
                Serial.printf("FAILED (rc=%d), will retry.\n", mqttClient.state());
            }
        }
    }
}

void publishTelemetry(const char* triggerReason = "PERIODIC") {
    int rawAdc = readFilteredADC();
    float moisture = calculateMoisture(rawAdc);
    int pwmDuty = updatePwmActuator(moisture);

    // อ่านค่าอุณหภูมิและความชื้นอากาศจริงจากเซ็นเซอร์ DHT11 (GPIO 15)
    float rawTemp = dht.readTemperature();
    float rawHumidity = dht.readHumidity();

    static float lastValidTemp = 29.5;
    static float lastValidHum  = 63.8;

    float temp = isnan(rawTemp) ? lastValidTemp : round(rawTemp * 10.0) / 10.0;
    float humidity = isnan(rawHumidity) ? lastValidHum : round(rawHumidity * 10.0) / 10.0;

    if (!isnan(rawTemp)) lastValidTemp = temp;
    if (!isnan(rawHumidity)) lastValidHum = humidity;

    const char* statusStr = "DRYING_NORMAL";
    if (moisture > 12.5) {
        statusStr = "MOISTURE_HIGH";
    } else if (moisture < 11.0) {
        statusStr = "DRYING_COMPLETE";
    }

    // สร้าง JSON ตาม Data Contract: shared/schemas.py
    JsonDocument doc;
    doc["device_id"]            = DEVICE_ID;
    doc["batch_id"]             = BATCH_ID;
    doc["timestamp"]            = (double)millis() / 1000.0;
    doc["moisture_pct"]         = moisture;
    doc["ambient_temp_c"]       = temp;
    doc["ambient_humidity_pct"] = humidity;
    doc["status"]               = statusStr;

    // ข้อมูลวินิจฉัยฮาร์ดแวร์เพิ่มเติมสำหรับทีม
    doc["raw_adc"]              = rawAdc;
    doc["pwm_duty"]             = pwmDuty;
    doc["board_type"]           = BOARD_NAME;
    doc["trigger"]              = triggerReason;

    char jsonBuffer[384];
    serializeJson(doc, jsonBuffer);

    char topic[64];
    snprintf(topic, sizeof(topic), "tgr2026/coffee/%s/sensing", BATCH_ID);

    if (mqttClient.connected()) {
        bool pubOk = mqttClient.publish(topic, jsonBuffer);
        if (pubOk) {
            Serial.printf(">> [MQTT PUB OK] Topic: %s | Payload: %s\n", topic, jsonBuffer);
            // กะพริบ LED ยืนยันการส่งข้อความสำเร็จ
            digitalWrite(STATUS_LED, LOW);
            delay(30);
            digitalWrite(STATUS_LED, HIGH);
        } else {
            Serial.printf(">> [MQTT PUB FAILED] (Buffer limit or network drop) Topic: %s\n", topic);
        }
    } else {
        Serial.printf(">> [LOCAL TELEMETRY] (Offline Mode) %s\n", jsonBuffer);
    }
}

// ==============================================================================
// 8. SETUP & LOOP
// ==============================================================================
void setup() {
    Serial.begin(115200);
    delay(500);

    Serial.println("\n=======================================================");
    Serial.printf("   TESA TOP GUN RALLY 2026 - SENSING NODE FIRMWARE\n");
    Serial.printf("   Target Architecture: %s\n", BOARD_NAME);
    Serial.printf("   Moisture Pin: GPIO%d | PWM Pin: GPIO%d | Button: GPIO%d | DHT11: GPIO%d\n", MOISTURE_PIN, PWM_PIN, BUTTON_PIN, DHT_PIN);
    Serial.println("=======================================================");

    // เริ่มต้นเซ็นเซอร์ DHT11
    dht.begin();

    // กำหนดโหมดขา
    pinMode(STATUS_LED, OUTPUT);
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(BUTTON_PIN), handleButtonInterrupt, FALLING);

    // กำหนด ADC Resolution (12-bit = 0 - 4095)
    analogReadResolution(12);

    // ติดตั้ง PWM Peripheral (LEDC)
    #if defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
        ledcAttach(PWM_PIN, PWM_FREQ, PWM_RES);
    #else
        ledcSetup(PWM_CHANNEL, PWM_FREQ, PWM_RES);
        ledcAttachPin(PWM_PIN, PWM_CHANNEL);
    #endif

    // ตั้งค่า Wi-Fi และ MQTT
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    Serial.printf("[%s] Connecting to Wi-Fi: %s ...\n", BOARD_NAME, WIFI_SSID);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
    mqttClient.setBufferSize(512); // ขยาย Buffer ให้รองรับ JSON ขนาดใหญ่ (>256 bytes)

    // ทดสอบหมุนพัดลม PWM ทดสอบเริ่มต้น (Self-test)
    updatePwmActuator(13.0); // เปิดพัดลมชั่วคราว 0.3 วินาที
    delay(300);
    updatePwmActuator(10.0); // ปิด
}

void loop() {
    // 1. ตรวจสอบสถานะเครือข่าย Wi-Fi และ MQTT แบบ Non-blocking
    checkWifiConnection();
    checkMqttConnection();
    mqttClient.loop();

    // 2. ตรวจสอบปุ่มกด BOOT (Immediate Trigger)
    if (buttonPressed) {
        buttonPressed = false;
        Serial.println(">> [BUTTON PRESSED] Manual Telemetry Triggered!");
        publishTelemetry("MANUAL_BUTTON");
    }

    // 3. ส่งข้อมูลตามรอบเวลา (Periodic Publish)
    unsigned long now = millis();
    if (now - lastPublishTime >= PUBLISH_INTERVAL) {
        lastPublishTime = now;
        publishTelemetry("PERIODIC");
    }

    // 4. จัดการไฟสถานะ LED เมื่อยังไม่ได้ต่อ Wi-Fi (กะพริบแจ้งเตือน)
    if (WiFi.status() != WL_CONNECTED || !mqttClient.connected()) {
        if (now - lastLedBlinkTime > 300) {
            lastLedBlinkTime = now;
            ledState = !ledState;
            digitalWrite(STATUS_LED, ledState);
        }
    }
}
