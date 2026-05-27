from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Hệ thống Siêu Trí Tuệ BaoHuyDevs đang hoạt động ổn định!"

def run():
    # Chạy Flask trên port 8080
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    # Chạy Web Server trên một luồng (Thread) riêng biệt để không làm gián đoạn Bot
    t = Thread(target=run)
    t.start()
