import json
import re
import sys
import zipfile
from pathlib import Path

zip_path, out_dir = sys.argv[1], Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)
z = zipfile.ZipFile(zip_path)
raw = z.read('transcript.jsonl')
(out_dir / 'transcript.jsonl').write_bytes(raw)
(out_dir / 'session-metadata.json').write_bytes(z.read('metadata.json'))

SKIP_USER = re.compile(r'^\s*<(system-reminder|task-notification|command-name|local-command)', re.S)


def clean(text):
    return text.replace('[[', '[ [').replace(']]', '] ]')


def summarise_tool(block):
    name = block.get('name', '?')
    data = block.get('input') or {}
    detail = data.get('description') or data.get('command') or data.get('file_path') or data.get('pattern') or data.get('query') or data.get('url') or data.get('skill') or ''
    detail = ' '.join(str(detail).split())[:170]
    if name in ('Write', 'Edit'):
        detail = data.get('file_path', '')
    return '- `%s` %s' % (name, detail)


turns, tools_buffer = [], []


def flush_tools():
    global tools_buffer
    if tools_buffer:
        turns.append('<details><summary>%d actions</summary>\n\n%s\n\n</details>' % (len(tools_buffer), '\n'.join(tools_buffer)))
        tools_buffer = []


user_count = reply_count = 0
for line in raw.decode('utf-8').splitlines():
    try:
        entry = json.loads(line)
    except ValueError:
        continue
    kind = entry.get('type')
    message = entry.get('message') or {}
    if kind == 'user' and not entry.get('isSidechain'):
        content = message.get('content')
        if isinstance(content, list):
            parts = [b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text']
            content = '\n'.join(parts)
        if not isinstance(content, str) or not content.strip():
            continue
        if SKIP_USER.match(content):
            if '<task-notification>' in content:
                flush_tools()
                turns.append('> *(automatic notification: a background command finished)*')
            continue
        flush_tools()
        user_count += 1
        turns.append('## المستخدم — رسالة %d\n\n%s' % (user_count, clean(content.strip())))
    elif kind == 'assistant' and not entry.get('isSidechain'):
        for block in message.get('content') or []:
            if not isinstance(block, dict):
                continue
            if block.get('type') == 'text' and block.get('text', '').strip():
                flush_tools()
                reply_count += 1
                turns.append('### Claude\n\n%s' % clean(block['text'].strip()))
            elif block.get('type') == 'tool_use':
                tools_buffer.append(summarise_tool(block))
flush_tools()

head = '''---
title: Conversation (readable)
type: raw
tags: [ai-memory, raw]
updated: 2026-11-14
---

# Conversation, readable form

Generated from the exported session transcript (`transcript.jsonl` beside this file). Contains every message from the user and every reply from Claude, in order, with each run of tool actions folded into a one-line-per-action list. Tool *output* (file contents, test logs) is omitted; the full raw data is in `transcript.jsonl`.

Wikilink brackets inside quoted text were escaped (`[ [`) so Obsidian does not treat them as links. %d user messages, %d replies.

---

''' % (user_count, reply_count)
(out_dir / 'Conversation (readable).md').write_bytes((head + '\n\n'.join(turns) + '\n').encode('utf-8'))
print('user messages', user_count, 'replies', reply_count, 'chars', sum(len(t) for t in turns))
