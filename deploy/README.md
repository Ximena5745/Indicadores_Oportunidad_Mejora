# Despliegue en la nube - Opciones de prueba

Opciones rápidas para desplegar la interfaz para pruebas en cloud.

1) Streamlit Community Cloud (recomendado para prototipos)
   - Crear un repositorio en GitHub con este código.
   - Conectar el repo en https://streamlit.io/cloud y crear una nueva aplicación con estas opciones:
     - **Branch:** `main` (o la rama que uses)
     - **Main file path:** `streamlit_app/main.py`
     - **Requirements file path:** `requirements.txt` (también funciona `streamlit_app/requirements.txt` si prefieres mantener dependencias aisladas)
     - Opcional: en *Advanced settings* establecer `Headless` y variables de entorno si necesitas secretos.

   Nota: hemos incluido un `requirements.txt` en la raíz para que Streamlit Cloud instale las dependencias automáticamente.

2) Usando Docker (Render, Azure Container Instances, Heroku Container Registry)
   - Construir localmente:
     ```bash
     docker build -t sistema-indicadores:latest .
     docker run -p 8501:8501 sistema-indicadores:latest
     ```
   - Subir a GHCR (workflow ya incluido): pushea a `main` o `master` para que GitHub Actions suba la imagen a `ghcr.io/<owner>/<repo>:latest`.
   - En Render o Azure, crear un servicio de tipo *Web Service/Container* apuntando al contenedor de GHCR.

3) Deploy rápido con `docker-compose` (pruebas en servidor)
   ```bash
   docker-compose up --build
   ```

Notas:
- Asegúrate de configurar secretos si usas otro registry (Docker Hub): `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN`.
- El `Dockerfile` expone el puerto `8501` y el comando por defecto ejecuta `streamlit run streamlit_app/main.py`.
