import asyncio
import logging
import sys
import time
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from google import genai
from groq import Groq
from openai import OpenAI
import httpx

# ==== KHỞI TẠO WEB SERVER KHÔNG CẦN THỜI GIAN CHỜ ====
from keep_alive import app

# --- CẤU HÌNH TOKEN VÀ API KEY ---
TELEGRAM_TOKEN = "6367532329:AAEe9f501-n72-ZKLv4s5I_4O51vgznyXao"
GEMINI_API_KEY = "AIzaSyDD1NhOh6aX58SdnK-3A5MYiQG-AqPDfJM"
GROQ_API_KEY = "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"
OPENROUTER_API_KEY = "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"
MISTRAL_API_KEY = "KL9zhAQXsjTSClDM1aLs1nvWXs5k6sP1"

# --- KHỞI TẠO CÁC CỔNG AI CHÍNH ---
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)
openrouter_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

dp = Dispatcher()

# --- HÀM GỌI MISTRAL QUA HTTPX TRỰC TIẾP (FIX TRIỆT ĐỂ IMPORT ERROR) ---
async def fetch_mistral(prompt: str) -> str:
    try:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MISTRAL_API_KEY}"
        }
        payload = {
            "model": "mistral-large-latest",
            "messages": [{"role": "user", "content": prompt}]
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(url, json=payload, headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                return f"[Mistral]: {data['choices'][0]['message']['content']}"
            return ""
    except Exception as e:
        logging.warning(f"Mistral API (HTTPX) không phản hồi: {e}")
        return ""

async def fetch_openrouter(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, lambda: openrouter_client.chat.completions.create(
            model="deepseek/deepseek-chat", messages=[{"role": "user", "content": prompt}], timeout=8
        ))
        return f"[DeepSeek]: {res.choices[0].message.content}"
    except Exception:
        return ""

async def fetch_groq(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, lambda: groq_client.chat.completions.create(
            model="llama3-70b-8192", messages=[{"role": "user", "content": prompt}], timeout=8
        ))
        return f"[Llama3]: {res.choices[0].message.content}"
    except Exception:
        return ""

async def fetch_gemini(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, lambda: gemini_client.models.generate_content(model='gemini-1.5-flash', contents=prompt))
        return f"[Gemini]: {res.text}"
    except Exception:
        return ""

# --- BỘ NÃO HỢP NHẤT DỮ LIỆU ---
async def aggregate_responses(user_prompt: str, raw_responses: list) -> str:
    valid_responses = [resp for resp in raw_responses if resp.strip()]
    if not valid_responses:
        return "Hệ thống đang bảo trì core dữ liệu. Bạn vui lòng thử lại sau nhé!"
        
    combined_context = "\n\n=====\n\n".join(valid_responses)
    system_instruction = (
        "Bạn là một Siêu trí tuệ nhân tạo có năng lực thấu cảm diễn đạt như con người.\n"
        "Hãy tổng hợp dữ liệu thô bên dưới thành câu trả lời hoàn chỉnh, viết tự nhiên, "
        "trực diện vấn đề, thân thiện. Sử dụng định dạng Markdown đẹp."
    )
    prompt_to_master = f"{system_instruction}\n\n[USER]: {user_prompt}\n\n[DATA]:\n{combined_context}"
    
    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, lambda: openrouter_client.chat.completions.create(
            model="deepseek/deepseek-chat", messages=[{"role": "user", "content": prompt_to_master}], timeout=10
        ))
        return res.choices[0].message.content
    except Exception:
        return valid_responses[0].split("]: ", 1)[-1]

# --- SỰ KIỆN BOT ---
@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    await message.answer(
        f"🧠 **Chào {message.from_user.full_name}! Hệ thống Siêu AI Gộp đã kích hoạt!**\n\n"
        f"📢 *Phát triển bởi:* [BaoHuyDevs Team](https://t.me/baohuydevs)",
        disable_web_page_preview=True, parse_mode="Markdown"
    )

@dp.message()
async def handle_chat(message: types.Message) -> None:
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    start_time = time.time()
    
    results = await asyncio.gather(fetch_mistral(message.text), fetch_openrouter(message.text), fetch_groq(message.text), fetch_gemini(message.text))
    final_answer = await aggregate_responses(message.text, results)
    
    execution_time = round(time.time() - start_time, 2)
    final_answer += f"\n\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n⚙️ *Hợp nhất dữ liệu trong:* {execution_time}s\n🛡️ *Bản quyền thuộc về:* [BaoHuyDevs Team](https://t.me/baohuydevs)"
    
    try:
        await message.answer(final_answer, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        await message.answer(final_answer, parse_mode=None)

# --- CHẠY KHỞI ĐỘNG LIÊN KẾT PORT ---
async def start_server_and_bot():
    bot = Bot(token=TELEGRAM_TOKEN)
    port = int(os.environ.get("PORT", 8080))
    
    # Ép Flask chạy trên luồng phụ ngay lập tức để chiếm Port phục vụ Render scan
    from werkzeug.serving import make_server
    server = make_server('0.0.0.0', port, app)
    
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, server.serve_forever)
    print(f"--> [OK] Đã mở cổng giữ mạng: {port}")
    
    print("--- KHỞI ĐỘNG HỆ THỐNG BAOHUYDEVS AN TOÀN TUYỆT ĐỐI ---")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(start_server_and_bot())
