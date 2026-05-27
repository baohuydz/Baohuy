import asyncio
import logging
import sys
import time
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from google import genai
from openai import OpenAI

# ==== KHỞI TẠO WEB SERVER ĐỂ RENDER QUÉT PORT ====
from keep_alive import app

# --- CẤU HÌNH TOKEN VÀ API KEY CHÍNH THỨC ---
TELEGRAM_TOKEN = "6367532329:AAEe9f501-n72-ZKLv4s5I_4O51vgznyXao"
GEMINI_API_KEY = "AIzaSyDD1NhOh6aX58SdnK-3A5MYiQG-AqPDfJM"
OPENROUTER_API_KEY = "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"

# --- KHỞI TẠO CÁC CỔNG AI TIẾNG VIỆT ---
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
openrouter_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

dp = Dispatcher()

# --- CÁC HÀM GỌI API AN TOÀN ---
async def fetch_gemini(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, lambda: gemini_client.models.generate_content(
            model='gemini-1.5-flash', contents=prompt
        ))
        return f"[Gemini]: {res.text}" if res.text else ""
    except Exception as e:
        logging.warning(f"Gemini API gặp sự cố: {e}")
        return ""

async def fetch_openrouter(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, lambda: openrouter_client.chat.completions.create(
            model="deepseek/deepseek-chat", 
            messages=[{"role": "user", "content": prompt}], 
            timeout=8
        ))
        return f"[DeepSeek]: {res.choices[0].message.content}" if res.choices[0].message.content else ""
    except Exception as e:
        logging.warning(f"OpenRouter API gặp sự cố: {e}")
        return ""

# --- BỘ NÃO HỢP NHẤT DỮ LIỆU TIẾNG VIỆT (TÍNH NĂNG TỰ CỨU HỘ) ---
async def aggregate_responses(user_prompt: str, raw_responses: list) -> str:
    # Lọc bỏ các phản hồi trống nếu một trong hai AI bị nghẽn
    valid_responses = [resp for resp in raw_responses if resp.strip()]
    
    if not valid_responses:
        return "Hiện tại hệ thống AI đang bận xử lý dữ liệu. Bạn vui lòng thử lại sau ít phút nhé!"
        
    combined_context = "\n\n=====\n\n".join(valid_responses)
    
    system_instruction = (
        "Bạn là một Siêu trí tuệ nhân tạo có năng lực thấu cảm và diễn đạt tiếng Việt đỉnh cao.\n"
        "Dưới đây là dữ liệu thô thu thập được từ các mô hình AI.\n"
        "Nhiệm vụ của bạn:\n"
        "1. Đọc và đúc kết thông tin chính xác, loại bỏ các ý trùng lặp.\n"
        "2. QUAN TRỌNG NHẤT: Viết lại toàn bộ câu trả lời bằng văn phong tiếng Việt tự nhiên, rành mạch, "
        "cuốn hút như một người bạn chia sẻ, tuyệt đối không dùng các từ ngữ rập khuôn máy móc của AI.\n"
        "3. Trả về định dạng Markdown trực quan, rõ ràng."
    )
    
    prompt_to_master = f"{system_instruction}\n\n[CÂU HỎI CỦA USER]: {user_prompt}\n\n[DỮ LIỆU AI]:\n{combined_context}"
    
    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, lambda: openrouter_client.chat.completions.create(
            model="deepseek/deepseek-chat", 
            messages=[{"role": "user", "content": prompt_to_master}], 
            timeout=10
        ))
        return res.choices[0].message.content
    except Exception as e:
        logging.error(f"Bộ não gộp OpenRouter gặp lỗi: {e}")
        
        # --- CƠ CHẾ PHÒNG THỦ: NẾU DEEPSEEK LỖI, LẤY NGAY GEMINI ĐỂ TRẢ LỜI ---
        for resp in valid_responses:
            if "[Gemini]" in resp:
                return resp.replace("[Gemini]: ", "")
        
        # Cứu hộ cuối cùng: Lấy bất cứ thứ gì còn sống để trả về
        return valid_responses[0].split("]: ", 1)[-1]

# --- SỰ KIỆN BOT TELEGRAM ---
@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    await message.answer(
        f"🧠 **Chào {message.from_user.full_name}! Hệ thống Siêu AI Gộp Tiếng Việt đã kích hoạt!**\n\n"
        f"Hệ thống đã tối ưu hóa, loại bỏ hoàn toàn các API tiếng Anh để tập trung phản hồi tiếng Việt với tốc độ cao nhất.\n\n"
        f"📢 *Phát triển bởi:* [BaoHuyDevs Team](https://t.me/baohuydevs)",
        disable_web_page_preview=True, parse_mode="Markdown"
    )

@dp.message()
async def handle_chat(message: types.Message) -> None:
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    start_time = time.time()
    
    # Chạy song song 2 lõi AI thuần Tiếng Việt
    results = await asyncio.gather(
        fetch_gemini(message.text),
        fetch_openrouter(message.text)
    )
    
    final_answer = await aggregate_responses(message.text, results)
    execution_time = round(time.time() - start_time, 2)
    
    # --- AUTO CHÈN THƯƠNG HIỆU ---
    copyright_footer = (
        f"\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"⚙️ *Hợp nhất dữ liệu trong:* {execution_time}s\n"
        f"🛡️ *Bản quyền thuộc về:* [BaoHuyDevs Team](https://t.me/baohuydevs)"
    )
    final_answer += copyright_footer
    
    try:
        await message.answer(final_answer, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        # Nếu định dạng Markdown bị lỗi ký tự đặc biệt, gửi văn bản thô để chống im lặng
        await message.answer(final_answer, parse_mode=None)

# --- KHỞI CHẠY ĐỒNG BỘ PORT VÀ BOT ---
async def start_server_and_bot():
    bot = Bot(token=TELEGRAM_TOKEN)
    port = int(os.environ.get("PORT", 8080))
    
    # Khởi động Flask giữ Port cho Render ngay lập tức
    from werkzeug.serving import make_server
    server = make_server('0.0.0.0', port, app)
    
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, server.serve_forever)
    print(f"--> [OK] Web Server giữ cổng đã mở thành công trên port: {port}")
    
    print("--- HỆ THỐNG SIÊU AI VIỆT HÓA CHÍNH THỨC HOẠT ĐỘNG ---")
    
    # Xóa sạch webhook kẹt cũ và các tin nhắn dồn ứ trong lúc ngắt kết nối
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(start_server_and_bot())
