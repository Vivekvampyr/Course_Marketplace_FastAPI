import os
from google import genai
from google.genai import types
from sqlalchemy.orm import Session
from app.config import settings
from app.models.chat import ChatMessage
from app.models.course import Course

# Initialize client
client = genai.Client(api_key=settings.GEMINI_API_KEY)
MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are a helpful AI assistant for an online course marketplace.
Your job is to:
- Answer questions about courses and learning topics
- Help students understand course content
- Suggest what courses to take based on their goals
- Give clear, concise, beginner-friendly explanations
- Stay focused on education and learning topics
Keep responses short and helpful."""


def build_context(course_id: int, db: Session) -> str:
    if not course_id:
        return ""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return ""
    return f"\nContext: The student is asking about the course titled '{course.title}'. Description: {course.description}"


async def ask_gemini(message: str, course_id: int, user_id: int, db: Session) -> str:
    try:
        context = build_context(course_id, db)
        full_prompt = f"{SYSTEM_PROMPT}{context}\n\nStudent question: {message}"

        response = client.models.generate_content(
            model=MODEL,
            contents=full_prompt
        )
        ai_response = response.text

        # Save to DB
        chat = ChatMessage(
            user_id=user_id,
            message=message,
            response=ai_response,
            course_id=course_id
        )
        db.add(chat)
        db.commit()

        return ai_response

    except Exception as e:
        return f"Error: {str(e)}"


async def ask_gemini_ws(message: str, history: list) -> str:
    """For WebSocket — uses conversation history for context"""
    try:
        # Build contents from history + new message
        contents = []

        for item in history:
            role = item.get("role")       # "user" or "model"
            text = item["parts"][0]["text"]
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=text)]
                )
            )

        # Add current message
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"{SYSTEM_PROMPT}\n\n{message}")]
            )
        )

        response = client.models.generate_content(
            model=MODEL,
            contents=contents
        )
        return response.text

    except Exception as e:
        return f"Error: {str(e)}"