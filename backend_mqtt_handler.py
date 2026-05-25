import paho.mqtt.client as mqtt
import json
from datetime import datetime
from collections import deque

BROKER = "20.205.107.61"
PORT = 1883


class MQTTHandler:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        # ==================== 核心数据 ====================
        self.latest_data = {"status": "waiting_for_first_data"}
        self.history = deque(maxlen=200)   # 最多保存200条记录

    def start(self):
        try:
            self.client.connect(BROKER, PORT, 60)
            self.client.loop_start()
            print("🚀 MQTT 客户端正在连接...")
        except Exception as e:
            print("❌ MQTT 连接失败:", e)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✅ MQTT 连接成功！")
            client.subscribe("sleep/device/data")
            client.subscribe("sleep/device/event")
        else:
            print(f"❌ MQTT 连接失败，错误码: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            if msg.topic == "sleep/device/data":
                data = json.loads(msg.payload.decode())
                
                # 添加时间戳
                record = {
                    **data,
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "full_time": datetime.now().isoformat()
                }
                
                self.latest_data = record
                self.history.append(record)
                
                print(f"📡 收到数据 → core_temp: {data.get('core_temp')} | 历史记录: {len(self.history)} 条")
                
                self.auto_control_led(data)
                
        except Exception as e:
            print("❌ 数据解析失败:", e)

    def auto_control_led(self, data):
        """自动控制 LED"""
        core = data.get("core_temp", 0)
        cmd = "hot" if core >= 33.5 else "cold" if core <= 29 else "ok"
        self.client.publish("sleep/device/led", cmd)

    # ==================== 提供给 main.py 使用的方法 ====================
    def get_latest_data(self):
        """返回最新的硬件数据"""
        return self.latest_data

    def get_history(self, limit=100):
        """返回历史记录"""
        return list(self.history)[-limit:]