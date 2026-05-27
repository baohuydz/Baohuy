import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Hệ thống Siêu Trí Tuệ BaoHuyDevs đang hoạt động ổn định trên Render!"

def run():
    # Lấy cổng động do Render cấp qua biến môi trường 'PORT', nếu không có thì mặc định là 8080
    port = int(os.environ.get("PORT", 8080))
    
    # Chạy Flask trên host 0.0.0.0 và cổng đã nhận diện
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    # Chạy Web Server trên một luồng (Thread) riêng biệt để không làm gián đoạn Bot
    t = Thread(target=run)
    t.start()
