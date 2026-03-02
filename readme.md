# 🇩🇪 Klartext: Adaptive AI German Tutor

A full-stack, AI-powered web application built to simulate an encouraging, university-level German professor. Unlike standard chatbots, Klartext features persistent automated weakness tracking, real-time voice integration, and the ability to natively ingest and analyze massive textbook PDFs.


## 🚀 Key Features

* **🧠 Automated Weakness Profiling (Ghost Tagging):** The AI silently analyzes the user's grammar mistakes (e.g., mixing up *Akkusativ* and *Dativ*) and attaches hidden tags to its responses. The FastAPI backend intercepts these tags, logs them in an SQLite database, and dynamically injects them into future system prompts to actively test the user on their specific weak points.
* **📚 Smart Document Analysis:** Capable of reading massive, multi-page German PDFs (like the *Kursbuch*). It uses a custom Context Flattening architecture to bypass standard SDK memory limits for large file sizes.
* **🎙️ Real-time Voice Chat:** Integrates the browser's native Web Speech API for seamless German speech-to-text input and text-to-speech pronunciation practice.
* **🎚️ Dynamic Proficiency Leveling:** Users can switch their target CEFR level (A1 - C1) on the fly. The backend instantly rewrites the AI's core instructions to match the selected vocabulary and grammatical complexity.
* **💾 Persistent Memory:** Uses an SQLite database (`SQLModel`) to store chat histories, manage multiple concurrent conversation sessions, and auto-generate context-aware German titles for the sidebar.
* **✨ Modern UI:** Built from scratch featuring a sleek dark-mode "glassmorphism" design, markdown text rendering, and smooth CSS animations without relying on heavy frontend frameworks.

## 🛠️ Tech Stack

* **Backend:** Python, FastAPI, Uvicorn
* **Database:** SQLite, SQLModel (SQLAlchemy)
* **AI Integration:** Google GenAI SDK (Gemini 2.5 Flash-Lite)
* **Frontend:** HTML5, CSS3, Vanilla JavaScript, Bootstrap Icons

## ⚙️ How to Run Locally

**1. Clone the repository:**
```bash
git clone [https://github.com/nayan-ng/klartext-ai-tutor.git](https://github.com/nayan-ng/klartext-ai-tutor.git)
cd klartext-ai-tutor
