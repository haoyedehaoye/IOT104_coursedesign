#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <Adafruit_AHTX0.h>
#include <Adafruit_GFX.h>
#include <Adafruit_LEDBackpack.h>

// ================= LED =================
#define YELLOW_LED_PIN 12
#define RED_LED_PIN    13
#define GREEN_LED_PIN  14

#define USER_BUTTON 34
#define USER_LIGHT 23

// ================= Temperature ADC Pins =================
#define BACK_TEMP_PIN      35
#define CORE_TEMP_PIN      32
#define HAND_LED_TEMP_PIN  33

// ================= I2C Pins =================
#define I2C_SDA_PIN 21
#define I2C_SCL_PIN 22

// ================= I2C Address =================
#define AHT20_ADDR   0x38
#define MATRIX_ADDR  0x70

// ================= WiFi =================
const char* WIFI_SSID = "oneplus";
const char* WIFI_PASS = "7355608a";

// ================= MQTT =================
const char* MQTT_SERVER = "20.205.107.61";
const int   MQTT_PORT   = 1883;

const char* TOPIC_DATA  = "sleep/device/data";
const char* TOPIC_EVENT = "sleep/device/event";
const char* TOPIC_AGE   = "sleep/frontend/age";
const char* TOPIC_QUILT = "sleep/frontend/quilt";

const char* TOPIC_LED_CONTROL  = "sleep/device/led";
const char* TOPIC_CORE_DISPLAY = "sleep/device/core_display";

// ================= Display Mode =================
// false = 显示 MQTT 下发的 matrixCoreValue
// true  = 显示本地 CORE_TEMP_PIN 读取的 coreTemp
#define DISPLAY_LOCAL_CORE_TEMP false

// 点阵屏默认显示值
int matrixCoreValue = 24;

WiFiClient espClient;
PubSubClient mqtt(espClient);

Adafruit_AHTX0 aht;
Adafruit_8x8matrix matrix = Adafruit_8x8matrix();


// ================= 3x5 Digit Font =================
// 每个数字宽 3，高 5，适合 8x8 显示两位数
byte digitFont[10][5] = {
  {B111, B101, B101, B101, B111}, // 0
  {B010, B110, B010, B010, B111}, // 1
  {B111, B001, B111, B100, B111}, // 2
  {B111, B001, B111, B001, B111}, // 3
  {B101, B101, B111, B001, B001}, // 4
  {B111, B100, B111, B001, B111}, // 5
  {B111, B100, B111, B101, B111}, // 6
  {B111, B001, B001, B001, B001}, // 7
  {B111, B101, B111, B101, B111}, // 8
  {B111, B101, B111, B001, B111}  // 9
};


// ================= 8x8 Matrix Direction Fix =================
// 你的屏幕现在是左右镜像，所以 X 镜像打开
// 如果之后发现上下也反，再把 MATRIX_MIRROR_Y 改成 true
#define MATRIX_MIRROR_X true
#define MATRIX_MIRROR_Y false

void drawFixedPixel(int x, int y, bool on) {
  if (x < 0 || x > 7 || y < 0 || y > 7) return;

  int realX = x;
  int realY = y;

  if (MATRIX_MIRROR_X) realX = 7 - realX;
  if (MATRIX_MIRROR_Y) realY = 7 - realY;

  matrix.drawPixel(realX, realY, on ? LED_ON : LED_OFF);
}


void drawSmallDigit(int digit, int xOffset, int yOffset) {
  if (digit < 0 || digit > 9) return;

  for (int row = 0; row < 5; row++) {
    for (int col = 0; col < 3; col++) {
      bool pixelOn = digitFont[digit][row] & (1 << (2 - col));
      drawFixedPixel(xOffset + col, yOffset + row, pixelOn);
    }
  }
}


void displayNumberOnMatrix(int number) {
  if (number < 0) number = 0;
  if (number > 99) number = 99;

  int tens = number / 10;
  int ones = number % 10;

  matrix.clear();

  // 8x8 上显示两位数：
  // 左边数字占 x=0~2
  // 中间 x=3 空一列
  // 右边数字占 x=4~6
  drawSmallDigit(tens, 0, 1);
  drawSmallDigit(ones, 4, 1);

  matrix.writeDisplay();
}


// ================= Button Start =================
void waitForButtonStart() {
  Serial.println("Waiting for button press...");
  Serial.println("Press USER_BUTTON LOW to start system.");

  while (digitalRead(USER_BUTTON) != LOW) {
    delay(50);
  }

  delay(50);

  if (digitalRead(USER_BUTTON) == LOW) {
    Serial.println("Button pressed. System starting...");
    digitalWrite(USER_LIGHT, LOW);
  }

  while (digitalRead(USER_BUTTON) == LOW) {
    delay(10);
  }
}


// ================= LED Control =================
void turnOffAllLED() {
  digitalWrite(YELLOW_LED_PIN, LOW);
  digitalWrite(RED_LED_PIN, LOW);
  digitalWrite(GREEN_LED_PIN, LOW);
}


void yellowOn() {
  turnOffAllLED();
  digitalWrite(YELLOW_LED_PIN, HIGH);
}


void redOn() {
  turnOffAllLED();
  digitalWrite(RED_LED_PIN, HIGH);
}


void greenOn() {
  turnOffAllLED();
  digitalWrite(GREEN_LED_PIN, HIGH);
}


void setLedByStatus(String status) {
  status.trim();

  if (status == "cold") {
    greenOn();
    Serial.println("LED status: cold -> green");
  }
  else if (status == "hot") {
    redOn();
    Serial.println("LED status: hot -> red");
  }
  else if (status == "ok") {
    yellowOn();
    Serial.println("LED status: ok -> yellow");
  }
  else if (status == "off") {
    turnOffAllLED();
    Serial.println("LED status: off -> all off");
  }
  else {
    turnOffAllLED();
    Serial.println("LED status: unknown -> all off");
  }
}


// ================= MQTT Callback =================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.print("MQTT message received, topic: ");
  Serial.println(topic);

  String msg = "";

  Serial.print("Payload: ");
  for (unsigned int i = 0; i < length; i++) {
    Serial.print((char)payload[i]);
    msg += (char)payload[i];
  }
  Serial.println();

  msg.trim();

  String topicStr = String(topic);

  if (topicStr == TOPIC_LED_CONTROL) {
    setLedByStatus(msg);
  }

  if (topicStr == TOPIC_CORE_DISPLAY) {
    int value = msg.toInt();

    if (value < 0) value = 0;
    if (value > 99) value = 99;

    matrixCoreValue = value;

    Serial.print("Matrix display value set to: ");
    Serial.println(matrixCoreValue);

    if (!DISPLAY_LOCAL_CORE_TEMP) {
      displayNumberOnMatrix(matrixCoreValue);
    }
  }
}


// ================= WiFi Init =================
void wifiInit() {
  Serial.println();
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}


// ================= MQTT Init =================
void mqttInit() {
  mqtt.setServer(MQTT_SERVER, MQTT_PORT);
  mqtt.setCallback(mqttCallback);

  Serial.println("MQTT initialized");
}


// ================= MQTT Reconnect =================
void mqttReconnect() {
  while (!mqtt.connected()) {
    Serial.print("Connecting to MQTT...");

    String clientId = "ESP32_sleep_device_";
    clientId += String((uint32_t)ESP.getEfuseMac(), HEX);

    if (mqtt.connect(clientId.c_str())) {
      Serial.println("connected");

      mqtt.subscribe(TOPIC_AGE);
      mqtt.subscribe(TOPIC_QUILT);
      mqtt.subscribe(TOPIC_LED_CONTROL);
      mqtt.subscribe(TOPIC_CORE_DISPLAY);

      mqtt.publish(TOPIC_EVENT, "ESP32 connected to MQTT");
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqtt.state());
      Serial.println(" retry in 2 seconds");
      delay(2000);
    }
  }
}


// ================= I2C Devices Init =================
void i2cDevicesInit() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);

  if (!aht.begin()) {
    Serial.println("AHT20 not found. Check SDA/SCL wiring.");
  } else {
    Serial.println("AHT20 initialized. Address: 0x38");
  }

  matrix.begin(MATRIX_ADDR);

  // 保持 0，不靠 setRotation 修正，靠 drawFixedPixel 修正镜像
  matrix.setRotation(0);

  matrix.clear();
  matrix.writeDisplay();

  delay(100);

  displayNumberOnMatrix(matrixCoreValue);

  Serial.println("8x8 matrix initialized. Address: 0x70");
}


// ================= Read AHT20 Humidity =================
float readEnvHumidity() {
  sensors_event_t humidityEvent, tempEvent;
  aht.getEvent(&humidityEvent, &tempEvent);

  float humidity = humidityEvent.relative_humidity;

  Serial.print("env_wet");
  Serial.print(" | Humidity: ");
  Serial.print(humidity);
  Serial.println(" %");

  return humidity;
}


// ================= Read AHT20 Environment Temperature =================
float readEnvTemp() {
  sensors_event_t humidityEvent, tempEvent;
  aht.getEvent(&humidityEvent, &tempEvent);

  float temp = tempEvent.temperature;

  Serial.print("env_temp");
  Serial.print(" | Temp: ");
  Serial.print(temp);
  Serial.println(" C");

  return temp;
}


// ================= Read LM35 Temperature =================
// LM35: 10mV = 1°C
float readLM35Temp(int pin, const char* name) {
  int adcValue = analogRead(pin);
  float voltage = adcValue * 3.3 / 4095.0;
  float tempC = voltage * 100.0;

  Serial.print(name);
  Serial.print(" | ADC: ");
  Serial.print(adcValue);
  Serial.print(" | Voltage: ");
  Serial.print(voltage);
  Serial.print(" V | Temp: ");
  Serial.print(tempC);
  Serial.println(" C");

  return tempC;
}


// ================= setup =================
void setup() {
  Serial.begin(9600);
  delay(1000);

  pinMode(USER_LIGHT, OUTPUT);
  digitalWrite(USER_LIGHT, HIGH);

  pinMode(USER_BUTTON, INPUT);

  pinMode(YELLOW_LED_PIN, OUTPUT);
  pinMode(RED_LED_PIN, OUTPUT);
  pinMode(GREEN_LED_PIN, OUTPUT);

  turnOffAllLED();

  analogReadResolution(12);

  i2cDevicesInit();

  waitForButtonStart();

  wifiInit();
  mqttInit();
}


// ================= loop =================
void loop() {
  if (!mqtt.connected()) {
    mqttReconnect();
  }

  mqtt.loop();

  Serial.println("Hello Raspberry Pi from ESP32");

  float backTemp = readLM35Temp(BACK_TEMP_PIN, "back_temp");
  float coreTemp = readLM35Temp(CORE_TEMP_PIN, "core_temp");
  float handLedTemp = readLM35Temp(HAND_LED_TEMP_PIN, "hand_led_temp");

  float envWet = readEnvHumidity();
  float envTemp = readEnvTemp();

  if (DISPLAY_LOCAL_CORE_TEMP) {
    int displayTemp = round(coreTemp);
    displayNumberOnMatrix(displayTemp);
  } else {
    displayNumberOnMatrix(matrixCoreValue);
  }

  char msg[220];
  snprintf(
    msg,
    sizeof(msg),
    "{\"back_temp\":%.2f,\"core_temp\":%.2f,\"hand_led_temp\":%.2f,\"env_wet\":%.2f,\"env_temp\":%.2f,\"matrix_core_value\":%d}",
    backTemp,
    coreTemp,
    handLedTemp,
    envWet,
    envTemp,
    matrixCoreValue
  );

  mqtt.publish(TOPIC_DATA, msg);

  delay(1000);
}