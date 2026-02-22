# GitHub Copilot Instructions for AIzen Project

## Project Overview

AIzen is an AI-powered chatbot for drrr.com anonymous chat platform. It uses Groq's free LLM API (llama-3.1-8b-instant) to respond when tagged with @AIzen in chat rooms.

**Key Facts:**
- Language: Python 3.12+
- AI Provider: Groq (free tier)
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
- Responds to @AIzen mentions in chat (NOT to DMs)
- Uses Groq API with llama-3.1-8b-instant model
- Maintains per-user conversation history (max 10 messages)
- Injects real-time context (Turkish timezone, date, time)
- System prompt emphasizes short responses (<100 chars) and excellent Turkish

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
# DMs are IGNORED (as of latest version)
def handler(self, msg):
    import popyo
    if msg.type == popyo.Message_Type.dm:
        return  # Don't respond to DMs
    super().handler(msg)
```

### 2. AI Response with Real-Time Context
```python
# Always inject current time/date for Turkish users
import datetime
turkey_offset = datetime.timezone(datetime.timedelta(hours=3))
now = datetime.datetime.now(turkey_offset)

time_context = f"\n\n[GÜNCEL BİLGİ - Türkiye saati: {time_str}, Tarih: {date_str} {day_name}]"
question_with_context = question + time_context
```

### 3. Character Limit Compliance
- drrr.com has 140 character limit
- Messages are auto-chunked in `networking.py`
- AI is instructed to keep responses under 100 chars to account for @username tag

### 4. Async Patterns
```python
# Use asyncio.run_coroutine_threadsafe for thread-safe async calls
asyncio.run_coroutine_threadsafe(self.putQ(msgs), self.loop)
```

### 5. Error Handling
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

### 6. Environment Variables
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
**Solution:** Use current model: `llama-3.1-8b-instant`

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
- [ ] @AIzen mentions trigger responses
- [ ] Responses are under 140 characters
- [ ] Turkish language quality is good
- [ ] Real-time date/time information is correct
- [ ] No response to DMs (expected behavior)
- [ ] Conversation history persists per user
- [ ] API errors handled gracefully
- [ ] Log files created successfully

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
3. **Token Limit**: Max 200 tokens per AI response for speed
4. **Temperature**: 0.8 for balanced creativity/consistency
5. **Model Choice**: llama-3.1-8b-instant is fastest

## Deployment Notes

### Local Testing
```bash
python main.py
# Enter cookies when prompted
# Test with @AIzen in drrr.com room
```

### Cloud Deployment (Planned)
- **Fly.io**: Recommended for 24/7 hosting
- **Railway**: Alternative option
- **VPS**: Use screen/tmux for persistence

### Environment Variables for Production
```env
GROQ_API_KEY=gsk_xxxxx
```

## AI Prompt Engineering

Current system prompt philosophy:
- **Brevity**: Max 100 characters enforced
- **Language Quality**: Emphasize natural Turkish
- **Context Awareness**: Inject real-time date/time
- **Personality**: Friendly, helpful, conversational
- **emoji**: Allowed for expressiveness

## Future Enhancements

Planned features (DO NOT implement without discussion):
- Multi-room support
- Web dashboard for statistics
- Custom command system
- Auto rate-limit management
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
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "test"}],
    max_tokens=200
)
print(response.choices[0].message.content)
```

## Contact & Support

- **GitHub Issues**: For bug reports and features
- **drrr.com**: Test with AIzen user in rooms
- **Documentation**: See README.md for user guide

---

**Remember**: This bot is designed for Turkish users on drrr.com. Keep responses short, Turkish quality high, and always respect platform rules.
