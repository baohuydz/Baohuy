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

# ==== KÍCH HOẠT WEB SERVER KEEP ALIVE ====
from keep_alive import keep_alive

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

# --- CÁC HÀM GỌI API ĐỒNG THỜI (ASYNC) ---
async def fetch_mistral(prompt: str) -> str:
    try:
        res = await mistral_client.chat.complete_async(model="mistral-large-latest", messages=[{"role": "user", "content": prompt}])
        return f"[Mistral]: {res.choices[0].message.content}"
    except Exception as e:
        return f"[Mistral Error]: {e}"

async def fetch_openrouter(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        def call():
            return openrouter_client.chat.completions.create(
                model="deepseek/deepseek-chat",
                messages=[{"role": "user", "content": prompt}]
            )
        res = await loop.run_in_executor(None, call)
        return f"[DeepSeek]: {res.choices[0].message.content}"
    except Exception as e:
        return f"[DeepSeek Error]: {e}"

async def fetch_groq(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        def call():
            return groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}]
            )
        res = await loop.run_in_executor(None, call)
        return f"[Llama3]: {res.choices[0].message.content}"
    except Exception as e:
        return f"[Llama3 Error]: {e}"

async def fetch_gemini(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        def call():
            return gemini_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        res = await loop.run_in_executor(None, call)
        return f"[Gemini]: {res.text}"
    except Exception as e:
        return f"[Gemini Error]: {e}"

# --- BỘ NÃO HỢP NHẤT & BIÊN TẬP VĂN PHONG CON NGƯỜI ---
async def aggregate_responses(user_prompt: str, raw_responses: list) -> str:
    combined_context = "\n\n=====\n\n".join(raw_responses)
    
    system_instruction = (
        "Bạn là một Siêu trí tuệ nhân tạo có năng lực thấu cảm và diễn đạt đỉnh cao như một chuyên gia con người thực thụ.\n"
        "Dưới đây là câu trả lời từ 4 mô hình AI khác nhau (Gemini, Llama3, DeepSeek, Mistral) cho cùng một câu hỏi của người dùng.\n"
        "Nhiệm vụ của bạn:\n"
        "1. Đọc phản hồi từ cả 4 nguồn, loại bỏ các thông tin trùng lặp, chọn lọc ra những ý đúng nhất, sâu sắc và giá trị nhất.\n"
        "2. Đúc kết và gộp chúng lại thành một câu trả lời duy nhất hoàn chỉnh.\n"
        "3. QUAN TRỌNG NHẤT: Hãy viết lại bằng văn phong tự nhiên, mượt mà, rành mạch và cuốn hút của con người. "
        "Tuyệt đối KHÔNG sử dụng các từ ngữ rập khuôn máy móc của AI (ví dụ: 'Dưới đây là...', 'Tóm lại...', 'Như vậy...'). Trả lời thẳng vào vấn đề, thể hiện sự thông minh và có cảm xúc phù hợp như hai người bạn đang trò chuyện.\n"
        "4. Sử dụng định dạng Markdown (bôi đậm, gạch đầu dòng) để câu trả lời dễ đọc, trực quan."
    )
    
    prompt_to_master = f"{system_instruction}\n\n[CÂU HỎI CỦA USER]: {user_prompt}\n\n[DỮ LIỆU TỪ 4 AI]:\n{combined_context}"
    
    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, lambda: openrouter_client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=[{"role": "user", "content": prompt_to_master}]
        ))
        return res.choices[0].message.content
    except Exception:
        for resp in raw_responses:
            if "Error" not in resp:
                return resp.split("]: ", 1)[-1]
        return "Xin lỗi, hệ thống siêu trí tuệ đang bận xử lý dữ liệu. Bạn vui lòng thử lại sau nhé!"

# --- XỬ LÝ SỰ KIỆN TELEGRAM ---
@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    user_name = message.from_user.full_name
    await message.answer(
        f"🧠 **Chào {user_name}! Bạn đã kích hoạt Mạng lưới Siêu Trí Tuệ Gộp thành công!**\n\n"
        f"Mọi câu hỏi sẽ được xử lý qua 4 core AI: *Mistral*, *DeepSeek*, *Llama 3*, *Gemini*.\n\n"
        f"📢 *Bot được phát triển và bảo quyền bởi:* @baohuydevs"
    )

@dp.message()
async def handle_chat(message: types.Message) -> None:
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    start_time = time.time()
    
    # Gọi đồng thời các API AI
    results = await asyncio.gather(
        fetch_mistral(message.text),
        fetch_openrouter(message.text),
        fetch_groq(message.text),
        fetch_gemini(message.text)
    )
    
    # Hợp nhất nội dung câu trả lời
    final_answer = await aggregate_responses(message.text, results)
    
    execution_time = round(time.time() - start_time, 2)
    
    # --- PHẦN AUTO CHÈN BẢN QUYỀN VÀ LINK NHÓM ---
    copyright_footer = (
        f"\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        f"⚙️ *Hợp nhất dữ liệu trong:* {execution_time}s\n"
        f"🛡️ *Bản quyền thuộc về:* [BaoHuyDevs Team](https://t.me/baohuydevs)"
    )
    
    # Cộng dồn phần bản quyền vào cuối tin nhắn
    final_answer += copyright_footer
    
    try:
        await message.answer(final_answer, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        # Dự phòng nếu lỗi cú pháp Markdown do AI tạo ra ngoài ý muốn
        await message.answer(final_answer, parse_mode=None)

async def main() -> None:
    keep_alive()
    bot = Bot(token=TELEGRAM_TOKEN)
    print("--- HỆ THỐNG SIÊU TRÍ TUỆ ĐÃ KHỞI ĐỘNG THÀNH CÔNG ---")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
