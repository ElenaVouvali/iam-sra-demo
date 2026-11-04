from pathlib import Path
import runpy
import pytest
validate=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/chat-qr.py'))['public_chat_url']

@pytest.mark.parametrize('url',['http://localhost/chat','http://127.0.0.2/chat','http://[::1]/chat','https://example.org/chat?session=abc','https://user:secret@example.org/chat','https://example.org/sessions/abc',''])
def test_qr_rejects_local_or_session_bearing_urls(url):
    with pytest.raises(ValueError):validate(url)

def test_qr_ordinary_entry_url_only():assert validate('https://example.org/chat')=='https://example.org/chat'
