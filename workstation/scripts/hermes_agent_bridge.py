import subprocess
import json
import sys
import time
from typing import Any, Optional

def eval_hermes_raw(js_code: str) -> str:
    res = subprocess.run(
        ["node", "apps/desktop/scripts/eval.mjs", js_code],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    if res.returncode != 0:
        raise RuntimeError(f"eval.mjs failed ({res.returncode}): {res.stderr.strip() or res.stdout.strip()}")
    return res.stdout.strip()

def eval_hermes_json(js_code: str) -> Any:
    out = eval_hermes_raw(js_code)
    try:
        return json.loads(out)
    except Exception:
        return out

def get_ui_state() -> dict:
    code = """
    (() => {
        const input = document.querySelector('div[role="textbox"][aria-label="Message"]') || document.querySelector('[contenteditable="true"]');
        const sendBtn = document.querySelector('button[aria-label="Send message"]') || document.querySelector('button[aria-label="Send"]');
        const messages = Array.from(document.querySelectorAll('[data-role="message"], .chat-message, [class*="message-bubble"]')).map(m => m.textContent?.slice(0, 100));
        return {
            title: document.title,
            location: document.location.href,
            aiControlActive: !!window.__hermesAiControlActive,
            inputExists: !!input,
            inputAriaLabel: input ? input.getAttribute('aria-label') : null,
            inputText: input ? input.textContent : null,
            sendBtnExists: !!sendBtn,
            messageCount: messages.length,
            recentMessages: messages.slice(-3)
        };
    })()
    """
    return eval_hermes_json(code)

def inspect_chat_thread() -> dict:
    code = """
    (() => {
        const textElements = Array.from(document.querySelectorAll('div, p, span'))
            .filter(el => el.children.length === 0 && el.textContent?.trim().length > 0)
            .map(el => ({
                tag: el.tagName,
                text: el.textContent.trim().slice(0, 100),
                parentClass: el.parentElement?.className?.slice(0, 80)
            }));
        
        // Check for specific chat elements
        const chatContainers = Array.from(document.querySelectorAll('[data-testid], [aria-label], [role]')).map(el => ({
            tag: el.tagName,
            testid: el.getAttribute('data-testid'),
            role: el.getAttribute('role'),
            ariaLabel: el.getAttribute('aria-label'),
            className: el.className?.slice(0, 80)
        }));

        return {
            totalLeaves: textElements.length,
            sampleLeaves: textElements.slice(0, 15),
            specialElements: chatContainers.filter(e => e.testid || e.role || e.ariaLabel)
        };
    })()
    """
    return eval_hermes_json(code)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "inspect":
        print(json.dumps(inspect_chat_thread(), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(get_ui_state(), indent=2, ensure_ascii=False))

