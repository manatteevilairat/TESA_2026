/**
 * esp32_firmware/src/main.cpp
 * TESA Top Gun Rally 2026 - ESP32 Sensing Node Firmware
 * คุณสมบัติ:
 * - อ่านค่าเซ็นเซอร์กายภาพ (ADC / Temperature / Humidity)
 * - ตัวกรองค่า Moving Average ป้องกันสัญญาณแกว่ง
 * - Non-blocking Wi-Fi และ MQTT Reconnection
 * - ส่งข้อมูล JSON Payload ผ่าน MQTT
 */

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// --- ตั้งค่า Wi-Fi และ MQTT ---
const char* WIFI_SSID = "TGR2026_TEAM_WIFI";
const char* WIFI_PASSWORD = "Password1234";
const char* MQTT_BROKER = "192.168.1.100";
const int   MQTT_PORT = 1883;
const char* BATCH_ID = "CPN-2026-B001";
const char* DEVICE_ID = "esp32_sensing_01";

// Pin Configuration
const int MOISTURE_PIN = 34; // Analog Input Pin สำหรับเซ็นเซอร์ความชื้น
const int STATUS_LED = 2;

WiFiClient espClient;
PubSubClient mqttClient(espClient);

unsigned long lastPublishTime = 0;
const unsigned long PUBLISH_INTERVAL = 3000; // ส่งข้อมูลทุก 3 วินาที

// ฟังก์ชันกรองสัญญาณ Moving Average
float readFilteredMoisture() {
    long sum = 0;
    const int SAMPLES = 10;
    for (int i = 0; i < SAMPLES; i++) {
        sum += analogRead(MOISTURE_PIN);
        delay(10);
    }
    float rawAverage = sum / (float)SAMPLES;
    // ตัวอย่างการ Mapping สัญญาณดิบ ADC (0-4095) เป็นเปอร์เซ็นต์ความชื้น (10% - 14%)
    float moisturePct = 10.0 + (rawAverage / 4095.0) * 4.0;
    return moisturePct;
}

void setupWifi() {
    delay(100);
    Serial.println();
    Serial.print("Connecting to Wi-Fi: ");
    Serial.println(WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi connected! IP address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\nWiFi connection failed! Will retry in main loop.");
    }
}

void reconnectMqtt() {
    if (!mqttClient.connected()) {
        Serial.print("Attempting MQTT connection...");
        if (mqttClient.connect(DEVICE_ID)) {
            Serial.println(" connected!");
            digitalWrite(STATUS_LED, HIGH);
        } else {
            Serial.print(" failed, rc=");
            Serial.print(mqttClient.state());
            Serial.println(" will try again in next loop");
            digitalWrite(STATUS_LED, LOW);
        }
    }
}

void publishSensorData() {
    float moisture = readFilteredMoisture();
    float temp = 29.5;      // ค่าตัวอย่าง (สามารถต่อเซ็นเซอร์ SHT31/DHT22 เพิ่มได้)
    float humidity = 64.0;

    JsonDocument doc;
    doc["device_id"] = DEVICE_ID;
    doc["batch_id"] = BATCH_ID;
    doc["timestamp"] = millis() / 1000;
    doc["moisture_pct"] = round(moisture * 10.0) / 10.0;
    doc["ambient_temp_c"] = temp;
    doc["ambient_humidity_pct"] = humidity;
    
    if (moisture > 12.5) {
        doc["status"] = "MOISTURE_HIGH";
    } else if (moisture < 11.0) {
        doc["status"] = "DRYING_COMPLETE";
    } else {
        doc["status"] = "DRYING_NORMAL";
    }

    char jsonBuffer[256];
    serializeJson(doc, jsonBuffer);

    char topic[64];
    snprintf(topic, sizeof(topic), "tgr2026/coffee/%s/sensing", BATCH_ID);

    if (mqttClient.publish(topic, jsonBuffer)) {
        Serial.print("Published to ");
        Serial.print(topic);
        Serial.print(": ");
        Serial.println(jsonBuffer);
    } else {
        Serial.println("Failed to publish message!");
    }
}

void setup() {
    Serial.begin(115200);
    pinMode(STATUS_LED, OUTPUT);
    analogReadResolution(12); // ESP32 ADC 12-bit (0-4095)

    setupWifi();
    mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
}

void loop() {
    if (WiFi.status() == WL_CONNECTED) {
        if (!mqttClient.connected()) {
            reconnectMqtt();
        }
        mqttClient.loop();
    }

    unsigned long now = millis();
    if (now - lastPublishTime >= PUBLISH_INTERVAL) {
        lastPublishTime = now;
        if (mqttClient.connected()) {
            publishSensorData();
        }
    }
}
