from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
from api.routes import router as lexer_router
from pathlib import Path

app = FastAPI(title="Analizador léxico y sintáctico para Go")

app.include_router(lexer_router)

@app.get("/", response_class=HTMLResponse)
def read_root():
    html_path = Path(__file__).parent / "templates" / "index.html"
    return html_path.read_text(encoding="utf-8")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)