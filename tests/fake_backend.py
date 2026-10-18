"""Local subprocess fixture. Never contacts an AI provider."""
import json
import sys

cli, model, agent = sys.argv[1:]
prompt = sys.stdin.read() if cli == "codex" else ""
if cli == "codex" and ("RFP" not in prompt or "supplied" not in prompt):
    raise SystemExit("Missing Codex profile or prompt on stdin")
answer = ({"agents": [
    {"stage": stage, "description": "Offline test specialist",
     "instructions": "Analyse only the supplied RFP, cite its exact source anchors and return the required JSON contract."}
    for stage in ("discovery", "architecture", "audit")]}
    if "designer" in agent else {})
text = json.dumps(answer)
if cli == "claude":
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False,
                      "result": text, "modelUsage": {model: {}}, "usage": {}}))
elif cli == "codex":
    print(json.dumps({"type": "thread.started", "thread_id": "offline"}))
    print(json.dumps({"type": "item.completed",
                      "item": {"id": "a1", "type": "agent_message", "text": text}}))
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 42, "output_tokens": 10}}))
else:
    print(json.dumps({"type": "assistant.message", "data": {"content": text, "model": model}}))
