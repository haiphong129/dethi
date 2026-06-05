import requests
import time

while True:
    try:
        requests.get("https://dethi-cjoc.onrender.com/health")
    except:
        pass

    time.sleep(300)