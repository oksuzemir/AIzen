# GitHub Copilot Instructions for AI-zen Project

## Project Overview

AI-zen is an AI-powered chatbot for drrr.com anonymous chat platform. It uses Groq's free LLM API (llama-3.3-70b-versatile) to respond when tagged with @AI-zen in chat rooms.

**Key Facts:**
- Bot Name: AI-zen (with hyphen)
- Owner Username: aizen (without hyphen)
- Language: Python 3.12+
- AI Provider: Groq (free tier)
- Model: llama-3.3-70b-versatile (70B parameters, more powerful)
- Target Platform: drrr.com
- Primary Users: Turkish and English speakers
- Character Limit: 140 characters per message (Twitter-like)

## Core Technologies

### Required Packages
```python
aiohttp==3.10.11        # Async HTTP operations
aiofiles                # Async file operations
curl_cffi==0.7.3        # HTTP requests with Cloudflare bypass
groq==1.0.0             # Groq AI API client
python-dotenv           # Environment variable management
```

### Architecture
- **Async/Await**: All network operations are asynchronous
- **Event Loop**: Uses WindowsSelectorEventLoopPolicy for Windows compatibility
- **Modular System**: Plugin-based module loading from `modules/` directory
- **Cookie Auth**: Uses drrr-session-1 and cf_clearance cookies

## File Structure & Responsibilities

### Core Files

#### `main.py`
- Entry point for the application
- Loads environment variables with `python-dotenv`
- Sets up Windows event loop policy
- Dynamically loads modules from `modules/` directory
- Creates Connection instance and starts bot

#### `networking.py`
- Manages connection to drrr.com
- Handles login, room joining, message polling
- Implements message queue with throttling (1.5s default)
- **Important**: Proxy is disabled (`proxies = None`) by default
- Sends messages via async POST requests
- Cookie management and session handling

#### `modules/AIzen.py`
- Main AI chatbot logic
- Responds to @AI-zen mentions in chat (NOT to DMs)
- Uses Groq API with llama-3.3-70b-versatile model (70B params)
- Maintains per-user conversation history (max 10 messages)
- Injects real-time context (Turkish timezone, date, time)
- System prompt emphasizes natural, casual conversation (<100 chars)
- **Owner Authentication**: Verifies "aizen" username with password (OWNER_PASSWORD in .env)
- **Rate Limiting**: 5 requests per minute per user
- **Auto-Cleanup**: Removes inactive user histories after 1 hour
- **Statistics Tracking**: Total messages, unique users, uptime
- **Welcome Messages**: Greets users joining the room automatically
- **Self-Message Prevention**: Ignores own messages to prevent infinite loops
- **Commands**: !yardım, !saat, !unutbeni (user) + !stats, !model, !temp, !clear (owner)
- **Response Validation**: validate_response() checks all AI outputs
- **Fallback System**: 8 fallback responses for invalid AI outputs
- **Question Detection**: Rejects responses containing question words (even without ?)

#### `modules/module.py`
- Base class for all modules
- Provides regex-based command matching
- Override `cmds` property to define commands
- Override `handler()` for custom message handling

### Message Protocol (`popyo/`)

#### `message.py`
- Defines incoming message types (Message_Type enum)
- Classes: Message, JoinMessage, LeaveMessage, DirectMessage, etc.
- Core types: `message`, `me`, `dm`, `join`, `leave`, `music`, `url`, `new_host`, `room_profile`, `knock`, `async_response`

#### `outgoing_message.py`
- Defines outgoing message types (Outgoing_Message_Type enum)
- Classes: OutgoingMessage, OutgoingDirectMessage, OutgoingUrlMessage, etc.
- Used to construct messages sent to drrr.com via queue

#### `utils.py`
- `parse_message()`: Converts drrr.com JSON to message objects
- `parse_async_response()`: Handles server asynchronous responses
- Handles user parsing with None checks

#### `room.py` & `user.py`
- Room state management
- User tracking in rooms

## Important Patterns & Best Practices

### 1. Message Handling
```python
# Bot kendi mesajlarına cevap vermesin (sonsuz döngü önlemi)
def handler(self, msg):
    import popyo
    
    # Bot kendi mesajlarını işlemesin
    bot_user_id = self.bot.own_user.id if self.bot.own_user else None
    sender_user_id = msg.user.id if hasattr(msg, 'user') and msg.user else None
    if bot_user_id and sender_user_id == bot_user_id:
        return  # Bot kendi mesajlarını görmezden gel
    
    # DMs are IGNORED (sadece şifre kontrolü için kullanılır)
    if msg.type == popyo.Message_Type.dm:
        self.handle_dm_password(msg)
        return
    
    super().handler(msg)
```

### 2. Welcome Greeting
```python
def handle_join(self, msg):
    """Odaya katılan kullanıcıyı selamla"""
    if not msg.user:
        return
    
    user_name = msg.user.name
    user_id = msg.user.id
    bot_user_id = self.bot.own_user.id if self.bot.own_user else None
    
    # Bot kendine selam vermesin
    if user_id == bot_user_id:
        return
    
    # Selam mesajı
    self.bot.send(f"@{user_name} Hoş geldin! 👋😊")
```

### 3. AI Response with Real-Time Context
```python
# Always inject current time/date for Turkish users
import datetime
turkey_offset = datetime.timezone(datetime.timedelta(hours=3))
now = datetime.datetime.now(turkey_offset)

time_context = f"\n\n[GÜNCEL BİLGİ - Türkiye saati: {time_str}, Tarih: {date_str} {day_name}]"
question_with_context = question + time_context
```

### 4. Rate Limiting
```python
def check_rate_limit(self, user_id):
    """Rate limit kontrolü - dakikada 5 istek"""
    now = time.time()
    
    # Eski istekleri temizle (60 saniyeden eski)
    self.rate_limit_tracker[user_id] = [
        timestamp for timestamp in self.rate_limit_tracker[user_id]
        if now - timestamp < 60
    ]
    
    # Limit kontrolü
    if len(self.rate_limit_tracker[user_id]) >= self.max_requests_per_minute:
        return False
    
    # Yeni isteği kaydet
    self.rate_limit_tracker[user_id].append(now)
    return True
```

### 5. Owner Authentication
```python
# aizen kullanıcısına şifre sor (tire olmadan!)
if user_name_lower == "aizen":
    if user_id not in self.authenticated_owners:
        self.bot.dm(user_id, "🔐 Sen gerçek aizen misin? Şifreni söyle!")
```

### 6. Character Limit Compliance
- drrr.com has 140 character limit
- Messages are auto-chunked in `networking.py`
- AI is instructed to keep responses under 100 chars to account for @username tag

### 7. Async Patterns
```python
# Use asyncio.run_coroutine_threadsafe for thread-safe async calls
asyncio.run_coroutine_threadsafe(self.putQ(msgs), self.loop)
```

### 8. Error Handling
```python
# Always catch Groq API errors and provide friendly Turkish messages
try:
    response = self.client.chat.completions.create(...)
except Exception as e:
    if "api_key" in str(e).lower():
        return "⚠️ API key hatası. https://console.groq.com"
    elif "rate_limit" in str(e).lower():
        return "⚠️ Rate limit aşıldı. Biraz bekleyin."
```

### 9. Environment Variables
```python
# Always use .env file for secrets
from dotenv import load_dotenv
load_dotenv()  # Must be called BEFORE importing modules

api_key = os.getenv('GROQ_API_KEY')
```

## Common Issues & Solutions

### Issue: API Key Not Loading
**Cause:** `load_dotenv()` called after module imports
**Solution:** Call `load_dotenv()` at the very start of `main.py`

### Issue: Model Decommissioned Error
**Cause:** Groq deprecated old models (llama3-8b-8192)
**Solution:** Use current model: `llama-3.3-70b-versatile` (recommended for natural conversation) or `llama-3.1-8b-instant` (faster)

### Issue: Proxy Connection Failed
**Cause:** Proxy server not running
**Solution:** Set `proxies = None` in `networking.py`

### Issue: JSON Decode Error
**Cause:** Empty or malformed response from drrr.com
**Solution:** Check response content before JSON parsing:
```python
if not text or text.strip() == '':
    continue
data = json.loads(text)
```

### Issue: UnicodeEncodeError (Chinese characters)
**Cause:** Log filename used Chinese characters
**Solution:** Use `datetime.now().strftime('%Y-%m-%d')` for log filenames

### Issue: AttributeError: 'NoneType' has no attribute 'name'
**Cause:** User object can be None in some message types
**Solution:** Always check `if msg.user:` before accessing `msg.user.name`

### Issue: AI Responses Containing Questions or Banned Phrases
**Cause:** LLM generates responses that don't match desired personality
**Solution:** Use `validate_response()` method with 5-check validation:
```python
def validate_response(self, response):
    # 1. Length check (10-100 chars)
    # 2. Question mark detection
    # 3. Question word detection
    # 4. Banned phrase checking
    # 5. Text-only length validation
    return True/False
```
**Fallback:** Return random selection from 8 fallback responses when validation fails

## Coding Style Guidelines

### Language
- **Comments**: Turkish (this is a Turkish project)
- **Variable names**: English (standard practice)
- **User-facing messages**: Turkish
- **Documentation**: English (for wider accessibility)

### Python Conventions
- Use type hints where helpful
- Prefer async/await over callbacks
- Use try/except for all external API calls
- Log important events to terminal and file

### Turkish Language Support
- Use proper Turkish characters (ı, ğ, ü, ş, ö, ç)
- Month and day names translated to Turkish
- Natural, conversational Turkish in AI responses

## Module Development Guide

### Creating a New Module
```python
from modules.module import Module

class MyModule(Module):
    def __init__(self, bot):
        super().__init__(bot)
    
    @property
    def cmds(self):
        return {
            'command_name': r'regex pattern here',
            'greet': r'!hello (.+)'
        }
    
    def command_name(self, msg):
        # msg.message = full message
        # msg.user = User object
        # msg.groups = regex capture groups
        self.bot.send("Response")
```

### Available Bot Methods
```python
self.bot.send(message)                      # Send to room
self.bot.dm(user_id, message)              # Send DM (not recommended)
self.bot.send_url(message, url)            # Send with URL
self.bot.music(name, url)                  # Share music
```

## Testing Checklist

When making changes, test:
- [ ] Bot connects successfully
- [ ] Bot joins room without errors
- [ ] @AI-zen mentions trigger responses
- [ ] Responses are under 140 characters
- [ ] Turkish language quality is good
- [ ] Real-time date/time information is correct
- [ ] No response to DMs (expected behavior)
- [ ] Conversation history persists per user
- [ ] API errors handled gracefully
- [ ] Log files created successfully
- [ ] Validation system catches questions (with and without ?)
- [ ] Validation system rejects banned phrases
- [ ] Fallback responses used when AI output invalid
- [ ] Bot doesn't respond to its own messages

## Security Considerations

- **Never commit** `.env` file to Git
- **Never log** API keys or cookies in plain text
- **Always use** environment variables for secrets
- **Validate** all user input before processing
- **Rate limit** API calls to avoid abuse
- **Don't expose** internal error details to users

## Performance Tips

1. **Throttling**: Keep `throttle >= 1.5` to avoid rate limits
2. **History Limit**: Max 10 messages per user to save memory
3. **Token Limit**: Max 150 tokens per AI response for speed
4. **Temperature**: 0.7 for balanced creativity/consistency
5. **Model Choice**: llama-3.3-70b-versatile is recommended for natural conversation (70B params)
6. **Rate Limiting**: 5 requests per minute per user prevents abuse
7. **Auto-Cleanup**: 1 hour inactivity timeout clears old histories

## Deployment Notes

### Local Testing
```bash
python main.py
# Enter cookies when prompted
# Test with @AI-zen in drrr.com room
```

### Cloud Deployment (Planned)
- **Fly.io**: Recommended for 24/7 hosting
- **Railway**: Alternative option
- **VPS**: Use screen/tmux for persistence

### Environment Variables for Production
```env
GROQ_API_KEY=gsk_xxxxx
OWNER_PASSWORD=your_password_here
```

## AI Prompt Engineering

Current system prompt philosophy:
- **Brevity**: Max 100 characters enforced (validated: 10-100 char range)
- **Natural Language**: Rahat, basit, kasımsız konuşma tarzı
- **Example-Driven**: Prompt içinde "naber" → "iyidir senden naber" gibi örnekler
- **Avoid Patterns**: "sabahları iyiyim", "güzel günler" gibi garip ifadeler yasaklandı
- **Banned Phrases**: "kahve", "çay", "ne yaparız", "ne yapıyorsun", "yemek yedin" ve benzerleri
- **No Questions**: Soru kelimesi ve soru işareti kesinlikle yasak
- **Context Awareness**: Inject real-time date/time
- **Personality**: Arkadaş canlısı, samimi, doğal
- **Temperature**: 0.7 for optimal consistency (lowered from 0.9)
- **Max Tokens**: 150 (optimized for brevity)
- **Model**: llama-3.3-70b-versatile (70B params for better understanding)

## Future Enhancements

Planned features (DO NOT implement without discussion):
- Multi-room support
- Web dashboard for statistics
- Message analytics
- User reputation system

## Quick Reference

### Restart Bot After Changes
```bash
Ctrl+C  # Stop bot
python main.py  # Restart
```

### View Logs
- Terminal: Real-time output
- Files: `logs/YYYY-MM-DD.log`

### Test AI Locally
```python
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv('GROQ_API_KEY'))
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "test"}],
    max_tokens=150
)
print(response.choices[0].message.content)
```

## Contact & Support

- **GitHub Issues**: For bug reports and features
- **drrr.com**: Test with AI-zen user in rooms
- **Documentation**: See README.md for user guide

---

**Remember**: This bot is designed for Turkish users on drrr.com. Keep responses short, Turkish quality high, and always respect platform rules.
