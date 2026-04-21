import os
from pathlib import Path
from urllib.parse import quote, unquote

from cryptography.fernet import Fernet
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from pyzotero import Zotero

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent

# Generate or load encryption key
# For production, set ZOTERAG_SECRET_KEY env var
SECRET_KEY = os.getenv("ZOTERAG_SECRET_KEY", Fernet.generate_key().decode())
cipher = Fernet(SECRET_KEY.encode() if isinstance(SECRET_KEY, str) else SECRET_KEY)

def encrypt_credentials(userid: str, apikey: str) -> str:
    """Encrypt userid and apikey into a shareable token."""
    credentials = f"{userid}:{apikey}".encode()
    encrypted = cipher.encrypt(credentials)
    return quote(encrypted.decode())

def decrypt_credentials(token: str) -> tuple[str, str]:
    """Decrypt token back to (userid, apikey)."""
    try:
        encrypted = unquote(token).encode()
        credentials = cipher.decrypt(encrypted).decode()
        userid, apikey = credentials.split(":", 1)
        return userid, apikey
    except Exception:
        raise ValueError("Invalid or tampered token")

@app.get("/", response_class=HTMLResponse)
def main():
    index_html = (BASE_DIR / "index.html").read_text(encoding="utf-8")
    return index_html

@app.post("/get_url/", response_class=HTMLResponse)
async def get_url(userid: str = Form(...), apikey: str = Form(...)):
    token = encrypt_credentials(userid, apikey)
    response_html = (BASE_DIR / "response.html").read_text(encoding="utf-8")
    response_html = response_html.replace("{{token}}", token)
    return response_html

@app.get("/lib/{token}", response_class=HTMLResponse)
def lib(token: str):
    try:
        userid, apikey = decrypt_credentials(token)
    except ValueError:
        return "<h1>Invalid Token</h1><p>The provided token is invalid or has been tampered with.</p>"
    
    try:
        zot = Zotero(userid, "user", apikey)
        # get all items with fulltext and attachments
        # zot.add_parameters(fulltext=True, attachments=True)

        items_html = ""

        # Fetch everything (use with caution on huge libraries)
        all_items = zot.everything(zot.items(q='machine learning'))

        # Separate parents and notes
        parents = {i['key']: i for i in all_items if i['data']['itemType'] != 'note'}
        notes = [i for i in all_items if i['data']['itemType'] == 'note']

        # Map notes to their parents
        for note in notes:
            parent_key = note['data'].get('parentItem')
            if parent_key in parents:
                print(f"Note for '{parents[parent_key]['data']['title']}':")
                print(f" > {note['data']['note']}")






        #items = zot.everything(zot.items())
        '''
        items_html = "<ul>"
        for item in items:
            items_html += f"<li>{item['data']['title']}</li>"
        items_html += "</ul>"
        '''
        items_html = ""
        for item in items:
            #title = item['data'].get('title', 'No Title')
            items_html += f"<article>{item}</article>"

        library_html = (BASE_DIR / "lib.html").read_text(encoding="utf-8")
        library_html = library_html.replace("{{items}}", items_html)
        return library_html
    except Exception as e:
        return f"<h1>Error</h1><p>Failed to retrieve library: {str(e)}</p>"