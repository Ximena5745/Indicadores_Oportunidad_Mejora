# Fase 3 — Despliegue rápido del prototipo

Opciones para ejecutar el prototipo en un entorno de pruebas o staging.

1) Ejecutar localmente (rápido)

```bash
python -m venv .venv
source .venv/bin/activate  # o .venv\Scripts\activate en Windows
pip install -r requirements.txt
streamlit run scripts/prototipo_nivel3.py
```

2) Ejecutar en un contenedor Docker (opcional)

Dockerfile (sugerido):

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "scripts/prototipo_nivel3.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Construir y ejecutar:

```bash
docker build -t sgind-prototipo:latest .
docker run -p 8501:8501 sgind-prototipo:latest
```

3) Dependencias opcionales
- `python-pptx` para exportar PPTX.
- `kaleido` para exportar imágenes Plotly a PNG (requerido por python-pptx export en algunos entornos).

Seguridad y notas
- Asegura acceso restringido al entorno de despliegue (datos sensibles). El prototipo usa archivos locales; para producción considerar un almacén seguro (S3/Blob) y autenticación.
