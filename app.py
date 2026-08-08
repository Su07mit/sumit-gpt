from flask import Flask, request, Response, render_template_string, jsonify
import requests
import json
import webbrowser
import threading
import time
import re
import os
import pickle
from datetime import datetime, timedelta
import urllib.parse

app = Flask(__name__)

# Configuration
MODEL_NAME = "qwen2.5vl:3b"
OLLAMA_URL = "http://localhost:11434/api/chat"
CACHE_FILE = "search_cache.pkl"
CACHE_EXPIRY = timedelta(days=1)

print(f"🤖 Using model: {MODEL_NAME}")
print(f"📅 System date: {datetime.now().strftime('%Y-%m-%d')}")

# SUPER ADVANCED SYSTEM PROMPTS
SYSTEM_PROMPT_OFFLINE = """You are Sumit GPT, an AI assistant.
Answer based on your training knowledge.
Be honest about your limitations."""

SYSTEM_PROMPT_ONLINE = """CRITICAL INSTRUCTION: You MUST use the provided search results to answer.
You are Sumit GPT with access to CURRENT web data.

RULES:
1. READ the search results CAREFULLY
2. Use ONLY the information from search results
3. Give SPECIFIC names, dates, and facts from the search results
4. If search results say something, repeat it directly
5. NEVER say "I don't have real-time access" or "my last update was"
6. You ARE updated to 2026 with the search results

Search results provided:
{search_results}

Question: {question}

Answer directly using the search results above. Be specific and detailed."""

SYSTEM_PROMPT_DEEP = """DEEP RESEARCH MODE: Provide comprehensive analysis using search results.

You are Sumit GPT with access to extensive search data.
Analyze the search results thoroughly and provide:
- Specific facts and figures
- Names and dates
- Connections between information
- Detailed insights

Search results:
{search_results}

Question: {question}

Provide a comprehensive, well-structured response using ONLY the search results."""

# Cache system
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as f:
                return pickle.load(f)
        except:
            return {}
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(cache, f)
    except:
        pass

search_cache = load_cache()

def get_cached_search(query):
    if query in search_cache:
        entry = search_cache[query]
        if datetime.now() - entry['timestamp'] < CACHE_EXPIRY:
            return entry['results']
    return None

def cache_search_results(query, results):
    search_cache[query] = {
        'timestamp': datetime.now(),
        'results': results
    }
    save_cache(search_cache)

def extract_key_info(text):
    """Extract key information from search results"""
    if not text:
        return ""
    
    sentences = re.split(r'[.!?]+', text)
    key_sentences = []
    
    keywords = ['prime minister', 'president', 'minister', 'government', 'election', 
                'appointed', 'served', 'current', 'since', 'leader', 'chief', 'head',
                'ceo', 'founder', 'director', 'chairman', 'secretary', 'ambassador']
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) > 20:
            for keyword in keywords:
                if keyword.lower() in sentence.lower():
                    key_sentences.append(sentence)
                    break
    
    if key_sentences:
        return ". ".join(key_sentences[:5])
    
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    return ". ".join(sentences[:3])

def web_search(query, deep=False):
    """Enhanced web search with better result extraction"""
    cached = get_cached_search(query)
    if cached:
        print(f"📦 Using cached results")
        return cached
    
    print(f"🔍 {'Deep ' if deep else ''}Searching: {query[:50]}...")
    
    try:
        clean_query = query.strip()
        all_results = []
        
        # 1. DuckDuckGo API
        ddg_url = f"https://api.duckduckgo.com/?q={clean_query}&format=json&no_html=1&skip_disambig=1"
        try:
            ddg_response = requests.get(ddg_url, timeout=10)
            if ddg_response.status_code == 200:
                ddg_data = ddg_response.json()
                
                if ddg_data.get('Abstract'):
                    all_results.append(ddg_data['Abstract'])
                if ddg_data.get('Answer'):
                    all_results.append(ddg_data['Answer'])
                if ddg_data.get('Definition'):
                    all_results.append(ddg_data['Definition'])
                
                if ddg_data.get('Infobox'):
                    infobox = ddg_data['Infobox']
                    if isinstance(infobox, dict):
                        for key, value in infobox.items():
                            if isinstance(value, str) and len(value) > 10:
                                all_results.append(f"{key}: {value}")
        except Exception as e:
            print(f"⚠️ DDG error: {e}")
        
        # 2. Wikipedia API
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_query.replace(' ', '_')}"
        try:
            wiki_response = requests.get(wiki_url, timeout=10)
            if wiki_response.status_code == 200:
                wiki_data = wiki_response.json()
                if wiki_data.get('extract'):
                    all_results.append(wiki_data['extract'])
        except Exception as e:
            print(f"⚠️ Wiki error: {e}")
        
        # 3. Wikipedia search
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={clean_query}&format=json&limit=5"
        try:
            search_response = requests.get(search_url, timeout=10)
            if search_response.status_code == 200:
                search_data = search_response.json()
                for result in search_data.get('query', {}).get('search', [])[:3]:
                    if result.get('snippet'):
                        snippet = re.sub(r'<[^>]+>', '', result['snippet'])
                        if len(snippet) > 30:
                            all_results.append(snippet)
        except Exception as e:
            print(f"⚠️ Wiki search error: {e}")
        
        if all_results:
            combined = " ".join(all_results)
            combined = re.sub(r'\s+', ' ', combined).strip()
            key_info = extract_key_info(combined)
            
            final_result = key_info if key_info and len(key_info) > 50 else combined[:1500]
            
            cache_search_results(query, final_result)
            return final_result
        
        return None
    except Exception as e:
        print(f"❌ Search error: {e}")
        return None

# HTML Template with Sumit GPT branding
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sumit GPT</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Poppins', sans-serif;
            background: #0d0d0d;
            color: #f0f0f0;
            height: 100vh;
            overflow: hidden;
        }
        
        .app {
            display: flex;
            height: 100vh;
            background: radial-gradient(circle at 20% 30%, #0f0a1a, #1a0a2e, #0d0d0d);
            background-size: 300% 300%;
            animation: gradientShift 15s ease infinite alternate;
        }
        
        @keyframes gradientShift {
            0% { background-position: 0% 0%; }
            50% { background-position: 100% 60%; }
            100% { background-position: 0% 100%; }
        }
        
        .sidebar {
            width: 280px;
            background: rgba(15, 10, 30, 0.7);
            backdrop-filter: blur(16px) saturate(180%);
            border-right: 1px solid rgba(167, 139, 250, 0.08);
            display: flex;
            flex-direction: column;
            padding: 24px 16px;
            flex-shrink: 0;
            box-shadow: 4px 0 40px rgba(0,0,0,0.6);
            z-index: 2;
        }
        
        .sidebar-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 28px;
        }
        
        .logo-icon {
            font-size: 32px;
            color: #a78bfa;
            filter: drop-shadow(0 0 12px #7c3aed88);
            animation: pulseGlow 3s infinite;
        }
        
        @keyframes pulseGlow {
            0% { filter: drop-shadow(0 0 4px #7c3aed88); }
            50% { filter: drop-shadow(0 0 24px #a78bfacc); }
            100% { filter: drop-shadow(0 0 4px #7c3aed88); }
        }
        
        .logo-text {
            font-weight: 800;
            font-size: 22px;
            background: linear-gradient(135deg, #c4b5fd, #a78bfa, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .logo-year {
            font-size: 12px;
            font-weight: 600;
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
            padding: 2px 10px;
            border-radius: 20px;
            border: 1px solid rgba(16, 185, 129, 0.2);
            -webkit-text-fill-color: #34d399;
        }
        
        .new-chat-btn {
            background: rgba(167, 139, 250, 0.08);
            border: 1px solid rgba(167, 139, 250, 0.15);
            color: #f0f0f0;
            padding: 12px 16px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: 0.3s;
            margin-bottom: 16px;
        }
        
        .new-chat-btn:hover {
            background: rgba(167, 139, 250, 0.16);
            border-color: #a78bfa66;
            transform: translateY(-1px);
            box-shadow: 0 0 30px #7c3aed22;
        }
        
        .mode-section {
            margin-bottom: 16px;
            padding: 12px;
            background: rgba(255,255,255,0.03);
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.04);
        }
        
        .mode-label {
            font-size: 11px;
            color: #8e8ea0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            display: block;
        }
        
        .mode-toggle {
            display: flex;
            gap: 6px;
            background: rgba(255,255,255,0.04);
            border-radius: 8px;
            padding: 4px;
        }
        
        .mode-btn {
            flex: 1;
            padding: 6px 10px;
            border: none;
            border-radius: 6px;
            background: transparent;
            color: #8e8ea0;
            cursor: pointer;
            font-size: 12px;
            font-weight: 500;
            transition: 0.3s;
            font-family: 'Poppins', sans-serif;
        }
        
        .mode-btn.active {
            background: rgba(167, 139, 250, 0.2);
            color: #c4b5fd;
            box-shadow: 0 0 20px rgba(167, 139, 250, 0.1);
        }
        
        .mode-btn:hover:not(.active) {
            color: #f0f0f0;
            background: rgba(255,255,255,0.04);
        }
        
        .deep-research-btn {
            width: 100%;
            padding: 10px 14px;
            border: 1px solid rgba(16, 185, 129, 0.2);
            border-radius: 10px;
            background: rgba(16, 185, 129, 0.06);
            color: #34d399;
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            transition: 0.3s;
            font-family: 'Poppins', sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            margin-top: 8px;
        }
        
        .deep-research-btn:hover {
            background: rgba(16, 185, 129, 0.12);
            border-color: rgba(16, 185, 129, 0.3);
            transform: translateY(-1px);
            box-shadow: 0 0 30px rgba(16, 185, 129, 0.1);
        }
        
        .deep-research-btn.active {
            background: rgba(16, 185, 129, 0.15);
            border-color: #34d399;
            box-shadow: 0 0 30px rgba(16, 185, 129, 0.15);
        }
        
        .sidebar-footer {
            margin-top: auto;
            font-size: 11px;
            color: #6b7280;
            display: flex;
            flex-direction: column;
            gap: 6px;
            padding-top: 16px;
            border-top: 1px solid rgba(255,255,255,0.04);
        }
        
        .badge-group {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }
        
        .badge {
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 10px;
            font-weight: 500;
        }
        
        .badge-model {
            background: rgba(167, 139, 250, 0.12);
            color: #a78bfa;
            border: 1px solid rgba(167, 139, 250, 0.1);
        }
        
        .badge-feature {
            background: rgba(16, 185, 129, 0.08);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.08);
        }
        
        .badge-status {
            background: rgba(16, 185, 129, 0.12);
            color: #34d399;
        }
        
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            height: 100vh;
            position: relative;
            z-index: 1;
        }
        
        .chat-window {
            flex: 1;
            overflow-y: auto;
            padding: 20px 20px 140px 20px;
            scroll-behavior: smooth;
        }
        
        .chat-window::-webkit-scrollbar {
            width: 4px;
        }
        .chat-window::-webkit-scrollbar-thumb {
            background: #a78bfa66;
            border-radius: 12px;
        }
        
        .welcome {
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            animation: fadeSlide 0.6s ease-out;
        }
        
        .welcome h1 {
            font-size: 48px;
            font-weight: 800;
            background: linear-gradient(135deg, #e0e0ff, #a78bfa, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 4px;
        }
        
        .welcome .year-badge-large {
            font-size: 16px;
            font-weight: 600;
            color: #34d399;
            background: rgba(16, 185, 129, 0.12);
            padding: 4px 16px;
            border-radius: 20px;
            border: 1px solid rgba(16, 185, 129, 0.15);
            display: inline-block;
            margin-top: 4px;
            -webkit-text-fill-color: #34d399;
        }
        
        .welcome .subtitle {
            color: #9ca3af;
            font-size: 16px;
            margin-top: 8px;
        }
        
        .welcome .sub-icon {
            font-size: 56px;
            margin-bottom: 16px;
            color: #7c3aed66;
            animation: pulseGlow 3s infinite;
        }
        
        .welcome .features {
            margin-top: 24px;
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            justify-content: center;
        }
        
        .welcome .features span {
            background: rgba(255,255,255,0.04);
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 12px;
            color: #8e8ea0;
            border: 1px solid rgba(255,255,255,0.04);
        }
        
        .message-row {
            padding: 16px 0;
            animation: fadeSlide 0.3s ease-out;
            border-bottom: 1px solid rgba(255,255,255,0.02);
        }
        
        .message-row.assistant {
            background: rgba(255,255,255,0.015);
            border-radius: 16px;
            margin: 4px 0;
        }
        
        @keyframes fadeSlide {
            0% { opacity: 0; transform: translateY(12px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        
        .message-content {
            max-width: 740px;
            margin: 0 auto;
            padding: 0 16px;
            display: flex;
            gap: 14px;
            align-items: flex-start;
        }
        
        .avatar {
            width: 34px;
            height: 34px;
            border-radius: 40px;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: 600;
            background: #2a2a40;
            color: #fff;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        .avatar.user {
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
        }
        .avatar.assistant {
            background: linear-gradient(135deg, #0d9488, #14b8a6);
        }
        
        .bubble-text {
            line-height: 1.7;
            white-space: pre-wrap;
            word-wrap: break-word;
            padding-top: 4px;
            font-weight: 400;
            font-size: 15px;
            color: #e8e8f0;
            flex: 1;
        }
        
        .bubble-text img {
            max-width: 100%;
            border-radius: 8px;
            margin: 8px 0;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .bubble-text pre {
            background: #151525;
            padding: 12px 16px;
            border-radius: 12px;
            overflow-x: auto;
            margin: 12px 0;
            border-left: 3px solid #a78bfa;
            position: relative;
        }
        
        .bubble-text code {
            background: #1e1e2f;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 0.9em;
            color: #f0c6c6;
        }
        
        .bubble-text pre code {
            background: transparent;
            padding: 0;
            color: #d4d4e0;
        }
        
        .copy-btn {
            position: absolute;
            top: 8px;
            right: 12px;
            background: rgba(255,255,255,0.06);
            border: none;
            color: #b0b0c8;
            padding: 4px 10px;
            border-radius: 30px;
            font-size: 12px;
            cursor: pointer;
            transition: 0.2s;
        }
        
        .copy-btn:hover {
            background: rgba(167, 139, 250, 0.25);
            color: #fff;
        }
        
        .thinking-dots {
            display: inline-flex;
            gap: 6px;
            align-items: center;
            padding: 4px 0;
        }
        
        .thinking-dots span {
            width: 8px;
            height: 8px;
            background: #a78bfa;
            border-radius: 40px;
            display: inline-block;
            animation: dotBounce 1.2s infinite ease-in-out;
        }
        
        .thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
        .thinking-dots span:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes dotBounce {
            0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
            40% { transform: scale(1); opacity: 1; }
        }
        
        .chat-form {
            position: fixed;
            bottom: 0;
            left: 280px;
            right: 0;
            display: flex;
            justify-content: center;
            padding: 16px 20px 28px 20px;
            background: linear-gradient(to top, #0d0d1a 50%, transparent);
            z-index: 5;
        }
        
        .form-wrapper {
            position: relative;
            width: 100%;
            max-width: 740px;
        }
        
        .input-container {
            display: flex;
            gap: 6px;
            align-items: flex-end;
            background: rgba(25, 25, 40, 0.7);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255,255,255,0.06);
            border-radius: 16px;
            padding: 4px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
            transition: 0.2s;
        }
        
        .input-container:focus-within {
            border-color: #a78bfa88;
            background: rgba(30, 30, 50, 0.8);
            box-shadow: 0 0 40px #7c3aed33;
        }
        
        #chat-input {
            flex: 1;
            resize: none;
            background: transparent;
            border: none;
            color: #f0f0f0;
            padding: 12px 16px;
            font-size: 15px;
            font-family: 'Poppins', sans-serif;
            max-height: 180px;
            outline: none;
        }
        
        .image-preview {
            display: none;
            padding: 8px 12px;
            align-items: center;
            gap: 10px;
            background: rgba(167, 139, 250, 0.1);
            border-radius: 30px;
            margin: 4px;
        }
        
        .image-preview.show {
            display: flex;
        }
        
        .image-preview img {
            height: 30px;
            width: 30px;
            border-radius: 6px;
            object-fit: cover;
        }
        
        .image-preview span {
            font-size: 12px;
            color: #a0a0b8;
        }
        
        .image-preview .remove-image {
            cursor: pointer;
            color: #f87171;
            font-size: 14px;
            padding: 0 4px;
        }
        
        .btn-icon {
            background: transparent;
            border: none;
            color: #8e8ea0;
            padding: 8px 10px;
            cursor: pointer;
            transition: 0.2s;
            border-radius: 30px;
            font-size: 16px;
        }
        
        .btn-icon:hover {
            color: #c4b5fd;
            background: rgba(167, 139, 250, 0.08);
        }
        
        .btn-icon.recording {
            color: #ef4444;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        
        #send-btn {
            background: linear-gradient(135deg, #7c3aed, #a78bfa);
            border: none;
            color: #fff;
            padding: 8px 16px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 16px;
            transition: 0.2s;
            margin: 4px;
            height: 40px;
            min-width: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 20px #7c3aed77;
        }
        
        #send-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 0 40px #a78bfaaa;
        }
        
        #send-btn:disabled {
            opacity: 0.4;
            transform: scale(0.95);
            box-shadow: none;
            cursor: not-allowed;
        }
        
        .error-message {
            color: #f87171;
            padding: 12px 16px;
            background: rgba(248, 113, 113, 0.08);
            border-radius: 8px;
            border-left: 3px solid #f87171;
        }
        
        .tag {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: 500;
            margin-top: 8px;
        }
        
        .tag-offline {
            background: rgba(107, 114, 128, 0.15);
            color: #9ca3af;
        }
        
        .tag-online {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
        }
        
        .tag-deep {
            background: rgba(167, 139, 250, 0.15);
            color: #a78bfa;
        }
        
        .tag-search {
            background: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
        }
        
        .search-indicator {
            display: inline-block;
            background: rgba(59, 130, 246, 0.1);
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 10px;
            color: #60a5fa;
            margin-top: 6px;
            border: 1px solid rgba(59, 130, 246, 0.1);
        }
        
        @media (max-width: 700px) {
            .sidebar {
                width: 70px;
                padding: 16px 8px;
                align-items: center;
            }
            .sidebar-header .logo-text,
            .sidebar-footer span:not(.badge),
            .new-chat-btn span,
            .mode-label,
            .badge-group span:not(.badge) {
                display: none;
            }
            .mode-toggle { flex-direction: column; }
            .mode-btn { font-size: 10px; padding: 4px 6px; }
            .deep-research-btn { font-size: 10px; padding: 6px 8px; }
            .new-chat-btn { justify-content: center; padding: 10px; }
            .chat-form { left: 70px; }
        }
        
        @media (max-width: 480px) {
            .sidebar { width: 60px; }
            .chat-form { left: 60px; padding: 12px 8px 16px; }
            #chat-input { padding: 12px 12px; font-size: 14px; }
            .btn-icon { padding: 6px 8px; font-size: 14px; }
            #send-btn { height: 36px; min-width: 38px; font-size: 14px; }
        }
    </style>
</head>
<body>
    <div class="app">
        <aside class="sidebar">
            <div class="sidebar-header">
                <i class="fas fa-brain logo-icon"></i>
                <span class="logo-text">Sumit GPT</span>
                <span class="logo-year">2026</span>
            </div>
            <button id="new-chat-btn" class="new-chat-btn">
                <i class="fas fa-plus"></i> <span>New Chat</span>
            </button>
            
            <div class="mode-section">
                <span class="mode-label"><i class="fas fa-globe"></i> Mode</span>
                <div class="mode-toggle">
                    <button class="mode-btn active" data-mode="offline" id="mode-offline">
                        <i class="fas fa-database"></i> Offline
                    </button>
                    <button class="mode-btn" data-mode="online" id="mode-online">
                        <i class="fas fa-globe"></i> Online
                    </button>
                </div>
                <button id="deep-research-btn" class="deep-research-btn">
                    <i class="fas fa-microscope"></i> Deep Research
                </button>
            </div>
            
            <div class="sidebar-footer">
                <div class="badge-group">
                    <span class="badge badge-model"><i class="fas fa-brain"></i> {{ model_name }}</span>
                    <span class="badge badge-feature"><i class="fas fa-microphone"></i> Voice</span>
                    <span class="badge badge-feature"><i class="fas fa-image"></i> Vision</span>
                </div>
                <span class="badge badge-status"><i class="fas fa-circle" style="font-size: 6px; vertical-align: middle;"></i> 2026 Updated</span>
            </div>
        </aside>

        <main class="main">
            <div id="chat-window" class="chat-window">
                <div class="welcome">
                    <div class="sub-icon"><i class="fas fa-comment-dots"></i></div>
                    <h1>Sumit GPT</h1>
                    <span class="year-badge-large">2026 Edition</span>
                    <p class="subtitle">Ask me anything — offline or online</p>
                    <div class="features">
                        <span><i class="fas fa-database"></i> Offline mode</span>
                        <span><i class="fas fa-globe"></i> Online search</span>
                        <span><i class="fas fa-microscope"></i> Deep research</span>
                        <span><i class="fas fa-microphone"></i> Voice input</span>
                        <span><i class="fas fa-image"></i> Image analysis</span>
                    </div>
                </div>
            </div>

            <form id="chat-form" class="chat-form">
                <div class="form-wrapper">
                    <div class="input-container">
                        <input type="file" id="image-input" accept="image/*" style="display:none">
                        <button type="button" class="btn-icon" id="image-btn" title="Upload image">
                            <i class="fas fa-image"></i>
                        </button>
                        <button type="button" class="btn-icon" id="voice-btn" title="Voice input">
                            <i class="fas fa-microphone"></i>
                        </button>
                        <div class="image-preview" id="image-preview">
                            <img id="preview-img" src="" alt="Preview">
                            <span id="image-name">image.jpg</span>
                            <span class="remove-image" id="remove-image">✕</span>
                        </div>
                        <textarea id="chat-input" placeholder="Ask Sumit GPT anything..."></textarea>
                        <button type="submit" id="send-btn"><i class="fas fa-arrow-up"></i></button>
                    </div>
                </div>
            </form>
        </main>
    </div>

    <script>
        const chatWindow = document.getElementById('chat-window');
        const chatForm = document.getElementById('chat-form');
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('send-btn');
        const newChatBtn = document.getElementById('new-chat-btn');
        const imageInput = document.getElementById('image-input');
        const imageBtn = document.getElementById('image-btn');
        const voiceBtn = document.getElementById('voice-btn');
        const imagePreview = document.getElementById('image-preview');
        const previewImg = document.getElementById('preview-img');
        const imageName = document.getElementById('image-name');
        const removeImageBtn = document.getElementById('remove-image');
        const modeOffline = document.getElementById('mode-offline');
        const modeOnline = document.getElementById('mode-online');
        const deepResearchBtn = document.getElementById('deep-research-btn');

        let history = [];
        let isStreaming = false;
        let currentImage = null;
        let isRecording = false;
        let currentMode = 'offline';
        let isDeepResearch = false;
        let recognition = null;

        modeOffline.addEventListener('click', () => {
            modeOffline.classList.add('active');
            modeOnline.classList.remove('active');
            currentMode = 'offline';
            deepResearchBtn.classList.remove('active');
            isDeepResearch = false;
            addSystemMessage('🔄 Switched to Offline mode');
        });

        modeOnline.addEventListener('click', () => {
            modeOnline.classList.add('active');
            modeOffline.classList.remove('active');
            currentMode = 'online';
            addSystemMessage('🌐 Switched to Online mode');
        });

        deepResearchBtn.addEventListener('click', () => {
            if (currentMode === 'offline') {
                modeOnline.click();
            }
            isDeepResearch = !isDeepResearch;
            deepResearchBtn.classList.toggle('active');
            if (isDeepResearch) {
                addSystemMessage('🔬 Deep Research mode enabled');
            } else {
                addSystemMessage('📊 Deep Research mode disabled');
            }
        });

        function addSystemMessage(text) {
            clearWelcome();
            const row = document.createElement('div');
            row.className = 'message-row assistant';
            const content = document.createElement('div');
            content.className = 'message-content';
            const avatar = document.createElement('div');
            avatar.className = 'avatar assistant';
            avatar.textContent = 'S';
            const bubble = document.createElement('div');
            bubble.className = 'bubble-text';
            bubble.style.color = '#8e8ea0';
            bubble.style.fontSize = '13px';
            bubble.style.fontStyle = 'italic';
            bubble.textContent = text;
            content.appendChild(avatar);
            content.appendChild(bubble);
            row.appendChild(content);
            chatWindow.appendChild(row);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }

        // Voice recognition
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.lang = 'en-US';
            recognition.continuous = false;
            recognition.interimResults = true;

            recognition.onresult = (event) => {
                let transcript = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    transcript += event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        chatInput.value = transcript;
                        chatInput.style.height = 'auto';
                        chatInput.style.height = chatInput.scrollHeight + 'px';
                        voiceBtn.classList.remove('recording');
                        isRecording = false;
                        setTimeout(() => {
                            if (transcript.trim()) {
                                chatForm.requestSubmit();
                            }
                        }, 300);
                    }
                }
            };

            recognition.onerror = (event) => {
                voiceBtn.classList.remove('recording');
                isRecording = false;
                if (event.error === 'not-allowed') {
                    alert('Please allow microphone access.');
                }
            };

            recognition.onend = () => {
                voiceBtn.classList.remove('recording');
                isRecording = false;
            };
        }

        voiceBtn.addEventListener('click', () => {
            if (!recognition) {
                alert('Voice not supported. Please use Chrome or Edge.');
                return;
            }
            if (isRecording) {
                recognition.stop();
                voiceBtn.classList.remove('recording');
                isRecording = false;
                return;
            }
            try {
                recognition.start();
                isRecording = true;
                voiceBtn.classList.add('recording');
            } catch (e) {
                voiceBtn.classList.remove('recording');
                isRecording = false;
            }
        });

        imageBtn.addEventListener('click', () => imageInput.click());

        imageInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (event) => {
                currentImage = event.target.result;
                previewImg.src = currentImage;
                imageName.textContent = file.name;
                imagePreview.classList.add('show');
            };
            reader.readAsDataURL(file);
        });

        removeImageBtn.addEventListener('click', () => {
            currentImage = null;
            imagePreview.classList.remove('show');
            imageInput.value = '';
        });

        function clearWelcome() {
            const welcome = chatWindow.querySelector('.welcome');
            if (welcome) welcome.remove();
        }

        function addMessage(role, text, isThinking = false, image = null, mode = '', isDeep = false) {
            clearWelcome();
            const row = document.createElement('div');
            row.className = `message-row ${role}`;
            const content = document.createElement('div');
            content.className = 'message-content';
            const avatar = document.createElement('div');
            avatar.className = `avatar ${role}`;
            avatar.textContent = role === 'user' ? 'U' : 'S';
            const bubble = document.createElement('div');
            bubble.className = 'bubble-text';
            
            if (isThinking) {
                bubble.innerHTML = `<div class="thinking-dots"><span></span><span></span><span></span></div>`;
            } else if (image && role === 'user') {
                bubble.innerHTML = `<img src="${image}" alt="Uploaded image"><br>${text || ''}`;
            } else {
                bubble.textContent = text || '';
                if (role === 'assistant' && text) {
                    let tag = '';
                    if (mode === 'online') tag = '<span class="tag tag-online"><i class="fas fa-globe"></i> Online</span>';
                    else if (mode === 'offline') tag = '<span class="tag tag-offline"><i class="fas fa-database"></i> Offline</span>';
                    if (isDeep) tag += ' <span class="tag tag-deep"><i class="fas fa-microscope"></i> Deep</span>';
                    if (tag) bubble.innerHTML += `<br>${tag}`;
                }
            }
            
            content.appendChild(avatar);
            content.appendChild(bubble);
            row.appendChild(content);
            chatWindow.appendChild(row);
            chatWindow.scrollTop = chatWindow.scrollHeight;
            return bubble;
        }

        function renderContent(bubble, text, mode = '', isDeep = false) {
            if (!text) { bubble.innerHTML = ''; return; }
            let html = text;
            html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
            html = html.replace(/```([\\s\\S]*?)```/g, function(match, code) {
                const escaped = code.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
                return `<pre><code>${escaped}</code><button class="copy-btn" onclick="copyCode(this)"><i class="fas fa-copy"></i> copy</button></pre>`;
            });
            html = html.replace(/\\n/g, '<br>');
            
            let tags = '';
            if (mode === 'online') tags += '<span class="tag tag-online"><i class="fas fa-globe"></i> Online</span>';
            else if (mode === 'offline') tags += '<span class="tag tag-offline"><i class="fas fa-database"></i> Offline</span>';
            if (isDeep) tags += ' <span class="tag tag-deep"><i class="fas fa-microscope"></i> Deep</span>';
            if (tags) html += `<br>${tags}`;
            
            bubble.innerHTML = html;
        }

        window.copyCode = function(btn) {
            const pre = btn.closest('pre');
            if (!pre) return;
            const codeEl = pre.querySelector('code');
            if (!codeEl) return;
            const text = codeEl.textContent;
            navigator.clipboard?.writeText(text).then(() => {
                btn.innerHTML = '<i class="fas fa-check"></i> copied';
                setTimeout(() => btn.innerHTML = '<i class="fas fa-copy"></i> copy', 1800);
            }).catch(() => {});
        };

        async function sendMessage(message) {
            if (isStreaming) return;
            isStreaming = true;
            sendBtn.disabled = true;

            addMessage('user', message, false, currentImage);
            const userMessage = { role: 'user', content: message, image: currentImage };
            history.push(userMessage);

            const thinkingBubble = addMessage('assistant', '', true);
            let fullText = '';
            let searchResults = '';
            let modeUsed = currentMode;

            if (currentMode === 'online') {
                try {
                    const searchResponse = await fetch('/api/search', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            query: message,
                            deep: isDeepResearch
                        }),
                    });
                    const searchData = await searchResponse.json();
                    if (searchData.results) {
                        searchResults = searchData.results;
                        console.log('🔍 Search results found!');
                    } else {
                        console.log('⚠️ No search results found');
                    }
                } catch (e) {
                    console.log('Search error:', e);
                }
            }

            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        message: message,
                        history: history.slice(0, -1),
                        image: currentImage,
                        search_results: searchResults,
                        mode: currentMode,
                        deep: isDeepResearch
                    }),
                });

                if (!response.body) throw new Error('No response body');

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });

                    const lines = buffer.split('\\n\\n');
                    buffer = lines.pop();

                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        const payload = line.slice(6);
                        if (payload === '[DONE]') continue;
                        try {
                            const parsed = JSON.parse(payload);
                            if (parsed.error) {
                                fullText += `\\n[Error: ${parsed.error}]`;
                            } else if (parsed.content) {
                                fullText += parsed.content;
                            }
                            if (thinkingBubble.querySelector('.thinking-dots')) {
                                thinkingBubble.innerHTML = '';
                            }
                            renderContent(thinkingBubble, fullText, modeUsed, isDeepResearch);
                            chatWindow.scrollTop = chatWindow.scrollHeight;
                        } catch (e) {}
                    }
                }
            } catch (err) {
                fullText = `Error: ${err.message}`;
                thinkingBubble.innerHTML = '';
                thinkingBubble.innerHTML = `<div class="error-message"><i class="fas fa-exclamation-circle"></i> ${err.message}</div>`;
            }

            if (thinkingBubble.querySelector('.thinking-dots')) {
                thinkingBubble.innerHTML = '';
                renderContent(thinkingBubble, '');
            }
            if (fullText) {
                renderContent(thinkingBubble, fullText, modeUsed, isDeepResearch);
            } else {
                thinkingBubble.textContent = 'No response';
            }
            
            history.push({ role: 'assistant', content: fullText });
            currentImage = null;
            imagePreview.classList.remove('show');
            imageInput.value = '';
            isStreaming = false;
            sendBtn.disabled = false;
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }

        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const message = chatInput.value.trim();
            if ((!message && !currentImage) || isStreaming) return;
            chatInput.value = '';
            chatInput.style.height = 'auto';
            sendMessage(message);
        });

        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                chatForm.requestSubmit();
            }
        });

        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = chatInput.scrollHeight + 'px';
        });

        newChatBtn.addEventListener('click', () => {
            if (isStreaming) return;
            history = [];
            currentImage = null;
            imagePreview.classList.remove('show');
            imageInput.value = '';
            chatWindow.innerHTML = `
                <div class="welcome">
                    <div class="sub-icon"><i class="fas fa-comment-dots"></i></div>
                    <h1>Sumit GPT</h1>
                    <span class="year-badge-large">2026 Edition</span>
                    <p class="subtitle">Ask me anything — offline or online</p>
                    <div class="features">
                        <span><i class="fas fa-database"></i> Offline mode</span>
                        <span><i class="fas fa-globe"></i> Online search</span>
                        <span><i class="fas fa-microscope"></i> Deep research</span>
                        <span><i class="fas fa-microphone"></i> Voice input</span>
                        <span><i class="fas fa-image"></i> Image analysis</span>
                    </div>
                </div>`;
            chatWindow.scrollTop = 0;
        });

        chatInput.style.height = 'auto';
    </script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, model_name=MODEL_NAME)

@app.route('/api/search', methods=['POST'])
def search():
    """Web search endpoint with better result extraction"""
    data = request.get_json(force=True)
    query = data.get('query', '').strip()
    deep = data.get('deep', False)
    
    if not query:
        return jsonify({'results': ''})
    
    results = web_search(query, deep)
    
    if results:
        print(f"✅ Search results: {results[:200]}...")
    else:
        print(f"⚠️ No search results found")
    
    return jsonify({'results': results or ''})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json(force=True)
    user_message = data.get('message', '').strip()
    history = data.get('history', [])
    image_data = data.get('image', None)
    search_results = data.get('search_results', '')
    mode = data.get('mode', 'offline')
    deep = data.get('deep', False)

    messages = []
    
    # Build messages based on mode
    if mode == 'online':
        if search_results:
            system_prompt = SYSTEM_PROMPT_ONLINE.format(
                search_results=search_results,
                question=user_message
            )
        else:
            system_prompt = f"""You are Sumit GPT. The user asked: "{user_message}"

IMPORTANT: No search results were found for this query.
Please respond with: "I couldn't find current information about this. Please try a more specific question or check official sources."

Do not make up information or use outdated knowledge."""
        
        messages.append({'role': 'system', 'content': system_prompt})
    else:
        messages.append({'role': 'system', 'content': SYSTEM_PROMPT_OFFLINE})
    
    messages.extend(history)
    
    user_content = user_message if user_message else "What do you see in this image?"
    
    if image_data:
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        messages.append({
            'role': 'user',
            'content': user_content,
            'images': [image_data]
        })
    else:
        messages.append({'role': 'user', 'content': user_content})

    def generate():
        payload = {
            'model': MODEL_NAME, 
            'messages': messages, 
            'stream': True, 
            'options': {
                'num_predict': 2048 if deep else 1024,
                'temperature': 0.7,
                'top_p': 0.9
            }
        }
        
        try:
            print(f"📤 Mode: {mode.upper()}{' 🔬 DEEP' if deep else ''}")
            if image_data:
                print(f"🖼️ Image included")
            if search_results:
                print(f"🔍 Search results included ({len(search_results)} chars)")
            
            with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=120) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line.decode('utf-8'))
                    content = chunk.get('message', {}).get('content', '')
                    if content:
                        yield f"data: {json.dumps({'content': content})}\n\n"
                    if chunk.get('done'):
                        yield "data: [DONE]\n\n"
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            print(f"❌ Error: {error_msg}")
            yield f"data: {json.dumps({'error': error_msg})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Sumit GPT - 2026 Edition (Super Advanced)")
    print("=" * 60)
    print(f"🤖 Model: {MODEL_NAME}")
    print("📱 Features:")
    print("   - Offline mode (local knowledge)")
    print("   - Online mode (web search with forced usage)")
    print("   - Deep Research (comprehensive)")
    print("   - Voice input")
    print("   - Image analysis")
    print("=" * 60)
    print("🌐 http://localhost:5000")
    print("=" * 60)
    print("Press CTRL+C to stop")
    print("=" * 60)
    
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://localhost:5000")
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    app.run(debug=True, port=5000, host='127.0.0.1')