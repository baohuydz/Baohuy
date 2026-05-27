from flask import Flask
app = Flask('')

@app.route('/')
def home():
    return "Hệ thống Siêu Trí Tuệ BaoHuyDevs hoạt động tốt!"
