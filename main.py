import asyncio
import logging
import sys
import time
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from google import genai
from groq import Groq
from openai import OpenAI
from mistralai import Mistral

# ==== LIÊN KẾT FILE PHỤ KEEP ALIVE MỚI ====
from keep_alive import app, setup_keep_alive

# --- CẤU HÌNH TOKEN VÀ API KEY ---
TELEGRAM_TOKEN = "6367532329:AAEe9f501-n72-ZKLv4s5I_4O51vgznyXao"
GEMINI_API_KEY = "AIzaSyDD1NhOh6aX58SdnK-3A5MYiQG-AqPDfJM"
GROQ_API_KEY = "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"
OPENROUTER_API_KEY = "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"
MISTRAL_API_KEY = "KL9zhAQXsjTSClDM1aLs1nvWXs5k6sP1"

# --- KHỞI TẠO CÁC CỔNG AI ---
mistral_client = Mistral(api_key=MISTRAL_API_KEY)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)
openrouter_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

dp = Dispatcher()

# --- CÁC HÀM GỌI API AN TOÀN ---
async def fetch_mistral(prompt: str) -> str:
    try:
        res = await mistral_client.chat.complete_async(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}], timeout=8)
        return f"[Mistral]: {res.choices[0].message.content}"
    except Exception as e:
        logging.warning(f"Mistral API không phản hồi: {e}")
        return ""

async def fetch_openrouter(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        def call():
            return openrouter_client.chat.completions.create(model="deepseek/deepseek-chat", messages=[{"role": "user", "content": prompt}], timeout=8)
        res = await loop.run_in_executor(None, call)
        return f"[DeepSeek]: {res.choices[0].message.content}"
    except Exception as e:
        logging.warning(f"OpenRouter API không phản hồi: {e}")
        return ""

async def fetch_groq(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        def call():
            return groq_client.chat.completions.create(model="llama3-70b-8192", messages=[{"role": "user", "content": prompt}], timeout=8)
        res = await loop.run_in_executor(None, call)
        return f"[Llama3]: {res.choices[0].message.content}"
    except Exception as e:
        logging.warning(f"Groq API không phản hồi: {e}")
        return ""

async def fetch_gemini(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        def call():
            return gemini_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        res = await loop.run_in_executor(None, call)
        return f"[Gemini]: {res.text}"
    except Exception as e:
        logging.warning(f"Gemini API không phản hồi: {e}")
        return ""

# --- BỘ NÃO HỢP NHẤT ---
async def aggregate_responses(user_prompt: str, raw_responses: list) -> str:
    valid_responses = [resp for resp in raw_responses if resp.strip()]
    if not valid_responses:
        return "Hiện tại hệ thống AI đang bảo trì core dữ liệu. Bạn vui lòng thử lại sau nhé!"
        
    combined_context = "\n\n=====\n\n".join(valid_responses)
    system_instruction = (
        "Bạn là một Siêu trí tuệ nhân tạo có năng lực thấu cảm và diễn đạt đỉnh cao như một chuyên gia con người thực thụ.\n"
        "Dưới đây là các câu trả lời từ các mô hình AI cho câu hỏi của người dùng.\n"
        "Nhiệm vụ của bạn:\n"
        "1. Lọc dữ liệu thô, loại bỏ thông tin trùng lặp, giữ lại ý sâu sắc nhất.\n"
        "2. Đúc kết thành một câu trả lời duy nhất hoàn chỉnh.\n"
        "3. QUAN TRỌNG NHẤT: Viết lại bằng văn phong tự nhiên, rành mạch, cuốn hút của con người, không rập khuôn máy móc AI.\n"
        "4. Sử dụng định dạng Markdown đẹp mắt."
    )
    prompt_to_master = f"{system_instruction}\n\n[CÂU HỎI CỦA USER]: {user_prompt}\n\n[DỮ LIỆU TỪ CÁC AI]:\n{combined_context}"
    
    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, lambda: openrouter_client.chat.completions.create(model="deepseek/deepseek-chat", messages=[{"role": "user", "content": prompt_to_master}], timeout=10))
        return res.choices[0].message.content
    except Exception:
        return valid_responses[0].split("]: ", 1)[-1]

# --- SỰ KIỆN TELEGRAM ---
@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    user_name = message.from_user.full_name
    await message.answer(
        f"🧠 **Chào {user_name}! Bạn đã kích hoạt Mạng lưới Siêu Trí Tuệ Gộp thành công!**\n\n"
        f"📢 *Bot được phát triển bởi:* @baohuydevs"
    )

@dp.message()
async def handle_chat(message: types.Message) -> None:
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    start_time = time.time()
    
    results = await asyncio.gather(fetch_mistral(message.text), fetch_openrouter(message.text), fetch_groq(message.text), fetch_gemini(message.text))
    final_answer = await aggregate_responses(message.text, results)
    execution_time = round(time.time() - start_time, 2)
    
    copyright_footer = (
        f"\n\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"⚙️ *Hợp nhất dữ liệu trong:* {execution_time}s\n"
        f"🛡️ *Bản quyền thuộc về:* [BaoHuyDevs Team](https://t.me/baohuydevs)"
    )
    final_answer += copyright_footer
    
    try:
        await message.answer(final_answer, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        await message.answer(final_answer, parse_mode=None)

# --- CHẠY SONG SONG WEB SERVER VÀ BOT TELEGRAM TRÊN CÙNG EVENT LOOP ---
async def start_web_and_bot():
    bot = Bot(token=TELEGRAM_TOKEN)
    
    # 1. Cấu hình cổng mạng động phục vụ Render trước
    bind_port = setup_keep_alive()
    
    # Kích hoạt Web Server Flask chạy bất đồng bộ ngay bên trong Event Loop của Bot
    from werkzeug.serving import make_server
    server = make_server('0.0.0.0', bind_port, app)
    
    loop = asyncio.get_event_loop()
    # Ném tác vụ giữ cổng Flask chạy ngầm vĩnh viễn trên luồng xử lý chính của hệ thống
    loop.run_in_executor(None, server.serve_forever)
    print(f"--> [OK] Web Server đã mở thành công trên cổng: {bind_port}")
    
    # 2. Bắt đầu kích hoạt Polling cho Telegram Bot ngay sau đó
    print("--- HỆ THỐNG SIÊU BOT BAOHUYDEVS ĐANG TRỰC TUYẾN 24/7 ---")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(start_web_and_bot())
