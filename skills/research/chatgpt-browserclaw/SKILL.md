---
name: chatgpt-browserclaw
description: "Continue an existing ChatGPT conversation by sending its exact next-cycle prompt, with durable readback, no duplicate sends, and no speculative retries."
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [ChatGPT, Browser, Continuation, Reliability]
    category: research
---

# ChatGPT continuation cycle via Hermes Workstation Browser

Use the native Workstation Browser task bound to the exact target conversation. Preserve its session_id, run_id and task_id on every tool call; never borrow a tab from another session. Do not use external CDP or OS mouse/keyboard automation.

1. Read the CURRENT ChatGPT conversation (not Hermes chat logs). Locate the most recent complete assistant-produced continuation prompt, with its exact heading (for example CONTINUAR OTIMIZACAO ACIRV - CICLO 6). Do not infer a heading from a summary such as "Prompt para iniciar o ciclo 6".
2. Extract the entire literal prompt from the assistant message. Check heading, cycle number, start and end boundaries. Preserve its content; do not summarize, translate, or rewrite.
3. Before sending, inspect the target ChatGPT user-message history. If that exact prompt was already sent, never send it again. Wait for a response or stop for reconciliation.
4. Find the ACTUAL composer in the target website, identified by its visible/accessibility label ("Pergunte ao ChatGPT") and editable state. Hermes chat editor is NOT the target. Use individual browser_click or browser_type actions to focus/fill it, NEVER browser_batch_actions for a generic click or submit. Re-read the composer and verify exact text equality, not just a tool ACK.
5. Submit once using a single normal browser action. Re-read the conversation to verify an actual new user bubble with the exact prompt. If readback is missing, uncertain, timed out, or reconciliation_required: STOP. Never retry a possible send blindly.
6. Wait for the assistant's new message to finish. Search only the newly completed response for the next continuation prompt. Continue only when a new explicit prompt exists; stop when final completion is explicit. A model's assertion of completion is not a substitute for inspecting the actual response.
7. On reconciliation_required, first request native controller action browser_admissions_recover_safe using the SAME explicit task_id, session_id and run_id. The controller also performs this safe check before every new mutation. Auto-recovery is ONLY for legacy parser-rejected invalid_step or invalid_batch_identity_or_size with ZERO executed steps and no receipts; it never retries a batch. If ready, use a new operation ID and verify the navigation or effect. If still blocked, use browser_admissions_inspect and obtain human Review batch AFTER independent inspection. Closing/reopening a tab, reloading, or restarting the app DOES NOT erase the durable admission fence and must never be suggested as a fix. Operator reconciliation does not prove remote delivery or resend the action. Following restart and reconciliation, navigate only to an exact previously verified conversation URL.
8. Bound polling. Do not switch conversations, generate your own continuation prompts, bypass control policy, or loop forever without a new verified assistant response.

Success: exact prompt appears as a single new user message in the intended ChatGPT conversation, or the workflow safely stops without duplication or unauthorized actions.