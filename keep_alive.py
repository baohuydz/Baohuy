import os
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Hệ thống Siêu Trí Tuệ BaoHuyDevs đang hoạt động 24/7 ổn định trên Render!"

def setup_keep_alive():
    # Lấy cổng động do Render cấp qua biến môi trường 'PORT'
    port = int(os.environ.get("PORT", 8080))
    return port
