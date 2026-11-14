import subprocess
import json
import time
import sys

sys.stdout.reconfigure(encoding="utf-8")

def read_chat_messages():
    code = """
    (() => {
        // Collect messages from thread
        // In Hermes desktop, messages often have specific attributes or role="article" or bubbles
        const allElements = document.querySelectorAll('*');
        const bubbles = [];
        
        // Find message items
        const messageNodes = document.querySelectorAll('[data-role="message"], [data-message-id], div[class*="message"], div[class*="bubble"]');
        
        // Let's inspect all elements inside the chat container
        const main = document.querySelector('main') || document.body;
        const items = Array.from(main.querySelectorAll('p, pre, code, button[class*="flex"], div[class*="markdown"], h1, h2, h3, h4')).map(el => ({
            tag: el.tagName,
            text: el.textContent?.trim()?.slice(0, 300),
            role: el.getAttribute('role'),
            ariaLabel: el.getAttribute('aria-label')
        })).filter(x => x.text && x.text.length > 0);

        return {
            url: window.location.href,
            totalItems: items.length,
            recentItems: items.slice(-15)
        };
    })()
    """
    res = subprocess.run(["node", "apps/desktop/scripts/eval.mjs", code], capture_output=True, text=True, encoding="utf-8")
    if res.returncode == 0:
        try:
            return json.loads(res.stdout)
        except Exception:
            return res.stdout
    return {"error": res.stderr}

def watch_chat(iterations=6, delay=3):
    print(f"Monitoring Hermes AI ({iterations} cycles x {delay}s)...")
    for i in range(iterations):
        time.sleep(delay)
        data = read_chat_messages()
        if isinstance(data, dict):
            items = data.get("recentItems", [])
            meaningful = [
                f"[{x['tag']}] {x['text'][:120]}"
                for x in items
                if not any(ignore in x['text'] for ignore in ["v0.21", "Scroll to bottom", "Backendready", "desktop", "Aprender"])
            ]
            print(f"--- T+{(i+1)*delay}s (Total elements: {data.get('totalItems')}) ---")
            for m in meaningful[-4:]:
                print("  ", m)

def print_last_response():
    code = """
    (() => {
        const main = document.querySelector('main') || document.body;
        const bubbles = Array.from(main.querySelectorAll('div[class*="prose"], div[class*="markdown"], p, table, ul, ol'));
        return bubbles.map(b => b.innerText || b.textContent).filter(Boolean);
    })()
    """
    res = subprocess.run(["node", "apps/desktop/scripts/eval.mjs", code], capture_output=True, text=True, encoding="utf-8")
    if res.returncode == 0:
        lines = json.loads(res.stdout)
        print("\n".join(lines[-8:]))

def inspect_turns():
    code = """
    (() => {
        const userPrompts = Array.from(document.querySelectorAll('button[aria-label="Edit message"]')).map(b => b.textContent?.trim());
        const toolButtons = Array.from(document.querySelectorAll('button[class*="flex"]')).map(b => b.textContent?.trim()).filter(Boolean);
        const paragraphs = Array.from(document.querySelectorAll('main p')).map(p => p.textContent?.trim()).filter(Boolean);
        return { userPrompts, toolButtons: toolButtons.slice(-8), paragraphs: paragraphs.slice(-6) };
    })()
    """
    res = subprocess.run(["node", "apps/desktop/scripts/eval.mjs", code], capture_output=True, text=True, encoding="utf-8")
    if res.returncode == 0:
        print(json.dumps(json.loads(res.stdout), indent=2, ensure_ascii=False))

def print_full_text():
    code = """
    (() => {
        const main = document.querySelector('main') || document.body;
        return main.innerText;
    })()
    """
    res = subprocess.run(["node", "apps/desktop/scripts/eval.mjs", code], capture_output=True, text=True, encoding="utf-8")
    if res.returncode == 0:
        text = json.loads(res.stdout)
        lines = [l for l in text.split("\n") if l.strip()]
        for l in lines[-25:]:
            print(l)

def print_prompt_b_response():
    code = """
    (() => {
        const main = document.querySelector('main') || document.body;
        return main.innerText;
    })()
    """
    res = subprocess.run(["node", "apps/desktop/scripts/eval.mjs", code], capture_output=True, text=True, encoding="utf-8")
    if res.returncode == 0:
        text = json.loads(res.stdout)
        lines = text.split("\n")
        idx = -1
        for i, l in enumerate(lines):
            if "Verifique a conversa atualmente aberta" in l:
                idx = i
                break
        if idx != -1:
            print("\n".join(lines[idx:]))
        else:
            print("\n".join(lines[-40:]))

def check_right_rail():
    code = """
    (() => {
        const tabs = Array.from(document.querySelectorAll('[role="tab"]')).map(t => ({
            text: t.textContent?.trim(),
            selected: t.getAttribute('aria-selected'),
            role: t.getAttribute('role')
        }));
        const webviews = Array.from(document.querySelectorAll('webview, iframe')).map(w => ({
            tag: w.tagName,
            src: w.getAttribute('src'),
            className: w.className
        }));
        return { tabs, webviews };
    })()
    """
    res = subprocess.run(["node", "apps/desktop/scripts/eval.mjs", code], capture_output=True, text=True, encoding="utf-8")
    if res.returncode == 0:
        print(res.stdout)

def inspect_right_tabs():
    code = """
    (() => {
        const tabs = Array.from(document.querySelectorAll('[role="tab"]')).map(t => ({
            text: t.textContent?.trim(),
            selected: t.getAttribute('aria-selected') === 'true',
            hasClose: !!t.querySelector('button[aria-label="Close"]')
        }));
        return tabs;
    })()
    """
    res = subprocess.run(["node", "apps/desktop/scripts/eval.mjs", code], capture_output=True, text=True, encoding="utf-8")
    if res.returncode == 0:
        print(res.stdout)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        watch_chat(iterations=int(sys.argv[2]) if len(sys.argv) > 2 else 5)
    elif len(sys.argv) > 1 and sys.argv[1] == "--last":
        print_last_response()
    elif len(sys.argv) > 1 and sys.argv[1] == "--turns":
        inspect_turns()
    elif len(sys.argv) > 1 and sys.argv[1] == "--text":
        print_full_text()
    elif len(sys.argv) > 1 and sys.argv[1] == "--prompt_b":
        print_prompt_b_response()
    elif len(sys.argv) > 1 and sys.argv[1] == "--right":
        check_right_rail()
    elif len(sys.argv) > 1 and sys.argv[1] == "--tabs":
        inspect_right_tabs()
    else:
        print(json.dumps(read_chat_messages(), indent=2, ensure_ascii=False))
