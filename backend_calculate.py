import math

def calculate_thermal_comfort(sensor_data: dict, user_settings: dict = None):
    """
    计算睡眠热舒适度（基于论文两部分模型）
    """
    if user_settings is None:
        user_settings = {}

    # ==================== 提取硬件数据 ====================
    core_temp = sensor_data.get("core_temp", 0.0)
    back_temp = sensor_data.get("back_temp", 0.0)
    env_temp  = sensor_data.get("env_temp", 0.0)
    env_wet   = sensor_data.get("env_wet", 0.0)

    # ==================== 提取用户设置 ====================
    height = user_settings.get("height", 1.70)
    weight = user_settings.get("weight", 60)
    gender = user_settings.get("gender", 1)
    posture = user_settings.get("posture", 1)
    mattress = user_settings.get("mattress", 1)
    quilt = user_settings.get("quilt", 2)

    # ==================== 计算热工参数 ====================
    # 1. 体表面积（修正为论文推荐公式）
    if gender == 1:      # 男性
        human_surface = 0.607 * height + 0.0127 * weight - 0.0698
    elif gender == 2:    # 女性
        human_surface = 0.586 * height + 0.0126 * weight - 0.0461
    else:
        human_surface = 1.8

    # 2. 接触面积比例
    alpha = 0.39 if posture == 1 else 0.24

    # 3. 床垫导热系数
    k = 0.048 if mattress == 1 else 0.147

    # 4. 被子 clo 值
    if quilt == 1:
        quilt_clo = 0.1
    elif quilt == 2:
        quilt_clo = 0.6
    elif quilt == 3:
        quilt_clo = 2.2
    else:
        quilt_clo = 0.6

    # ==================== 计算 QL（热负荷） ====================
    # 环境水蒸气分压
    sat_pressure = 610.78 * math.exp((17.27 * env_temp) / (env_temp + 237.3))
    water_pressure = sat_pressure * (env_wet / 100.0)

    # 非接触面皮肤温度
    skin_temp = back_temp * 0.75 + core_temp * 0.25

    # 皮肤饱和水蒸气压
    water_pressure_skin = 610.78 * math.exp((17.27 * skin_temp) / (skin_temp + 237.3))

    # 呼吸散热
    q_brea = (13.41 - 1.519 * 10**(-3) * water_pressure - 0.13 * env_temp) / human_surface

    # 皮肤散热
    E_d = 3.074 * 10**(-3) * (1 - 0.8 * alpha) * (water_pressure_skin - water_pressure)

    R_cl = quilt_clo * 0.155
    f_cl = 1.05 if quilt_clo <= 0.1 else 1.1 if quilt_clo <= 0.6 else 1.2

    h_c = 5.1
    h_r = 3.235
    h = h_c + h_r
    t_o = env_temp

    C_R = (1 - alpha) * (skin_temp - t_o) / (R_cl + 1 / (f_cl * h))

    d = 0.2 if mattress == 1 else 0.05
    t_sk2 = 35.4
    E_cond = k * alpha * (t_sk2 - env_temp) / d

    q_skin = E_d + C_R + E_cond

    # 核心热负荷
    M = 40.0
    QL = M - q_brea - q_skin

    # ==================== 舒适度分类 ====================
    if -1.3 <= QL <= 1.3:
        category = "I类(最舒适)"
    elif -3.3 <= QL <= 3.3:
        category = "II类(推荐舒适)"
    elif -6.6 <= QL <= 6.6:
        category = "III类(勉强接受)"
    else:
        category = "IV类(不舒适)"

    # ==================== 返回结果 ====================
    return {
        "QL": round(QL, 2),
        "category": category,
        "env_temp": round(env_temp, 2),
        "humidity": round(env_wet, 2),
        "skin_temp": round(skin_temp, 2),
        "q_brea": round(q_brea, 2),
        "q_skin": round(q_skin, 2),
    }