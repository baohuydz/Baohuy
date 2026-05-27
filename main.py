import logging
import random
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==========================================
# CẤU HÌNH UPTIME TREO BOT (KEEP-ALIVE)
# ==========================================
server = Flask('')

@server.route('/')
def home():
    return "Hệ thống Bot Shop Key Liên Quân đang hoạt động ổn định 24/7!"

def run_server():
    # Chạy một trang web phụ trợ ở cổng 8080 để UptimeRobot ping vào giữ bot luôn thức
    server.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

# ==========================================
# CẤU HÌNH LOGGING VÀ THÔNG TIN BOT
# ==========================================
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "6367532329:AAHUNIo2eLnCNSIle4b2IujI5Dumo0geYjI"
ADMIN_IDS = [5736655322]            # Thay bằng ID Telegram thực tế của bạn
ADMIN_USERNAME = "@tai_khoan_admin" # Tên liên hệ hỗ trợ hiển thị cho khách

# BỘ NHỚ LƯU TRỮ TẠM THỜI (LƯU TRÊN RAM)
PRODUCTS = {}       # Lưu thông tin gói: {"p1": {"name": "Gói Ngày", "price": 20000, "link": "https://...", "qr": "file_id"}}
KEY_STOCK = {}      # Lưu kho key: {"p1": ["KEY1", "KEY2"]}
PENDING_ORDERS = {} # Lưu đơn hàng chờ duyệt: {"#LQ12345": {"customer_id": 111, "p_id": "p1"}}

# --- GIAO DIỆN KHÁCH HÀNG (MENU CHÍNH) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data['buying_p_id'] = None
    context.user_data['customer_state'] = None
    
    keyboard = [
        [InlineKeyboardButton("🔑 Mua Key Liên Quân", callback_query_data='view_products')],
        [InlineKeyboardButton("📞 Hỗ trợ / Khiếu nại", callback_query_data='support')]
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🛠️ Trang Quản Trị (Admin)", callback_query_data='admin_menu')])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "🔥 **SHOP KEY LIÊN QUÂN TỰ ĐỘNG** 🔥\n\n"
        "⚡ Uy tín - Giao key và link tải tự động trong 30 giây.\n"
        "⚡ Hệ thống hoạt động liên tục không nghỉ.\n\n"
        "👇 Vui lòng bấm nút bên dưới để chọn gói key:"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# --- GIAO DIỆN QUẢN TRỊ ADMIN ---
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await query.answer("Bạn không có quyền truy cập vùng này!", show_alert=True)
        return
    keyboard = [
        [InlineKeyboardButton("➕ Tạo gói sản phẩm mới", callback_query_data='admin_add_product')],
        [InlineKeyboardButton("📥 Nạp thêm Key vào kho", callback_query_data='admin_stock_menu')],
        [InlineKeyboardButton("🔙 Quay lại Menu Khách", callback_query_data='main_menu')]
    ]
    await query.edit_message_text("⚡ **HỆ THỐNG QUẢN TRỊ SHOP KEY** ⚡\nChọn chức năng quản lý bên dưới:", reply_markup=InlineKeyboardMarkup(keyboard))

# Admin Bước 1: Yêu cầu nhập tên và giá gói
async def admin_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data['admin_state'] = 'waiting_product_info'
    await query.edit_message_text(
        "⚙️ **BƯỚC 1: TẠO GÓI SẢN PHẨM & GIÁ**\nVui lòng nhập theo cấu trúc chính xác:\n`Tên gói - Giá tiền`\n\n*Ví dụ:* `Key Ngày VIP - 20000` hoặc `Key Tuần VIP - 90000` ",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Hủy bỏ", callback_query_data='admin_menu')]])
    )

# Admin Chọn gói để nạp Key
async def admin_stock_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not PRODUCTS:
        await query.edit_message_text("❌ Chưa có gói sản phẩm nào trong shop! Vui lòng bấm tạo gói trước.", 
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại Admin", callback_query_data='admin_menu')]]))
        return
    keyboard = []
    for p_id, p_info in PRODUCTS.items():
        stock_count = len(KEY_STOCK.get(p_id, []))
        keyboard.append([InlineKeyboardButton(f"📦 {p_info['name']} (Còn {stock_count} key)", callback_query_data=f"admin_load_{p_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Quay lại Admin", callback_query_data='admin_menu')])
    await query.edit_message_text("🎯 Chọn gói bạn muốn bổ sung thêm Key vào kho:", reply_markup=InlineKeyboardMarkup(keyboard))

# XỬ LÝ DỮ LIỆU CHỮ VÀ ẢNH CẤU HÌNH DO ADMIN GỬI LÊN
async def handle_admin_inputs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS: return
    state = context.user_data.get('admin_state')

    # Nhận Bước 1: Lưu tên & giá gói
    if state == 'waiting_product_info' and update.message.text:
        try:
            name, price = update.message.text.split('-')
            context.user_data['temp_product'] = {"name": name.strip(), "price": int(price.strip())}
            context.user_data['admin_state'] = 'waiting_product_link'
            await update.message.reply_text(f"✅ Đã nhận gói: **{name.strip()}**\n\n🔗 **BƯỚC 2:** Hãy gửi **Link tải sản phẩm** (Link Drive/Mega tải file cài đặt hoặc link web hướng dẫn).")
        except:
            await update.message.reply_text("❌ Sai cấu trúc! Định dạng chuẩn phải có dấu gạch ngang ở giữa:\n`Tên gói - Giá` (Ví dụ: `Key Ngày - 20000`)")

    # Nhận Bước 2: Lưu Link sản phẩm
    elif state == 'waiting_product_link' and update.message.text:
        link = update.message.text.strip()
        context.user_data['temp_product']['link'] = link
        context.user_data['admin_state'] = 'waiting_product_qr'
        await update.message.reply_text(f"✅ Đã ghi nhận link tải.\n\n📷 **BƯỚC 3:** Hãy gửi **Ảnh mã QR Ngân hàng** nhận tiền riêng của gói này.")

    # Nhận Bước 3: Lưu ảnh QR -> Hoàn tất quy trình tạo gói
    elif state == 'waiting_product_qr' and update.message.photo:
        qr_id = update.message.photo[-1].file_id
        temp = context.user_data['temp_product']
        p_id = f"p{len(PRODUCTS) + 1}"
        
        PRODUCTS[p_id] = {
            "name": temp["name"], 
            "price": temp["price"], 
            "link": temp["link"], 
            "qr": qr_id
        }
        KEY_STOCK[p_id] = [] # Khởi tạo khay kho rỗng cho gói
        
        context.user_data['admin_state'] = None
        context.user_data['temp_product'] = None
        await update.message.reply_text(f"🎉 **THÀNH CÔNG!** Đã tạo hoàn tất gói **{temp['name']}**.\n⚠️ Lưu ý: Kho đang trống (0 key). Hãy bấm nút dưới để vào mục nạp key cho khách mua.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Đi nạp Key ngay", callback_query_data='admin_stock_menu')]]))

    # Nhận danh sách Key nạp hàng loạt vào kho
    elif state and state.startswith('waiting_keys_') and update.message.text:
        p_id = state.replace('waiting_keys_', '')
        input_keys = [k.strip() for k in update.message.text.split('\n') if k.strip()]
        
        KEY_STOCK[p_id].extend(input_keys)
        context.user_data['admin_state'] = None
        
        await update.message.reply_text(f"✅ Đã nạp thành công thêm {len(input_keys)} key vào kho của gói **{PRODUCTS[p_id]['name']}**!",
                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛠️ Về Trang Admin", callback_query_data='admin_menu')]]))

# --- XỬ LÝ TẤT CẢ NÚT BẤM (MUA HÀNG & DUYỆT ĐƠN) ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # LOGIC MENU ADMIN
    if data.startswith('admin_'):
        if data == 'admin_menu': await admin_menu(update, context)
        elif data == 'admin_add_product': await admin_add_product(update, context)
        elif data == 'admin_stock_menu': await admin_stock_menu(update, context)
        elif data.startswith('admin_load_'):
            p_id = data.replace('admin_load_', '')
            context.user_data['admin_state'] = f'waiting_keys_{p_id}'
            await query.edit_message_text(f"📥 Hãy gửi danh sách mã Key cho gói **{PRODUCTS[p_id]['name']}**.\n"
                                          f"⚠️ *Yêu cầu: Mỗi mã key nằm trên một dòng riêng biệt.*")
        
        # 🟢 HÀNH ĐỘNG: ADMIN BẤM NÚT DUYỆT TIỀN (Giao key + link tự động)
        elif data.startswith('admin_approve_'):
            order_id = data.replace('admin_approve_', '')
            order = PENDING_ORDERS.get(order_id)
            
            if not order:
                await query.edit_message_text("⚠️ Đơn hàng này đã được phê duyệt hoặc hủy bỏ trước đó!")
                return
                
            p_id = order['p_id']
            # Kiểm tra xem kho còn key để giao không
            if len(KEY_STOCK.get(p_id, [])) > 0:
                delivered_key = KEY_STOCK[p_id].pop(0) # Lấy key đầu tiên ra khỏi kho
                product = PRODUCTS[p_id]
                
                try:
                    # Bắn thông tin trả hàng về thẳng mục chat riêng của khách mua
                    await context.bot.send_message(
                        chat_id=order['customer_id'],
                        text=(
                            f"🎁 **CẢM ƠN BẠN ĐÃ THANH TOÁN THÀNH CÔNG!**\n\n"
                            f"▪️ Mã đơn hàng: `{order_id}`\n"
                            f"▪️ Sản phẩm: *{product['name']}*\n\n"
                            f"🔑 **MÃ KEY KÍCH HOẠT CỦA BẠN:**\n"
                            f"`{delivered_key}`\n"
                            f"*(Mẹo: Bạn có thể chạm vào mã key ở trên để tự sao chép)*\n\n"
                            f"🔗 **LINK TẢI SẢN PHẨM / HƯỚNG DẪN:**\n"
                            f"{product['link']}"
                        ),
                        parse_mode="Markdown"
                    )
                    # Cập nhật trạng thái tin nhắn duyệt tiền của Admin
                    await query.edit_message_text(f"✅ **ĐÃ DUYỆT ĐƠN THÀNH CÔNG {order_id}**\nKey `{delivered_key}` và Link tải đã được hệ thống bàn giao cho khách.")
                    del PENDING_ORDERS[order_id] # Xóa khỏi danh sách chờ duyệt
                except Exception as e:
                    await query.edit_message_text(f"❌ Lỗi gửi key (Khách có thể đã xóa chat hoặc chặn bot). Lỗi: {e}")
            else:
                await query.edit_message_text(f"⚠️ Không thể duyệt đơn! Kho của gói *{PRODUCTS[p_id]['name']}* hiện đã **HẾT KEY**. Hãy nạp thêm key rồi bấm duyệt lại sau.", parse_mode="Markdown")
                
        # 🔴 HÀNH ĐỘNG: ADMIN BẤM NÚT TỪ CHỐI ĐƠN
        elif data.startswith('admin_decline_'):
            order_id = data.replace('admin_decline_', '')
            order = PENDING_ORDERS.get(order_id)
            if not order: 
                await query.edit_message_text("⚠️ Đơn hàng này đã được xử lý rồi!")
                return
            try:
                await context.bot.send_message(chat_id=order['customer_id'], text=f"❌ **ĐƠN HÀNG {order_id} BỊ TỪ CHỐI!**\nLý do: Admin kiểm tra tài khoản chưa nhận được tiền khớp với đơn hàng hoặc ảnh chụp hóa đơn bị lỗi. Vui lòng nhắn tin hỗ trợ nếu có nhầm lẫn.")
            except: pass
            del PENDING_ORDERS[order_id]
            await query.edit_message_text(f"❌ Đã từ chối đơn hàng `{order_id}`.")
        return

    # LOGIC MUA HÀNG CỦA KHÁCH
    if data == 'view_products':
        if not PRODUCTS:
            await query.edit_message_text("Shop đang cập nhật sản phẩm mới, bạn vui lòng quay lại sau nhé!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại Menu", callback_query_data='main_menu')]]))
            return
        keyboard = []
        for p_id, p_info in PRODUCTS.items():
            stock = len(KEY_STOCK.get(p_id, []))
            keyboard.append([InlineKeyboardButton(f"{p_info['name']} - {p_info['price']:,}đ (Còn {stock})", callback_query_data=f"buy_key_{p_id}")])
        keyboard.append([InlineKeyboardButton("🔙 Quay lại Menu", callback_query_data='main_menu')])
        await query.edit_message_text("🛒 **DANH SÁCH GÓI KEY LIÊN QUÂN:**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith('buy_key_'):
        p_id = data.replace('buy_key_', '')
        if len(KEY_STOCK.get(p_id, [])) == 0:
            await query.answer("⚠️ Gói này hiện tại đang hết key, vui lòng mua gói khác hoặc báo Admin bổ sung!", show_alert=True)
            return
        product = PRODUCTS[p_id]
        context.user_data['buying_p_id'] = p_id
        context.user_data['customer_state'] = 'waiting_bill'
        
        # Gửi ảnh QR ngân hàng cấu hình riêng của gói đó cho khách quét
        await query.message.reply_photo(
            photo=product['qr'],
            caption=f"💳 **THÔNG TIN THANH TOÁN ĐƠN HÀNG**\n\n📦 Sản phẩm: *{product['name']}*\n💰 Giá bán: *{product['price']:,}đ*\n\n👇 Vui lòng quét mã QR ở trên để chuyển khoản đúng số tiền.\n⚠️ **QUAN TRỌNG:** Sau khi chuyển khoản thành công, hãy **GỬI ẢNH CHỤP BILL GIAO DỊCH** trực tiếp vào đây để nhận Key + Link tự động!",
            parse_mode="Markdown"
        )
        await query.message.delete()

    elif data == 'support':
        await query.edit_message_text(f"📞 Mọi thắc mắc về kỹ thuật, khiếu nại dòng tiền hoặc lỗi key, vui lòng liên hệ Admin trực tiếp tại: {ADMIN_USERNAME}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Quay lại", callback_query_data='main_menu')]]))
    elif data == 'main_menu':
        await start(update, context)

# --- XỬ LÝ KHI KHÁCH HÀNG GỬI ẢNH BILL ---
async def handle_customer_bill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in ADMIN_IDS: return # Nếu admin gửi ảnh bừa thì bỏ qua không xử lý
    
    if context.user_data.get('customer_state') == 'waiting_bill' and update.message.photo:
        p_id = context.user_data.get('buying_p_id')
        bill_photo_id = update.message.photo[-1].file_id
        username = update.effective_user.username or update.effective_user.first_name
        
        # Sinh mã đơn hàng ngẫu nhiên chuyên nghiệp
        order_id = f"#LQ{random.randint(10000, 99999)}"
        PENDING_ORDERS[order_id] = {"customer_id": user_id, "p_id": p_id}
        
        # Xóa trạng thái đang mua để làm sạch bộ nhớ khách
        context.user_data['customer_state'] = None
        context.user_data['buying_p_id'] = None
        
        await update.message.reply_text(f"⏳ **Hệ thống đã nhận được Bill của đơn {order_id}!**\nVui lòng chờ trong giây lát để Admin đối soát biến động số dư và ấn nút duyệt trả key.")
        
        # Thiết lập nút bấm kiểm soát cho Admin
        admin_keyboard = [
            [InlineKeyboardButton("✅ Duyệt Tiền (Giao Key+Link)", callback_query_data=f"admin_approve_{order_id}")],
            [InlineKeyboardButton("❌ Từ Chối Đơn (Sai Bill)", callback_query_data=f"admin_decline_{order_id}")]
        ]
        # Bắn bill về toàn bộ tài khoản Admin được cấu hình
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_photo(
                    chat_id=admin_id, photo=bill_photo_id,
                    caption=(
                        f"🚨 **PHÁT HIỆN ĐƠN HÀNG MỚI CHỜ DUYỆT!**\n\n"
                        f"▪️ Mã đơn: `{order_id}`\n"
                        f"▪️ Khách hàng: @{username} (ID: {user_id})\n"
                        f"▪️ Đăng ký mua: *{PRODUCTS[p_id]['name']}*\n"
                        f"▪️ Số tiền cần nhận: **{PRODUCTS[p_id]['price']:,}đ**\n\n"
                        f"👉 Hãy kiểm tra tài khoản ngân hàng, nếu đã nhận đủ tiền hãy ấn nút duyệt bên dưới:"
                    ),
                    parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(admin_keyboard)
                )
            except: pass

# --- ĐIỂM KHỞI CHẠY CHƯƠNG TRÌNH ---
def main():
    # 1. Kích hoạt Web Server ẩn để duy trì Uptime chống ngủ đông
    keep_alive()

    # 2. Liên kết điều khiển Telegram Bot bằng Token
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_customer_bill))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_inputs))

    print("=== BOT SHOP KEY ĐANG HOẠT ĐỘNG HOÀN TOÀN TỰ ĐỘNG ===")
    app.run_polling()

if __name__ == '__main__':
    main()
