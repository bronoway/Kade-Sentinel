#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>

const String BASE_URL = "https://encounter-starts-bits-selection.trycloudflare.com";
constexpr int TRAY_ID = 1;

constexpr int PIR_PIN = 27, BUZZER_PIN = 26, RED_LED = 25, GREEN_LED = 33;
constexpr uint32_t INDICATOR_MS = 3000;   // how long an LED stays lit
constexpr uint32_t ALARM_MS = 1000;       // buzzer duration
constexpr uint32_t ALARM_HZ = 2500;
constexpr uint32_t HTTP_TIMEOUT_MS = 5000;
constexpr uint32_t RETRY_MS = 10000;

bool prevMotion = false;
bool alertPending = false;
uint32_t indicatorOff = 0, alarmOff = 0, lastRetry = 0;

#if ESP_ARDUINO_VERSION_MAJOR >= 3
  void buzzerInit()          { ledcAttach(BUZZER_PIN, ALARM_HZ, 8); }
  void buzzerTone(uint32_t f) { ledcWriteTone(BUZZER_PIN, f); }
#else
  void buzzerInit()          { ledcSetup(0, ALARM_HZ, 8); ledcAttachPin(BUZZER_PIN, 0); }
  void buzzerTone(uint32_t f) { ledcWriteTone(0, f); }
#endif

void indicate(bool authorised) {
  digitalWrite(GREEN_LED, authorised);
  digitalWrite(RED_LED, !authorised);
  indicatorOff = millis() + INDICATOR_MS;
  if (!authorised) {
    buzzerTone(ALARM_HZ);
    alarmOff = millis() + ALARM_MS;
  }
}

int post(const String &path, String &body) {
  const String url = BASE_URL + path;
  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  WiFiClientSecure tls;
  WiFiClient plain;
  bool ok;
  if (url.startsWith("https")) {
    tls.setInsecure();  // DEMO ONLY: no certificate check. Pin a CA certificate for a real deployment.
    ok = http.begin(tls, url);
  } else {
    ok = http.begin(plain, url);
  }
  if (!ok) return -1;
  int code = http.POST("");
  body = code > 0 ? http.getString() : "";
  http.end();
  return code;
}

void handleMotion() {
  Serial.println("Motion detected. Asking backend...");
  String body;
  int code = WiFi.status() == WL_CONNECTED ? post("/api/trays/" + String(TRAY_ID) + "/motion", body) : -1;
  Serial.printf("HTTP status: %d\n", code);

  if (code == 200) {
    bool granted = body.indexOf("\"granted\":true") >= 0;
    indicate(granted);
    Serial.println(granted ? "AUTHORISED: green LED." : "UNAUTHORISED: red LED + buzzer. Alert logged by backend.");
    return;
  }
  Serial.println("UNKNOWN (backend unreachable): raising local alarm, will retry alert.");
  indicate(false);
  alertPending = true;
  lastRetry = millis();
}

void retryPendingAlert() {
  if (!alertPending || millis() - lastRetry < RETRY_MS) return;
  lastRetry = millis();
  if (WiFi.status() != WL_CONNECTED) { WiFi.reconnect(); return; }
  String body;
  int code = post("/api/trays/" + String(TRAY_ID) + "/alert", body);
  Serial.printf("Alert retry status: %d\n", code);
  if (code == 200) alertPending = false;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIR_PIN, INPUT);
  pinMode(RED_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  buzzerInit();

  WiFi.setAutoReconnect(true);
  WiFi.begin("Wokwi-GUEST", "", 6);  // Wokwi's open network; replace with real SSID/password on hardware
  Serial.print("Connecting to WiFi");
  for (uint32_t t0 = millis(); WiFi.status() != WL_CONNECTED && millis() - t0 < 20000; delay(250)) Serial.print(".");
  Serial.println(WiFi.status() == WL_CONNECTED ? "\nWiFi connected. Ready for motion." : "\nWiFi not connected yet; will keep retrying.");
}

void loop() {
  uint32_t now = millis();
  if (alarmOff && (int32_t)(now - alarmOff) >= 0) { buzzerTone(0); alarmOff = 0; }
  if (indicatorOff && (int32_t)(now - indicatorOff) >= 0) {
    digitalWrite(RED_LED, LOW);
    digitalWrite(GREEN_LED, LOW);
    indicatorOff = 0;
  }

  bool motion = digitalRead(PIR_PIN) == HIGH;
  if (motion && !prevMotion) handleMotion();  // one check per rising edge, not per pulse
  prevMotion = motion;

  retryPendingAlert();
  delay(50);
}
