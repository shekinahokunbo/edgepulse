import time, random, math, requests

URL = "http://127.0.0.1:8000/ingest"
sensor_ids = ["imu_1", "temp_2", "vibration_7"]

t = 0.0
while True:
    t += 0.1
    for sid in sensor_ids:
        base = {
            "imu_1": math.sin(t) * 2.0,
            "temp_2": 25 + math.sin(t/10)*0.5,
            "vibration_7": math.sin(t*3)*0.2,
        }[sid]

        noise = random.gauss(0, 0.05)
        value = base + noise

        # occasional anomaly spike
        if random.random() < 0.01:
            value += random.choice([5, -5, 3, -3])

        requests.post(URL, json={"sensor_id": sid, "value": value})

    time.sleep(0.1)
