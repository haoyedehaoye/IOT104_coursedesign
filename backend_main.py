from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from backend_mqtt_handler import MQTTHandler
from typing import Optional
from backend_calculate import calculate_thermal_comfort   # ← 新增导入
import threading

app = FastAPI(title="智能睡眠温控后端")

# ==================== 配置 ====================
HOST = "0.0.0.0"
PORT = 8000

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

mqtt_handler = None

# ==================== 启动事件 ====================
@app.on_event("startup")
async def startup_event():
    global mqtt_handler
    mqtt_handler = MQTTHandler()
    thread = threading.Thread(target=mqtt_handler.start, daemon=True)
    thread.start()
    print(f"🚀 后端启动成功！端口: {PORT}")

    print("\n" + "="*70)
    print("📋 智能睡眠温控后端 - 可用地址")
    print("="*70)
    base = f"http://localhost:{PORT}"
    print(f"首页                  → {base}/")
    print(f"最新传感器数据+舒适度 → {base}/api/latest")
    print(f"热舒适度专用接口       → {base}/api/comfort")
    print(f"历史温度记录           → {base}/api/history")
    print(f"手动控制 LED           → POST {base}/api/led")
    print(f"手动控制点阵屏         → POST {base}/api/display")
    print("="*70)


# ==================== 路由 ====================
@app.get("/")
async def root():
    return {"message": "✅ 智能睡眠温控后端运行正常！", "status": "running"}


@app.get("/api/latest")
async def get_latest():
    """返回最新硬件数据 + 热舒适度计算结果"""
    if mqtt_handler and mqtt_handler.latest_data.get("status") != "waiting_for_first_data":
        # 调用独立计算模块
        comfort = calculate_thermal_comfort(
            sensor_data=mqtt_handler.latest_data,
            user_settings={}          # 这里可以后续接收前端参数
        )
        return {
            "sensor_data": mqtt_handler.latest_data,
            "comfort": comfort
        }
    return {"status": "mqtt_not_ready", "comfort": {"category": "等待数据中..."}} 


@app.get("/api/comfort")
async def get_comfort(
    height: Optional[float] = 1.70,
    weight: Optional[float] = 60,
    gender: Optional[int] = 1,
    posture: Optional[int] = 1,
    quilt: Optional[int] = 2
):
    """支持前端传递用户参数计算舒适度"""
    if mqtt_handler and mqtt_handler.latest_data.get("status") != "waiting_for_first_data":
        user_settings = {
            "height": height,
            "weight": weight,
            "gender": gender,
            "posture": posture,
            "quilt": quilt
        }
        
        comfort = calculate_thermal_comfort(
            sensor_data=mqtt_handler.latest_data,
            user_settings=user_settings
        )
        return comfort
    return {"category": "等待数据中...", "message": "数据不足"}


@app.get("/api/history")
async def get_history(limit: int = 100):
    if mqtt_handler:
        return {
            "total": len(mqtt_handler.history),
            "limit": limit,
            "data": mqtt_handler.get_history(limit)
        }
    return {"status": "mqtt_not_ready", "data": []}


@app.post("/api/led")
async def control_led(command: dict):
    if mqtt_handler and "command" in command:
        cmd = command["command"]
        mqtt_handler.client.publish("sleep/device/led", cmd)
        return {"status": "success", "command": cmd}
    return {"status": "error"}


@app.post("/api/display")
async def control_display(data: dict):
    if mqtt_handler and "value" in data:
        value = str(data["value"])
        mqtt_handler.client.publish("sleep/device/core_display", value)
        return {"status": "success", "value": value}
    return {"status": "error"}


# ==================== 启动 ====================
if __name__ == "__main__":
    print(f"正在启动后端服务... 端口: {PORT}")
    uvicorn.run(
        "backend_main:app",
        host=HOST, 
        port=PORT, 
        reload=True
    )