"""Kısa Gemini karakter testi"""
import os, time
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types as genai_types

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

system_prompt = """Sen AI-zen, rahat ve samimi bir arkadaşsın. Normal bir insan gibi konuş, doğal ve akıcı.
KURALLAR:
1. Cevapların 15-250 karakter arası olsun.
2. ASLA SORU SORMA!
3. Mükemmel Türkçe, günlük dil, argo serbest.
4. Tam cümle kur, anlamlı cevap ver."""

cfg = genai_types.GenerateContentConfig(
    system_instruction=system_prompt,
    temperature=0.8,
    max_output_tokens=2048,
    thinking_config=genai_types.ThinkingConfig(thinking_budget=1024),
)

tests = [
    ("canım sıkılıyor", "Soru sormama"),
    ("bugün hava güzel", "Doğal cevap"),
    ("bir film izliyom", "Karakter tutarlılığı"),
]

for prompt, test_name in tests:
    try:
        r = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[genai_types.Content(role='user', parts=[genai_types.Part(text=prompt)])],
            config=cfg,
        )
        cevap = r.text.strip()
        has_q = '?' in cevap
        status = 'UYARI' if has_q else 'OK'
        print(f"[{test_name}] \"{prompt}\" -> \"{cevap}\" [{len(cevap)} karakter, soru:{status}]")
    except Exception as e:
        if '429' in str(e) or 'quota' in str(e).lower():
            print(f"[{test_name}] Rate limit - 15s bekleniyor...")
            time.sleep(15)
            r = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[genai_types.Content(role='user', parts=[genai_types.Part(text=prompt)])],
                config=cfg,
            )
            cevap = r.text.strip()
            has_q = '?' in cevap
            status = 'UYARI' if has_q else 'OK'
            print(f"[{test_name}] \"{prompt}\" -> \"{cevap}\" [{len(cevap)} karakter, soru:{status}]")
        else:
            print(f"[{test_name}] HATA: {e}")
    time.sleep(2)  # Rate limit önlemi

print("\n✅ Testler tamamlandı!")
print("Provider: gemini | Model: gemini-2.5-flash | ThinkingBudget: 1024")
