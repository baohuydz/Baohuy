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

# --- CẤU HÌNH TOKEN VÀ API KEY CHÍNH THỨC ---
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

# --- CÁC HÀM GỌI API AN TOÀN (Nếu lỗi tự động bỏ qua để không sập bot) ---
async def fetch_mistral(prompt: str) -> str:
    try:
        res = await mistral_client.chat.complete_async(
            model="mistral-large-latest", 
            messages=[{"role": "user", "content": prompt}], 
            timeout=8
        )
        return f"[Mistral]: {res.choices[0].message.content}"
    except Exception as e:
        logging.warning(f"Mistral API gặp sự cố hoặc bị chặn: {e}")
        return ""

async def fetch_openrouter(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        def call():
            return openrouter_client.chat.completions.create(
                model="deepseek/deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                timeout=8
            )
        res = await loop.run_in_executor(None, call)
        return f"[DeepSeek]: {res.choices[0].message.content}"
    except Exception as e:
        logging.warning(f"OpenRouter API gặp sự cố hoặc bị chặn: {e}")
        return ""

async def fetch_groq(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        def call():
            return groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                timeout=8
            )
        res = await loop.run_in_executor(None, call)
        return f"[Llama3]: {res.choices[0].message.content}"
    except Exception as e:
        logging.warning(f"Groq API gặp sự cố hoặc bị chặn: {e}")
        return ""

async def fetch_gemini(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        def call():
            return gemini_client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        res = await loop.run_in_executor(None, call)
        return f"[Gemini]: {res.text}"
    except Exception as e:
        logging.warning(f"Gemini API gặp sự cố hoặc bị chặn: {e}")
        return ""

# --- BỘ NÃO HỢP NHẤT & BIÊN TẬP VĂN PHONG CON NGƯỜI ---
async def aggregate_responses(user_prompt: str, raw_responses: list) -> str:
    # Lọc bỏ hoàn toàn các phản hồi trống từ các AI bị lỗi/chặn
    valid_responses = [resp for resp in raw_responses if resp.strip()]
    
    if not valid_responses:
        return "Hiện tại tất cả các cổng kết nối dữ liệu AI đang bảo trì. Bạn vui lòng thử lại sau ít phút nhé!"
        
    combined_context = "\n\n=====\n\n".join(valid_responses)
    
    system_instruction = (
        "Bạn là một Siêu trí tuệ nhân tạo có năng lực thấu cảm và diễn đạt đỉnh cao như một chuyên gia con người thực thụ.\n"
        "Dưới đây là các câu trả lời từ các mô hình AI cho câu hỏi của người dùng.\n"
        "Nhiệm vụ của bạn:\n"
        "1. Đọc kỹ các dữ liệu thô, loại bỏ thông tin trùng lặp, giữ lại những ý đúng và sâu sắc nhất.\n"
        "2. Đúc kết thành một câu trả lời duy nhất hoàn chỉnh.\n"
        "3. QUAN TRỌNG NHẤT: Viết lại bằng văn phong tự nhiên, rành mạch, cuốn hút của con người. "
        "Tuyệt đối KHÔNG dùng các từ ngữ rập khuôn máy móc của AI (ví dụ: 'Dưới đây là...', 'Tóm lại...', 'Như vậy...'). Trả lời thẳng vào vấn đề, có cảm xúc như một người bạn.\n"
        "4. Sử dụng định dạng Markdown đẹp mắt."
    )
    
    prompt_to_master = f"{system_instruction}\n\n[CÂU HỎI CỦA USER]: {user_prompt}\n\n[DỮ LIỆU TỪ CÁC AI]:\n{combined_context}"
    
    try:
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, lambda: openrouter_client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=[{"role": "user", "content": prompt_to_master}],
            timeout=10
        ))
        return res.choices[0].message.content
    except Exception:
        # Nếu bộ não gộp chính gặp lỗi, lấy kết quả của AI đầu tiên còn sống để trả về luôn
        return valid_responses[0].split("]: ", 1)[-1]

# --- XỬ LÝ SỰ KIỆN TELEGRAM ---
@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    user_name = message.from_user.full_name
    await message.answer(
        f"🧠 **Chào {user_name}! Bạn đã kích hoạt Mạng lưới Siêu Trí Tuệ Gộp thành công!**\n\n"
        f"Hệ thống tự động đồng bộ và tối ưu hóa dữ liệu từ nhiều nguồn AI khác nhau để phản hồi bằng giọng văn tự nhiên nhất.\n\n"
        f"📢 *Bot được phát triển bởi:* @baohuydevs"
    )

@dp.message()
async def handle_chat(message: types.Message) -> None:
    # Hiển thị hiệu ứng "bot đang gõ..." trên Telegram
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    start_time = time.time()
    
    # Kích hoạt chạy song song đồng thời cả 4 core AI
    results = await asyncio.gather(
        fetch_mistral(message.text),
        fetch_openrouter(message.text),
        fetch_groq(message.text),
        fetch_gemini(message.text)
    )
    
    # Hợp nhất nội dung từ những cổng hoạt động tốt
    final_answer = await aggregate_responses(message.text, results)
    execution_time = round(time.time() - start_time, 2)
    
    # --- PHẦN AUTO CHÈN BẢN QUYỀN VÀ LINK NHÓM ---
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
        # Dự phòng nếu chuỗi trả về chứa kí tự Markdown lỗi, gửi dạng văn bản thô
        await message.answer(final_answer, parse_mode=None)

async def main() -> None:
    # Khởi động Web Server Keep Alive nhận cổng động của Render
    keep_alive()
    
    bot = Bot(token=TELEGRAM_TOKEN)
    print("--- HỆ THỐNG PHÒNG THỦ VÀ ĐỒNG BỘ SIÊU AI ĐÃ KHỞI ĐỘNG CHÍNH THỨC ---")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
