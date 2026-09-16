import html
import io
import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from auth import decode_photo_token
from database import get_db
from models import Product

photo_router = APIRouter(tags=["photo"])

BACKEND_ROOT = Path(__file__).resolve().parent.parent
STATIC_ROOT = BACKEND_ROOT / "static"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_IMAGE_SIDE = 1280


def _html_page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      font-family: system-ui, sans-serif;
      margin: 0;
      padding: 24px 16px;
      background: #F5F7FA;
      color: #111827;
    }}
    .card {{
      max-width: 420px;
      margin: 0 auto;
      background: #fff;
      border-radius: 12px;
      padding: 20px;
      box-shadow: 0 1px 4px rgba(0,0,0,.08);
    }}
    h1 {{ font-size: 1.15rem; margin: 0 0 8px; }}
    p {{ color: #4B5563; line-height: 1.4; }}
    button, label.btn {{
      display: block;
      width: 100%;
      box-sizing: border-box;
      margin-top: 16px;
      padding: 14px;
      border: 0;
      border-radius: 8px;
      background: #2563EB;
      color: #fff;
      font-size: 1rem;
      font-weight: 600;
      text-align: center;
    }}
    button.send {{
      background: #2E7D32;
    }}
    label.btn.gallery {{
      background: #fff;
      color: #2563EB;
      border: 2px solid #2563EB;
    }}
    input[type=file] {{
      position: absolute;
      width: 1px;
      height: 1px;
      opacity: 0;
      overflow: hidden;
    }}
    button:disabled {{
      opacity: 0.6;
    }}
    #status {{
      font-size: 0.95rem;
      color: #111827;
    }}
    .ok {{ background: #2E7D32; }}
  </style>
</head>
<body>
  <div class="card">
    {body}
  </div>
</body>
</html>
"""


def _product_from_token(token: str, db: Session) -> Product:
    payload = decode_photo_token(token)
    product = db.query(Product).filter(
        Product.id == int(payload["product_id"]),
        Product.store_id == int(payload["store_id"]),
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return product


@photo_router.get("/photo/{token}", response_class=HTMLResponse)
async def photo_upload_page(token: str, db: Session = Depends(get_db)):
    try:
        product = _product_from_token(token, db)
    except HTTPException:
        body = """
        <h1>Link expirado ou inválido</h1>
        <p>Gere um QR novo no computador e tente outra vez.</p>
        """
        return HTMLResponse(_html_page("Link inválido", body), status_code=400)
    name = html.escape(product.name)
    body = f"""
    <h1>Foto do produto</h1>
    <p><b>{name}</b></p>
    <p id="status">Tire uma foto agora ou escolha uma da galeria. O envio começa sozinho.</p>
    <form id="photo-form">
      <input id="file-camera" type="file" name="file" accept="image/*" capture="environment">
      <input id="file-gallery" type="file" name="file" accept="image/*">
      <label class="btn" for="file-camera">Tirar foto</label>
      <label class="btn gallery" for="file-gallery">Escolher da galeria</label>
      <button class="btn send" type="button" id="send">Enviar foto</button>
    </form>
    <script>
      const camera = document.getElementById("file-camera");
      const gallery = document.getElementById("file-gallery");
      const status = document.getElementById("status");
      const send = document.getElementById("send");
      let sending = false;

      function chosenFile() {{
        if (camera.files && camera.files.length) return camera.files[0];
        if (gallery.files && gallery.files.length) return gallery.files[0];
        return null;
      }}

      async function upload() {{
        if (sending) return;
        const picked = chosenFile();
        if (!picked) {{
          status.textContent = "Ainda não há foto. Tire uma foto ou escolha da galeria.";
          return;
        }}
        sending = true;
        send.disabled = true;
        status.textContent = "Enviando foto...";
        const data = new FormData();
        data.append("file", picked, picked.name || "foto.jpg");
        try {{
          const res = await fetch(window.location.href, {{
            method: "POST",
            body: data
          }});
          const html = await res.text();
          document.open();
          document.write(html);
          document.close();
        }} catch (err) {{
          sending = false;
          send.disabled = false;
          status.textContent = "Falha de rede ao enviar. Tente Enviar foto de novo.";
        }}
      }}

      camera.addEventListener("change", function () {{
        if (camera.files && camera.files.length) {{
          gallery.value = "";
          status.textContent = "Foto capturada. Enviando...";
          upload();
        }}
      }});
      gallery.addEventListener("change", function () {{
        if (gallery.files && gallery.files.length) {{
          camera.value = "";
          status.textContent = "Foto escolhida. Enviando...";
          upload();
        }}
      }});
      send.addEventListener("click", function (event) {{
        event.preventDefault();
        upload();
      }});
    </script>
    """
    return _html_page("Foto do produto", body)


@photo_router.post("/photo/{token}", response_class=HTMLResponse)
async def photo_upload(
    token: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        product = _product_from_token(token, db)
    except HTTPException:
        body = """
        <h1>Link expirado ou inválido</h1>
        <p>Gere um QR novo no computador e tente outra vez.</p>
        """
        return HTMLResponse(_html_page("Link inválido", body), status_code=400)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Arquivo muito grande (máximo 15 MB)",
        )

    try:
        image = Image.open(io.BytesIO(content))
        image.load()
        transposed = ImageOps.exif_transpose(image)
        if transposed is not None:
            image = transposed
    except Exception:
        body = """
        <h1>Não foi possível ler a imagem</h1>
        <p>Tente de novo em JPEG ou PNG. No iPhone, desative
        &quot;High Efficiency&quot; nas câmeras se a foto não abrir.</p>
        """
        return HTMLResponse(_html_page("Erro na foto", body), status_code=400)

    if image.mode != "RGB":
        image = image.convert("RGB")
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))

    relative = f"products/{product.store_id}/{product.id}_{int(time.time())}.jpg"
    dest = STATIC_ROOT / relative
    dest.parent.mkdir(parents=True, exist_ok=True)

    old_path = product.image_path
    image.save(dest, format="JPEG", quality=85, optimize=True)

    if old_path:
        old_file = STATIC_ROOT / old_path
        if old_file.is_file() and old_file != dest:
            try:
                old_file.unlink()
            except OSError:
                pass

    product.image_path = relative.replace("\\", "/")
    db.commit()

    name = html.escape(product.name)
    body = f"""
    <h1 class="ok" style="background:none;color:#2E7D32;padding:0">Foto salva</h1>
    <p>A foto de <b>{name}</b> já está no computador. Pode fechar esta página.</p>
    """
    return _html_page("Foto salva", body)
