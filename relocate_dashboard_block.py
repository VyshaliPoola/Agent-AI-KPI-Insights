from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')
start_marker = 'st.markdown("### Group-by Analysis")'
end_marker = '# ---------------------------\n# DRIVER + ANOMALY PIPELINE'
start = text.find(start_marker)
end = text.find(end_marker)
if start == -1 or end == -1:
    raise SystemExit('Markers not found: start=%s end=%s' % (start, end))
block = text[start:end]
text = text[:start] + text[end:]
insert_after = 'st.json(insights)\n\n'
idx = text.find(insert_after)
if idx == -1:
    insert_after = 'st.json(insights["key_findings"])\n\n'
    idx = text.find(insert_after)
if idx == -1:
    raise SystemExit('Insert point not found')
text = text[:idx + len(insert_after)] + block + text[idx + len(insert_after):]
path.write_text(text, encoding='utf-8')
print('Done')
