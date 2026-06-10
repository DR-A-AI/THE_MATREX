import warnings
warnings.filterwarnings('ignore')
import google.generativeai as genai

keys = {
    'NEO_PRIMARY_KEY':      'AIzaSyDP7qkd2fVBn9qsnMPhffE6I-zFIQMuPwE',
    'TRINITY_MORPHEUS_KEY': 'AIzaSyDa2IPVU3fIm6nkExlBfWaXkLXIUQlYMjs',
}

models_to_try = [
    'gemini-2.0-flash-lite',
    'gemini-2.5-flash-lite',
    'gemini-2.0-flash',
    'gemini-2.5-flash',
]

for key_name, key in keys.items():
    genai.configure(api_key=key)
    print(f"\n[{key_name}]")
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content('Reply with ONE word: ready')
            print(f"  [OK] {model_name} -> {resp.text.strip()[:40]}")
            break  # found working model
        except Exception as e:
            err = str(e)
            if '429' in err:
                print(f"  [429] {model_name} -> quota hit")
            elif '404' in err:
                print(f"  [404] {model_name} -> not found")
            else:
                print(f"  [ERR] {model_name} -> {err[:80]}")
