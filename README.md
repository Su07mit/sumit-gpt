# 🧠 Sumit GPT

<p align="center">
  <strong>A personal AI assistant with Offline, Online Search, Deep Research, Voice & Vision capabilities.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.0.3-black?style=for-the-badge&logo=flask" alt="Flask">
  <img src="https://img.shields.io/badge/LLM-Qwen%202.5%20VL-purple?style=for-the-badge" alt="Qwen">
  <img src="https://img.shields.io/badge/AI-Local%20%26%20Private-success?style=for-the-badge" alt="AI">
  <img src="https://img.shields.io/badge/Status-2026%20Edition-8A2BE2?style=for-the-badge" alt="Status">
</p>

---

## ✨ Overview

**Sumit GPT** is a locally hosted AI assistant designed to provide a modern ChatGPT-style experience while supporting both **offline AI conversations** and **online information retrieval**.

The application combines a custom Flask backend with a futuristic web interface and a locally running **Qwen 2.5 VL 3B** model.

Instead of relying entirely on cloud AI services, Sumit GPT is designed around a local-first workflow, giving users more control over their conversations and data.

> **Ask me anything — offline or online.**

---

## 🖥️ Dashboard

<p align="center">
  <img src="screenshots/dashboard.png" alt="Sumit GPT Dashboard" width="100%">
</p>

### 🎨 Interface Highlights

- 🌌 Modern dark/purple glassmorphism interface
- 💬 ChatGPT-style conversation experience
- 🧠 Local AI model indicator
- 🌐 Offline / Online mode switching
- 🔬 Deep Research mode
- 🎙️ Voice input
- 🖼️ Image upload & analysis
- ⚡ Animated responses and thinking indicators
- 📱 Responsive layout for smaller screens

---

## 🚀 Features

### 🧠 Local AI

Sumit GPT uses:

**Qwen 2.5 VL 3B**

for local AI inference.

This allows the application to communicate with a locally running model rather than sending every conversation directly to a hosted AI provider.

---

### 📴 Offline Mode

Offline mode allows the assistant to answer using the locally available model.

Useful when you want:

- Local AI interaction
- Reduced dependency on internet services
- Private experimentation
- AI development without a cloud API

---

### 🌐 Online Search Mode

Switch to **Online Mode** when you need information retrieved from the web.

The application currently combines information from sources including:

- DuckDuckGo
- Wikipedia

Search results are processed before being passed to the AI assistant.

---

### 🔬 Deep Research

Deep Research mode is designed for more comprehensive questions.

Instead of simply returning a short answer, the system attempts to:

- Gather additional information
- Extract relevant facts
- Analyse search results
- Connect information together
- Produce a more detailed response

---

### 🎙️ Voice Input

Sumit GPT supports browser-based voice input using the Web Speech API.

You can:

1. Press the microphone button
2. Speak your question
3. Convert your speech into text
4. Send the question to the AI

> Browser microphone permissions may be required.

---

### 🖼️ Vision & Image Analysis

The interface supports image uploads and is designed to work with the vision capabilities of the Qwen model.

You can upload an image directly through the chat interface and provide a question or instruction about it.

---

### 💾 Search Caching

Search results are cached locally to reduce unnecessary repeated requests.

The application stores cached search information and applies an expiry period before retrieving fresh results.

This helps reduce redundant network requests during repeated searches.

---

### 💻 Developer-Friendly Chat Interface

The interface includes several quality-of-life features:

- Code blocks
- Copy-code buttons
- Message animations
- Thinking indicators
- Image previews
- Responsive sidebar
- Mode indicators
- New chat functionality
- Markdown-style response formatting

---

# 🏗️ Architecture

```text
                    ┌──────────────────────────┐
                    │       Sumit GPT UI       │
                    │                          │
                    │  Chat • Voice • Vision   │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │       Flask Backend       │
                    │          app.py            │
                    └────────────┬─────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │ Offline Mode │  │ Online Search│  │ Deep Research│
        └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
               │                 │                 │
               ▼                 ▼                 ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │ Qwen 2.5 VL  │  │ DuckDuckGo   │  │ Search Data  │
        │     3B       │  │  Wikipedia   │  │ + Analysis   │
        └──────────────┘  └──────────────┘  └──────────────┘
