from pathlib import Path

from web.app import app

CSS_DIR = Path(__file__).resolve().parents[1] / "web" / "static" / "css"


def test_theme_css_existe_y_define_tokens_de_diseno():
    contenido = (CSS_DIR / "theme.css").read_text(encoding="utf-8")

    assert "--color-primary" in contenido
    assert "body.dark" in contenido
    assert "@media (max-width: 768px)" in contenido


def test_accessibility_css_importa_el_tema():
    contenido = (CSS_DIR / "accessibility.css").read_text(encoding="utf-8")

    assert contenido.lstrip().startswith('@import url("theme.css");')


def test_theme_css_se_sirve_desde_flask():
    respuesta = app.test_client().get("/static/css/theme.css")

    assert respuesta.status_code == 200
    assert "text/css" in respuesta.headers.get("Content-Type", "")
