import logging
import requests
import io
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==================== CẤU HÌNH THÔNG TIN ====================
TELEGRAM_BOT_TOKEN = "6367532329:AAGYVm-U5l8jU8Kur_2WLmu9Gr9l5agRR9g"
BASE_URL = "https://shop.getbasic.link/api/v1"

# Thay đổi tài khoản và mật khẩu đăng nhập web của bạn tại đây
USER_EMAIL = "huydoan633@gmail.com"
USER_PASSWORD = "036320"

# Biến toàn cục hệ thống lưu trữ Token tạm thời sau khi đăng nhập
CURRENT_BEARER_TOKEN = None

# Cấu hình Nhật ký hệ thống (Log) để theo dõi luồng dữ liệu
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# ==================== HÀM XỬ LÝ API HỆ THỐNG ====================

def api_login_and_get_token():
    """Gửi tài khoản mật khẩu lên API đăng nhập để lấy chuỗi Bearer Token"""
    global CURRENT_BEARER_TOKEN
    try:
        # Endpoint login chuẩn hóa dựa trên tài liệu API hệ thống
        login_url = f"{BASE_URL}/login" 
        data = {
            "email": USER_EMAIL,
            "password": USER_PASSWORD
        }
        response = requests.post(login_url, data=data, timeout=10)
        
        if response.status_code == 200:
            res_data = response.json()
            # Trích xuất Token từ phản hồi của Server
            CURRENT_BEARER_TOKEN = res_data.get("token") or res_data.get("access_token")
            logger.info("🔑 Đăng nhập hệ thống thành công! Đã cập nhật Token mới.")
            return CURRENT_BEARER_TOKEN
        else:
            logger.error(f"❌ Đăng nhập thất bại. Mã phản hồi lỗi: {response.status_code}")
    except Exception as e:
        logger.error(f"❌ Lỗi kết nối khi cố gắng đăng nhập: {e}")
    return None

def get_auth_headers():
    """Tự động kiểm tra và khởi tạo Header chứa Authorization Token"""
    global CURRENT_BEARER_TOKEN
    if not CURRENT_BEARER_TOKEN:
        api_login_and_get_token()
    return {"Authorization": f"Bearer {CURRENT_BEARER_TOKEN}"}

def api_get_balance():
    """Gọi API kiểm tra số dư hiện tại của tài khoản"""
    try:
        response = requests.get(f"{BASE_URL}/balance", headers=get_auth_headers(), timeout=10)
        
        # Nếu Token hết hạn (401), tiến hành đăng nhập lại tự động và thử lại lần nữa
        if response.status_code == 401:
            api_login_and_get_token()
            response = requests.get(f"{BASE_URL}/balance", headers=get_auth_headers(), timeout=10)
            
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Lỗi API kiểm tra số dư: {e}")
    return None

def api_register_udid(udid, plan):
    """Gọi API thực hiện đăng ký UDID mới vào hệ thống"""
    data = {"udid": udid, "plan": str(plan)}
    try:
        response = requests.post(f"{BASE_URL}/register", headers=get_auth_headers(), data=data, timeout=10)
        
        if response.status_code == 401:
            api_login_and_get_token()
            response = requests.post(f"{BASE_URL}/register", headers=get_auth_headers(), data=data, timeout=10)
            
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Lỗi API đăng ký UDID: {e}")
    return None

def api_check_provision(order_id):
    """Gọi API tra cứu thông tin chứng chỉ và trạng thái đơn hàng"""
    try:
        response = requests.get(f"{BASE_URL}/provision?order_id={order_id}", headers=get_auth_headers(), timeout=10)
        
        if response.status_code == 401:
            api_login_and_get_token()
            response = requests.get(f"{BASE_URL}/provision?order_id={order_id}", headers=get_auth_headers(), timeout=10)
            
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Lỗi API tra cứu đơn hàng: {e}")
    return None


# ==================== LOGIC XỬ LÝ BOT TELEGRAM ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lệnh /start: Thiết lập giao diện nút bấm Menu tương tác"""
    keyboard = [
        [KeyboardButton("💰 Kiểm tra số dư"), KeyboardButton("🔎 Tra cứu đơn hàng")],
        [KeyboardButton("📝 Đăng ký UDID (Gói 3)"), KeyboardButton("📝 Đăng ký iPad (Gói 12)")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "👋 Chào mừng bạn đến với Bot quản lý dịch vụ Apple Cert tự động!\n"
        "Vui lòng chọn tính năng cần thao tác ở thanh Menu bên dưới.",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Điều hướng xử lý dữ liệu và hành động của người dùng"""
    text = update.message.text
    user_data = context.user_data

    # Chức năng: Kiểm tra số dư ví tiền
    if text == "💰 Kiểm tra số dư":
        res = api_get_balance()
        if res and res.get("status") == "200":
            balance = res.get("balance", 0)
            await update.message.reply_text(f"💳 Số dư tài khoản hiện tại: *{balance:,}đ*", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Không lấy được thông tin số dư. Vui lòng kiểm tra lại cấu hình tài khoản web.")

    # Chức năng: Đăng ký UDID mới cho iPhone (Gói 3)
    elif text == "📝 Đăng ký UDID (Gói 3)":
        user_data['action'] = 'waiting_udid_g3'
        await update.message.reply_text("📥 Vui lòng nhập hoặc gửi chuỗi **UDID iPhone** (Gói 3):", parse_mode="Markdown")

    # Chức năng: Đăng ký UDID mới cho iPad (Gói 12)
    elif text == "📝 Đăng ký iPad (Gói 12)":
        user_data['action'] = 'waiting_udid_g12'
        await update.message.reply_text("📥 Vui lòng nhập hoặc gửi chuỗi **UDID iPad** (Gói 12):", parse_mode="Markdown")

    # Chức năng: Tra cứu trạng thái đơn hàng để nhận Chứng chỉ (.p12, .mobileprovision)
    elif text == "🔎 Tra cứu đơn hàng":
        user_data['action'] = 'waiting_order_id'
        await update.message.reply_text("📥 Vui lòng nhập **Mã đơn hàng (Order ID)** bạn cần kiểm tra:")

    # Xử lý nhập văn bản tự do dựa trên trạng thái (State) người dùng lựa chọn trước đó
    else:
        current_action = user_data.get('action')

        # Xử lý khi nhận được chuỗi UDID gửi lên hệ thống đăng ký
        if current_action in ['waiting_udid_g3', 'waiting_udid_g12']:
            udid = text.strip()
            plan = "3" if current_action == 'waiting_udid_g3' else "12"
            
            await update.message.reply_text("⏳ Đang xử lý yêu cầu đăng ký lên máy chủ, vui lòng đợi giây lát...")
            res = api_register_udid(udid, plan)
            
            if res and res.get("status") == "200":
                msg = (
                    f"✅ **Gửi đơn đăng ký thành công!**\n\n"
                    f"🔹 Mã đơn hàng: `{res.get('order_id')}`\n"
                    f"🔹 Số dư tài khoản: {res.get('balance'):,}đ\n"
                    f"🔹 Trạng thái xử lý: {res.get('message')}\n\n"
                    f"👉 Copy mã đơn hàng trên và bấm nút **Tra cứu đơn hàng** để tải Cert về."
                )
                await update.message.reply_text(msg, parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Đăng ký thất bại. Lý do: Số dư khả dụng không đủ hoặc định dạng chuỗi UDID không chính xác.")
            
            user_data['action'] = None  # Xóa trạng thái hàng chờ

        # Xử lý khi nhận mã đơn hàng để tải bộ chứng chỉ về thiết bị
        elif current_action == 'waiting_order_id':
            order_id = text.strip()
            await update.message.reply_text(f"⏳ Đang tra cứu dữ liệu đơn hàng `{order_id}`...")
            res = api_check_provision(order_id)
            
            if res and res.get("status") == "200":
                status = res.get("message")
                
                if status == "completed":
                    p12_url = res.get("p12")
                    provision_text = res.get("provision")
                    
                    await update.message.reply_text(f"🟢 Đơn hàng đã hoàn thành xử lý!\n\n📦 Link tải File P12:\n{p12_url}\n\n⏳ Bot đang sinh file vật lý định dạng `.mobileprovision` gửi trực tiếp cho bạn...")
                    
                    # Chuyển đổi mã chuỗi Text XML sang định dạng File Binary trực tuyến không lưu ổ cứng
                    if provision_text:
                        file_io = io.BytesIO(provision_text.encode('utf-8'))
                        file_io.name = f"{order_id}.mobileprovision"
                        await update.message.reply_document(document=file_io, caption=f"📄 Bản gốc file Provision cho đơn hàng `{order_id}`", parse_mode="Markdown")
                else:
                    await update.message.reply_text(f"🟡 Đơn hàng của bạn đang ở trạng thái: `{status}`. Vui lòng quay lại kiểm tra sau ít phút.")
            else:
                await update.message.reply_text("❌ Sai mã đơn hàng hoặc hệ thống Server đang bảo trì.")
            
            user_data['action'] = None  # Xóa trạng thái hàng chờ
        else:
            await update.message.reply_text("⚠️ Vui lòng thao tác lựa chọn một chức năng cụ thể trên Menu bàn phím điều hướng.")


def main():
    """Hàm khởi tạo chạy Polling quét cập nhật tiến trình của Bot Telegram"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Thiết lập bộ lắng nghe sự kiện Lệnh và Văn bản tin nhắn từ người dùng
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Kích hoạt trạng thái hoạt động trực tuyến liên tục
    print("🤖 Bot Telegram Apple Cert đã khởi chạy hoàn tất và đang hoạt động...")
    application.run_polling()

if __name__ == "__main__":
    main()
