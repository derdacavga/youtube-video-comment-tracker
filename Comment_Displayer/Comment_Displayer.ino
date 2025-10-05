#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>
#include <MD_MAX72xx.h>
#include <MD_Parola.h>
#include <SPI.h>

const char* ssid = "YOUR-WIFI-ID";
const char* password = "YOUR-WIFI-PASSWORD";

const char* server = "http://YOUR-PC-IP-ADRESS:8000/comments";

#define HARDWARE_TYPE MD_MAX72XX::FC16_HW
#define MAX_DEVICES 4
#define CLK_PIN D5
#define DATA_PIN D7
#define CS_PIN D8

MD_Parola parola = MD_Parola(HARDWARE_TYPE, CS_PIN, MAX_DEVICES);

uint8_t displayBrightness = 13;  // 0-15
uint16_t scrollSpeed = 15;      // ms
uint16_t pauseTime = 0;         // ms
textEffect_t scrollEffect = PA_SCROLL_LEFT;
unsigned long checkInterval = 3000;  // check new comment

#define MAX_QUEUE_SIZE 40
String messageQueue[MAX_QUEUE_SIZE];
int queueHead = 0;
int queueTail = 0;

void enqueueMessage(const String& msg) {
  int next = (queueTail + 1) % MAX_QUEUE_SIZE;
  if (next != queueHead) {
    messageQueue[queueTail] = msg;
    queueTail = next;
  } else {
    queueHead = (queueHead + 1) % MAX_QUEUE_SIZE;
    messageQueue[queueTail] = msg;
    queueTail = (queueTail + 1) % MAX_QUEUE_SIZE;
  }
}
bool dequeueMessage(String& out) {
  if (queueHead == queueTail) return false;  
  out = messageQueue[queueHead];
  queueHead = (queueHead + 1) % MAX_QUEUE_SIZE;
  return true;
}

unsigned long lastCheck = 0;

void setup() {
  Serial.begin(115200);
  delay(10);
  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wifi");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
    if (millis() - start > 15000) break;  // 15s timeout 
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi Connected: " + WiFi.localIP().toString());
  } else {
    Serial.println("Not Connected to Wifi.");
  }

  parola.begin();
  parola.setIntensity(displayBrightness);
  parola.setSpeed(scrollSpeed);
  parola.setPause(pauseTime);
  parola.displayClear();
  parola.displayText("YT Chat Ready", PA_CENTER, scrollSpeed, 2000, scrollEffect, scrollEffect);
}

void loop() {
  static String currentMessage = "";
  static bool messageShowing = false;

  if (millis() - lastCheck >= checkInterval) {
    lastCheck = millis();
    if (WiFi.status() == WL_CONNECTED) {
      WiFiClient client;
      HTTPClient http;
      http.begin(client, server);
      int httpCode = http.GET();
      if (httpCode == 200) {
        String payload = http.getString();
        DynamicJsonDocument doc(8192);
        DeserializationError err = deserializeJson(doc, payload);
        if (!err) {
          for (JsonVariant v : doc.as<JsonArray>()) {
            enqueueMessage(v.as<const char*>());
          }
        }
      }
      http.end();
    }
  }

  if (!messageShowing) {
    if (dequeueMessage(currentMessage)) { 
      parola.displayText(currentMessage.c_str(), PA_LEFT, scrollSpeed, pauseTime, PA_SCROLL_LEFT, PA_SCROLL_LEFT);
      messageShowing = true;
      Serial.println("Showing: " + currentMessage);
    }
  }

  if (messageShowing && parola.displayAnimate()) {
    messageShowing = false;
    currentMessage = "";
  }
  delay(50);
}
