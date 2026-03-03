from pyexpat import model
import shutil
import os
import re
from fastapi import FastAPI, Depends, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
import google.generativeai as genai
import datetime

GOOGLE_API_KEY = "YOUR_API_KEY"
genai.configure(api_key=GOOGLE_API_KEY)

german_tutor_rules = """
You are an encouraging German language professor. 
Your student is at an beginner/intermediate/advanced university level (A1 to C2 level).
Follow these strict rules:
1. ALWAYS reply in German with english translations.
2. If the user makes a grammatical or spelling mistake in their German, correct it gently before answering their question.
3. Use vocabulary appropriate for a university student. 
4. Be especially helpful if the user asks for help with creative writing.
5. Keep your responses concise and conversational.
6. ALWAYS be cheerful.
"""

gemini_engine = genai.GenerativeModel(
    model_name='gemini-2.5-flash-lite'
)

DATABASE_URL = "sqlite+aiosqlite:///database.db"
engine = create_async_engine(DATABASE_URL, echo=False)

async def get_session():
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    session_id: str
    user_input: str
    bot_response: str
    timestamp: str

class MistakeLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    topic: str
    timestamp: str

app = FastAPI()

@app.get("/")
async def serve_home():
    with open("index.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read())


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

@app.get("/get_sessions")
async def get_sessions(db: AsyncSession = Depends(get_session)):
    statement = select(Message.session_id).distinct()
    result = await db.execute(statement)
    return result.scalars().all()

@app.get("/get_history")
async def get_history(session_id: str, db: AsyncSession = Depends(get_session)):
    statement = select(Message).where(Message.session_id == session_id).order_by(Message.id)
    result = await db.execute(statement)
    return result.scalars().all()

@app.delete("/delete_session")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_session)):
    statement = select(Message).where(Message.session_id == session_id)
    result = await db.execute(statement)
    messages = result.scalars().all()
    for msg in messages:
        await db.delete(msg)
    await db.commit()
    return {"status": "deleted"}

@app.get("/generate_title")
async def generate_title(prompt: str):
    try:
        title_model = genai.GenerativeModel('gemini-2.5-flash')
        strict_prompt = f"CRITICAL RULE: Return ONLY a 2 to 4 word German title for the following text. Do NOT correct grammar. Do NOT give explanations. Just the 3 words. Text: {prompt}"
        
        response = await title_model.generate_content_async(strict_prompt)
        clean_title = response.text.strip()
        
        if len(clean_title) > 30:
            clean_title = clean_title[:30] + "..."
            
        return {"title": clean_title}
    except:
        return {"title": "Neues Gespräch"}

@app.post("/upload")
async def upload_document(session_id: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_session)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        uploaded_file = genai.upload_file(temp_path)
        file_receipt = uploaded_file.name 
    except Exception as e:
        os.remove(temp_path)
        return {"error": f"Upload failed: {str(e)}"}
        
    os.remove(temp_path)
    
    user_prompt = f"[DOCUMENT_RECEIPT: {file_receipt}] Ich habe ein Dokument namens '{file.filename}' hochgeladen. Bitte lies es."
    bot_acknowledgement = f"Verstanden! Ich habe das Dokument '{file.filename}' gelesen. Wie kann ich dir dabei helfen?"
    
    chat_log = Message(
        session_id=session_id, user_input=user_prompt,
        bot_response=bot_acknowledgement, timestamp=str(datetime.datetime.now())
    )
    db.add(chat_log)
    await db.commit()
    
    return {"status": "success", "filename": file.filename}

@app.post("/chat")
async def chat(session_id: str, user_message: str, proficiency: str = "B1", db: AsyncSession = Depends(get_session)):
    
    weakness_stmt = select(MistakeLog.topic).distinct()
    weakness_result = await db.execute(weakness_stmt)
    known_weaknesses = weakness_result.scalars().all()
    weakness_str = ", ".join(known_weaknesses) if known_weaknesses else "Keine (None identified yet)."

    statement = select(Message).where(Message.session_id == session_id).order_by(Message.id)
    result = await db.execute(statement)
    old_messages = result.scalars().all()

    prompt_parts = []
    active_file = None
    chat_transcript = ""

    dynamic_rule = (
        f"You are an encouraging and cheerful university-level German professor. "
        f"The student is practicing at the {proficiency} CEFR level. "
        f"KNOWN STUDENT WEAKNESSES: {weakness_str}. Pay special attention to testing them on these. "
        f"CRITICAL RULE: ALWAYS reply in german with english translations."
        f"CRITICAL RULE: If the student makes a fundamental grammar error in their prompt, you MUST append a tag at the VERY END of your response in this exact format: [WEAKNESS: Topic]. For example: [WEAKNESS: Dativ Case] or [WEAKNESS: Word Order]. Do not say the tag out loud."
    )
    prompt_parts.append(dynamic_rule)

    for msg in old_messages:
        if "[DOCUMENT_RECEIPT:" in msg.user_input:
            start = msg.user_input.find("[DOCUMENT_RECEIPT:") + 18
            end = msg.user_input.find("]", start)
            file_id = msg.user_input[start:end].strip()
            clean_text = msg.user_input[end+1:].strip()
            try:
                active_file = genai.get_file(file_id)
                chat_transcript += f"Student: {clean_text}\n"
            except Exception:
                chat_transcript += f"Student: (Dokument abgelaufen) {clean_text}\n"
        else:
            chat_transcript += f"Student: {msg.user_input}\n"

        chat_transcript += f"Professor: {msg.bot_response}\n\n"

    if active_file:
        if active_file.state.name == "PROCESSING":
            return {"response": "Ich verarbeite dieses riesige Buch noch. Das dauert bei großen Dateien etwa 1-2 Minuten. Bitte versuche es gleich noch einmal!"}
        elif active_file.state.name == "FAILED":
            return {"response": "Entschuldigung, Google konnte das PDF nicht lesen. Es ist möglicherweise beschädigt."}
        prompt_parts.append(active_file)

    prompt_parts.append(f"Here is our conversation history:\n{chat_transcript}")
    prompt_parts.append(f"Here is my new question: {user_message}")

    try:
        response = await gemini_engine.generate_content_async(prompt_parts)
        ai_reply = response.text
    except Exception as e:
        print(f"--- GOOGLE ERROR: {e} ---")
        ai_reply = "Sorry, I am having trouble connecting to Google Gemini."

    match = re.search(r'\[WEAKNESS:\s*(.*?)\]', ai_reply)
    if match:
        mistake_topic = match.group(1).strip()
        
        ai_reply = re.sub(r'\[WEAKNESS:\s*(.*?)\]', '', ai_reply).strip()

        new_mistake = MistakeLog(topic=mistake_topic, timestamp=str(datetime.datetime.now()))
        db.add(new_mistake)

    chat_log = Message(
        session_id=session_id, user_input=user_message,
        bot_response=ai_reply, timestamp=str(datetime.datetime.now())
    )
    db.add(chat_log)
    await db.commit()
    
    return {"response": ai_reply}