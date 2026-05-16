from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
import io
import os
import pyautogui
import pygetwindow as gw
import pyperclip
import time

load_dotenv()

TOKEN = os.getenv('REMOTIFY_TOKEN', 'change-me')
WINDOW_TITLE = os.getenv('TARGET_WINDOW_TITLE', 'Codex')

app = FastAPI(title='Remotify')
app.mount('/static', StaticFiles(directory='app/static'), name='static')


class SendRequest(BaseModel):
    text: str
    press_enter: bool = True


class ClickRequest(BaseModel):
    x: float
    y: float
    display_width: float
    display_height: float



def validate_token(request: Request):
    token = request.query_params.get('token')
    if token != TOKEN:
        raise HTTPException(status_code=401, detail='Invalid token')



def get_window():
    windows = gw.getWindowsWithTitle(WINDOW_TITLE)

    if not windows:
        raise HTTPException(status_code=404, detail=f'Window not found: {WINDOW_TITLE}')

    win = windows[0]

    if win.isMinimized:
        win.restore()

    return win


@app.get('/', response_class=HTMLResponse)
def index():
    with open('app/static/index.html', 'r', encoding='utf-8') as f:
        return f.read()


@app.get('/api/health')
def health():
    return {'status': 'ok'}


@app.post('/api/focus')
def focus(request: Request):
    validate_token(request)

    win = get_window()
    win.activate()

    return {'success': True}


@app.get('/api/screenshot')
def screenshot(request: Request):
    validate_token(request)

    win = get_window()

    img = pyautogui.screenshot(
        region=(win.left, win.top, win.width, win.height)
    )

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    return StreamingResponse(buf, media_type='image/png')


@app.post('/api/send')
def send_text(payload: SendRequest, request: Request):
    validate_token(request)

    win = get_window()
    win.activate()

    time.sleep(0.2)

    pyperclip.copy(payload.text)
    pyautogui.hotkey('ctrl', 'v')

    if payload.press_enter:
        time.sleep(0.1)
        pyautogui.press('enter')

    return {
        'success': True,
        'text_length': len(payload.text)
    }


@app.post('/api/click')
def click(payload: ClickRequest, request: Request):
    validate_token(request)

    win = get_window()

    real_x = win.left + (payload.x / payload.display_width) * win.width
    real_y = win.top + (payload.y / payload.display_height) * win.height

    pyautogui.click(real_x, real_y)

    return {
        'success': True,
        'real_x': real_x,
        'real_y': real_y
    }


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        'app.main:app',
        host=os.getenv('HOST', '127.0.0.1'),
        port=int(os.getenv('PORT', '8765')),
        reload=True
    )
