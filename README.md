# FoodExpress Market (Flask + MySQL)

Proyecto tipo marketplace con roles:
- cliente (ver puestos, menú, carrito, pedidos)
- vendedor (crear puesto, agregar/editar productos)
- repartidor (aceptar pedidos y cambiar estado)

## 1) Requisitos
- Python 3.10+
- MySQL
- Un hosting que soporte WSGI (Render/Railway/VPS con gunicorn)

## 2) Dependencias
Se instalan con:
```bash
pip install -r requirements.txt
```

## 3) Base de datos
1. Crea una BD usando el script:
   - `foodexpress_market.sql`
2. Asegura que exista la BD `foodexpress_market`.

## 4) Variables de entorno (obligatorias en hosting)
Configura estas variables en tu plataforma:

- `FLASK_SECRET_KEY` (ej: una cadena larga aleatoria)
- `MYSQL_HOST` (ej: `localhost` o el host del servidor MySQL en producción)
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DB` (ej: `foodexpress_market`)

> Ejemplo local (opcional): crea un archivo `.env` y cárgalo según tu sistema de despliegue.

## 5) Cómo ejecutar
En local (desarrollo):
```bash
python wsgi.py
```

En hosting WSGI (Render/Railway/VPS) normalmente configurarán el entrypoint como:
- `wsgi:app`

y/o pasar el comando con `gunicorn`, por ejemplo:

```bash
gunicorn -w 2 -b 0.0.0.0:${PORT} wsgi:app
```


## 6) Archivos subidos
Las imágenes se guardan en `foodexpress/static/uploads/` (según la configuración actual).
En producción asegúrate de que el directorio exista y sea persistente si tu hosting es efímero.

