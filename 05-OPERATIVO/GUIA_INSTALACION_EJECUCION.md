# Guía de Instalación y Ejecución - SGIND

**Documento:** GUIA_INSTALACION_EJECUCION.md  
**Versión:** 1.0  
**Última actualización:** 11 de abril de 2026  
**Audiencia:** Desarrolladores, DevOps, administradores técnicos

---

## Tabla de Contenidos

1. [Requisitos del Sistema](#requisitos-del-sistema)
2. [Instalación Local](#instalación-local)
3. [Instalación con Docker](#instalación-con-docker)
4. [Configuración del Entorno](#configuración-del-entorno)
5. [Ejecución del Pipeline](#ejecución-del-pipeline)
6. [Ejecución del Dashboard](#ejecución-del-dashboard)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)
9. [Despliegue a Producción](#despliegue-a-producción)

---

## Requisitos del Sistema

### Software Requerido

| Componente | Versión | Propósito |
|-----------|---------|----------|
| **Python** | 3.10+ | Runtime |
| **Git** | 2.30+ | Control de versiones |
| **pip** | 23+  | Gestor paquetes Python |
| **PostgreSQL** | 14+ | BD producción (opcional) |
| **Docker** | 20.10+ | Contenedorización (optional) |
| **Docker Compose** | 1.29+ | Orquestación (optional) |

### Hardware Mínimo (Desarrollo)

```
├─ CPU: 2 núcleos (mínimo), 4 recomendado
├─ RAM: 4 GB (mínimo), 8 GB recomendado
├─ Disco: 5 GB disponibles (datos + códig + caches)
└─ Red: Conexión a internet para APIs externas
```

### Puertos Requeridos

```
8501  ← Streamlit app (local development)
8000  ← Backend API (futuro)
5432  ← PostgreSQL (si usar remoto)
3000  ← PgAdmin (si usar Docker)
```

---

## Instalación Local

### 1. Clonar Repositorio (2 minutos)

```bash
# Navegar a directorio de trabajo
cd /path/to/workspace

# Clonar repo
git clone https://github.com/poli/sistema-indicadores.git
cd sistema-indicadores

# Verificar rama correcta
git branch -a
git checkout main  # o develop si en desarrollo
```

### 2. Crear Entorno Virtual (3 minutos)

#### En Windows (PowerShell)

```powershell
# Crear entorno virtual
python -m venv .venv

# Activar entorno
.venv\Scripts\Activate.ps1

# Verificar (debe mostrar (.venv))
python --version
pip --version
```

#### En Linux/Mac

```bash
# Crear entorno virtual
python3 -m venv .venv

# Activar entorno
source .venv/bin/activate

# Verificar
python --version
pip --version
```

### 3. Instalar Dependencias (5-10 minutos)

```bash
# Actualizar pip
pip install --upgrade pip setuptools wheel

# Instalar dependencias principales
pip install -r requirements.txt

# Instalar dependencias de desarrollo (opcional, para testing)
pip install -r requirements-dev.txt

# Verificar instalación
pip list | grep streamlit
pip list | grep pandas
pip list | grep sqlalchemy
```

**Output esperado:**
```
streamlit              1.36.0
pandas                 2.2.2
plotly                 5.22.0
openpyxl               3.1.4
sqlalchemy             2.0.25
psycopg2-binary        2.9.9
anthropic              0.40.0
```

### 4. Configurar Variables de Entorno (2 minutos)

```bash
# Copiar template
cp .env.example .env

# Editar .env según tu entorno
nano .env
# o en Windows: notepad .env
```

**Contenido mínimo (.env):**

```ini
# Database configuration (Desarrollo)
DATABASE_URL=sqlite:///data/db/registros_om.db

# Or PostgreSQL (Producción)
# DATABASE_URL=postgresql://user:password@localhost:5432/sgind

# Streamlit configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_HEADLESS=false

# API Keys (si necesario para búsqueda/IA futura)
OPENAI_API_KEY=sk-xxxxx (optional)
ANTHROPIC_API_KEY=sk-ant-xxxxx (optional)

# Debug mode
DEBUG=false
LOG_LEVEL=INFO
```

### 5. Verificar Instalación (2 minutos)

```bash
# Verificar estructura directorios
ls -la

# Verificar archivos críticos
test -f config/settings.toml && echo "✓ config/settings.toml"
test -f requirements.txt && echo "✓ requirements.txt"
test -f streamlit_app/main.py && echo "✓ streamlit_app/main.py"
test -d data/raw && echo "✓ data/ directory"
test -d tests && echo "✓ tests/ directory"

# Verificar Python
python -c "import streamlit; print('Streamlit OK')"
python -c "import pandas; print('Pandas OK')"
python -c "import plotly; print('Plotly OK')"
```

**Expected output:**
```
✓ config/settings.toml
✓ requirements.txt
✓ streamlit_app/main.py
✓ data/ directory
✓ tests/ directory
Streamlit OK
Pandas OK
Plotly OK
```

---

## Instalación con Docker

### 1. Verificar Docker (1 minuto)

```bash
docker --version   # Docker version 20.10+
docker-compose --version  # Docker Compose 1.29+
```

### 2. Configurar Docker Compose (2 minutos)

```bash
# Revisar docker-compose.yml
cat docker-compose.yml

# Estructura esperada:
# services:
#   app:
#     build: .
#     ports: ["8501:8501"]
#   postgres:
#     image: postgres:14
#     environment: [POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD]
```

### 3. Construir y Ejecutar (10-15 minutos)

```bash
# Opción A: Build + Run en background
docker-compose up -d

# Opción B: Build + Run en foreground (ver logs)
docker-compose up --build

# Verificar contenedores
docker-compose ps

# Ver logs
docker-compose logs -f app
docker-compose logs -f postgres
```

**Expected output:**
```
Creating sgind_postgres_1 ... done
Creating sgind_app_1 ... done

app_1       |   You can now view your Streamlit app in your browser.
app_1       |   URL: http://localhost:8501
```

### 4. Acceder a la Aplicación

```bash
# Abrir en navegador
open http://localhost:8501  # macOS
xdg-open http://localhost:8501  # Linux
start http://localhost:8501  # Windows

# O via curl
curl http://localhost:8501
```

### 5. Detener Servicios

```bash
# Parar contenedores
docker-compose down

# Parar + eliminar volúmenes (CUIDADO: borra datos!)
docker-compose down -v
```

---

## Configuración del Entorno

### Settings Principales (config/settings.toml)

```toml
[General]
nombre_institucion = "Politécnico Grancolombiano"
anio_actual = 2026
anio_inicio = 2022

[ETL]
año_cierre_actual = 2026
ruta_kawak = "data/raw/Kawak"
ruta_api = "data/raw/API"
ruta_salida = "data/raw/Fuentes Consolidadas"
ruta_output = "data/output"

[Validaciones]
# Umbrales de cumplimiento
umbral_peligro = 0.80
umbral_alerta = 1.00
umbral_sobrecumplimiento = 1.05
umbral_plan_anual = 0.95  # Especial para IDs de Plan Anual

# Validaciones de data
meta_minima = 0.1  # Meta debe ser > 0.1
ejecucion_minima = 0.0  # Ejecución puede ser 0 pero no negativa

[Cache]
ttl_consolidado = 300  # 5 minutos (estándar global)
ttl_catalogo = 600  # 10 minutos
ttl_mapa = 300  # 5 minutos

[Base de Datos]
tabla_om = "registros_om"
tabla_historico = "consolidado_historico"
tabla_semestral = "consolidado_semestral"

[Logging]
nivel = "INFO"
archivo = "artifacts/pipeline.log"
formato = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### Mapeos Especiales (core/config.py)

```python
# Plan Anual - Cumple desde 95% (no 100%)
IDS_PLAN_ANUAL = frozenset([
    373, 390, 414, 415, 416, 417, 418, 419, 420, 469, 470, 471
])

# Indicadores con tope 100% (no permiten sobrecumplimiento)
IDS_TOPE_100 = frozenset([208, 218])
```

**Para editar estos valores:**
```python
# core/config.py
# Localizar: IDS_PLAN_ANUAL y IDS_TOPE_100
# Agregar/remover IDs según necesidad
# Guardar y reiniciar dashboard
```

### Variables de Entorno Importantes

```bash
# Desarrollo (SQLite local)
DATABASE_URL=sqlite:///data/db/registros_om.db

# Producción (PostgreSQL en Render)
DATABASE_URL=postgresql://user:pass@db.render.com:5432/sgind

# Streamlit
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_SERVER_ENABLECORS=false

# Logging
LOG_LEVEL=INFO
DEBUG=false
```

---

## Ejecución del Pipeline

### Flujo Normal (Paso a Paso)

```bash
# Activar entorno virtual PRIMERO
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\Activate.ps1  # Windows

# Opción 1: Ejecutar pipeline completo (recomendado)
python scripts/run_pipeline.py

# Output esperado:
# [2026-04-11 07:00:00] INFO - Iniciando pipeline...
# [2026-04-11 07:00:05] INFO - Paso 1: consolidar_api.py...
# [2026-04-11 07:01:15] INFO - ✓ Consolidado_API_Kawak.xlsx generado
# [2026-04-11 07:01:20] INFO - Paso 2: actualizar_consolidado.py...
# [2026-04-11 07:05:30] INFO - ✓ Resultados Consolidados.xlsx generado
# [2026-04-11 07:05:35] INFO - Paso 3: generar_reporte.py...
# [2026-04-11 07:06:20] INFO - ✓ Seguimiento_Reporte.xlsx generado
# [2026-04-11 07:06:25] INFO - Pipeline completado: 6 minutos 25 segundos
# [2026-04-11 07:06:26] INFO - QA Report: artifacts/pipeline_run_20260411_070000.json
```

### Ejecución Individual de Pasos

**Paso 1: Consolidar API (si solo necesitas actualizar histórico)**

```bash
python scripts/consolidar_api.py

# Verificar salida
ls -lh data/raw/Fuentes\ Consolidadas/
# Esperado: 
#   Consolidado_API_Kawak.xlsx (5-10 MB)
#   Indicadores_Kawak.xlsx (50 KB)
```

**Paso 2: Actualizar Consolidado (motor ETL principal)**

```bash
python scripts/actualizar_consolidado.py

# Verificar salida
ls -lh data/output/
# Esperado:
#   Resultados Consolidados.xlsx (15-20 MB)
#   Consolidado Historico/Semestral/Cierres hojas
```

**Paso 3: Generar Reporte**

```bash
python scripts/generar_reporte.py

# Verificar salida
ls -lh data/output/
# Esperado:
#   Seguimiento_Reporte.xlsx (2-5 MB)
```

### Ejecución Programada (Automatización)

#### En Linux/Mac (cron)

```bash
# Abrir crontab
crontab -e

# Agregar línea (ejecutar 06:00 AM cada día)
0 6 * * * cd /home/user/sistema-indicadores && python scripts/run_pipeline.py >> /var/log/sgind_pipeline.log 2>&1

# Verificar cron activo
crontab -l | grep "run_pipeline"
```

#### En Windows (Task Scheduler)

```powershell
# 1. Abrir Task Scheduler
tasksched.msc

# 2. New Basic Task:
#    Name: "SGIND Daily Pipeline"
#    Trigger: Daily at 06:00
#    Action: 
#      Program: C:\Users\user\.venv\Scripts\python.exe
#      Arguments: C:\Users\user\sistema-indicadores\scripts\run_pipeline.py
#      Start in: C:\Users\user\sistema-indicadores\

# 3. Clic OK
```

#### En Docker (usar cron image)

```dockerfile
# Dockerfile.cron
FROM system-indicadores:latest

# Instalar cron
RUN apt-get update && apt-get install -y cron

# Copiar cron job
COPY cron/pipeline.cron /etc/cron.d/pipeline
RUN chmod 0644 /etc/cron.d/pipeline

# Ejecutar cron
CMD ["cron", "-f"]
```

```bash
docker build -f Dockerfile.cron -t sgind-cron .
docker run -d sgind-cron
```

---

## Ejecución del Dashboard

### Iniciar Streamlit

```bash
# Terminal 1: Activar entorno
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\Activate.ps1  # Windows

# Ejecutar
streamlit run streamlit_app/main.py

# Output:
#   You can now view your Streamlit app in your browser.
#   URL: http://localhost:8501
```

### Acceder al Dashboard

```bash
# Opción 1: Abrir en navegador
curl http://localhost:8501

# Opción 2: Manual
open http://localhost:8501  # macOS
xdg-open http://localhost:8501  # Linux
start http://localhost:8501  # Windows
```

### Navegar Páginas Disponibles

```
Sidebar (Izquierda):
├─ 📊 Resumen General        [MAIN]
├─ 📈 CMI Estratégico         [Strategic]
├─ ✅ Plan Mejoramiento       [OMs]
└─ 🔍 Resumen por Proceso     [Drill-down]

Funcionalidades por página:
├─ Resumen General:
│  ├─ KPIs principales
│  ├─ Filtros avanzados
│  ├─ Tabla consolidado + Exportar
│  ├─ Gráficos histórico/tendencias
│  └─ Drill-down indicador → Modal
│
├─ CMI Estratégico:
│  ├─ 4 perspectivas (Financiero, Procesos, Aprendizaje, Cliente)
│  ├─ Trendlines
│  └─ Scatter plot
│
├─ Plan Mejoramiento:
│  ├─ Tabla OMs
│  ├─ Botón "+ Nueva OM"
│  ├─ Editar estado/descripción
│  └─ Cerrar exitosa o retrasada
│
└─ Resumen por Proceso:
   ├─ Seleccionar proceso
   ├─ Heatmap Subproceso × Período
   ├─ Drill-down a indicadores
   └─ Gráficos de riesgo
```

### Configuración de Streamlit (local)

```bash
# Crear .streamlit/config.toml (si no existe)
mkdir -p .streamlit
cat > .streamlit/config.toml << 'EOF'
[theme]
primaryColor = "#43A047"
backgroundColor = "#F8F9FA"
secondaryBackgroundColor = "#E8E8E8"
textColor = "#262730"
font = "sans serif"

[client]
showErrorDetails = true
toolbarMode = "developer"

[server]
port = 8501
enableCORS = false
maxUploadSize = 100

[logger]
level = "info"
EOF
```

### Troubleshooting Dashboard

**Problema: "No such file or directory: 'Resultados Consolidados.xlsx'"**

```bash
# Solución: Ejecutar pipeline primero
python scripts/run_pipeline.py
# Luego recargar Streamlit (Ctrl+F5)
```

**Problema: "ModuleNotFoundError: No module named 'streamlit'"**

```bash
# Solución: Verificar entornode virtual activo
which python  # Debe apuntar a .venv/bin/python
source .venv/bin/activate  # Re-activar
pip install streamlit
```

**Problema: Dashboard muestra datos viejos (>5 minutos)"**

```python
# Streamlit caché expiró pero no se relleyó automáticamente
# Solución: Presionar Ctrl+C en terminal + reiniciar
# O en dashboard: R (rerun)
```

---

## Testing

### Ejecutar Suite de Tests

```bash
# Terminal: Asegurarse que .venv está activo
source .venv/bin/activate

# Ejecutar TODOS los tests
pytest tests/ -v

# Ejecutar solo tests de calculos
pytest tests/test_calculos.py -v

# Ejecutar solo tests de validación visual
pytest tests/test_visual_validation.py -v

# Con cobertura
pytest tests/ --cov=core --cov=services --cov-report=html
```

**Output esperado:**

```
tests/test_calculos.py::test_normalizar_cumplimiento PASSED
tests/test_calculos.py::test_categorizar_cumplimiento PASSED
tests/test_calculos.py::test_categorizar_plan_anual PASSED
...
========================= 50 passed in 2.34s ==========================
```

### Tests Incluidos

| Test | Archivo | Cobertura |
|------|---------|-----------|
| Normalización cumplimiento | test_calculos.py | normalizar_cumplimiento() |
| Categorización (estándar + especiales) | test_calculos.py | categorizar_cumplimiento() |
| Cálculo tendencias | test_calculos.py | calcular_tendencia() |
| Generación recomendaciones | test_calculos.py | generar_recomendaciones() |
| Validación artefactos | test_visual_validation.py | Estructura Excel outputs |

### Agregar Nuevos Tests

```python
# tests/test_mi_feature.py
import pytest
from core.calculos import mi_funcion

def test_mi_funcion_caso_normal():
    """Descripción del test."""
    resultado = mi_funcion(input_valor)
    assert resultado == resultado_esperado

def test_mi_funcion_caso_error():
    """Test de error handling."""
    with pytest.raises(ValueError):
        mi_funcion(input_invalido)

# Ejecutar
pytest tests/test_mi_feature.py -v
```

---

## Troubleshooting

### Problemas Comunes

#### 1. ModuleNotFoundError: No module named X

```bash
# Verificar entorno virtual activo
which python
# Debe mostrar: /path/to/.venv/bin/python

# Si NO está activo:
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\Activate.ps1  # Windows

# Reinstalar dependencias
pip install -r requirements.txt
```

#### 2. PostgreSQL Connection Refused

```bash
# Si DATABASE_URL apunta a PostgreSQL pero no está disponible

# Solución 1: Usar SQLite (desarrollo)
export DATABASE_URL="sqlite:///data/db/registros_om.db"
streamlit run streamlit_app/main.py

# Solución 2: Verificar PostgreSQL está corriendo
docker ps | grep postgres
# Si NO está:
docker-compose up postgres -d

# Solución 3: Verificar credenciales en .env
cat .env | grep DATABASE_URL
# Formato: postgresql://user:password@host:port/database
```

#### 3. "Excel file is corrupted" error

```bash
# Causa: Script falló mid-write
# Solución: Eliminar archivo corrupto y regenerar

rm data/output/Resultados\ Consolidados.xlsx
python scripts/run_pipeline.py
```

#### 4. Streamlit caché desincronizado

```bash
# Síntomas: Dashboard muestra datos viejos (>5 min)
# Solución: Forzar recarga

# EN TERMINAL:
Ctrl+C  # Detener Streamlit
streamlit run streamlit_app/main.py  # Reiniciar

# O EN DASHBOARD:
# Presionar R (rerun)
# O presionar Ctrl+F5 (hard refresh)
```

#### 5. Out of Memory durante pipeline

```bash
# Si datos muy grandes (>1 GB)

# Optimización 1: Aumentar swap (Linux)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Optimización 2: Procesar en chunks
# Editar scripts/etl/builders.py:
# chunk_size = 10000  # Procesar por 10k registros

# Optimización 3: Docker con más RAM
docker-compose up -m 8g
```

---

## Despliegue a Producción

### Requisitos Pre-deployment

- [ ] Todos los tests pasando (`pytest tests/ -v`)
- [ ] Credenciales de BD en .env (PostgreSQL)
- [ ] CORS/Security headers configurados
- [ ] Certificados SSL/TLS listos
- [ ] Backup plan establecido

### Opción 1: Deploy en Render.com

```bash
# 1. Conectar GitHub
# → Settings → Connections → Connect your GitHub account

# 2. Crear nuevo Web Service
# → Dashboard → New → Web Service
# → Seleccionar repo: sistema-indicadores

# 3. Configuración
# Name: sgind-prod
# Environment: Python 3
# Region: US (Ohio)
# Branch: main
# Build Command: pip install -r requirements.txt
# Start Command: streamlit run streamlit_app/main.py

# 4. Environment Variables
# DATABASE_URL: postgresql://...
# STREAMLIT_SERVER_HEADLESS: true
# LOG_LEVEL: WARNING

# 5. Deploy
# Click "Deploy" → Esperar 5-10 minutos
```

### Opción 2: Deploy Manual en VM/VPS

```bash
# 1. SSH a servidor
ssh user@production.server.com

# 2. Clonar repo
cd /opt
git clone https://github.com/poli/sistema-indicadores.git
cd sistema-indicadores

# 3. Configurar
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env con credenciales PROD

# 4. Usar systemd para Streamlit
sudo cat > /etc/systemd/system/sgind.service << 'EOF'
[Unit]
Description=SGIND Dashboard
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/sistema-indicadores
Environment="PATH=/opt/sistema-indicadores/.venv/bin"
ExecStart=/opt/sistema-indicadores/.venv/bin/streamlit run streamlit_app/main.py --server.port=8501 --logger.level=warning
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 5. Iniciar servicio
sudo systemctl daemon-reload
sudo systemctl enable sgind
sudo systemctl start sgind
sudo systemctl status sgind

# 6. Verificar
curl http://localhost:8501
```

### Opción 3: Deploy con Docker en Kubernetes

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sgind-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sgind
  template:
    metadata:
      labels:
        app: sgind
    spec:
      containers:
      - name: streamlit
        image: gcr.io/poli/sgind-app:latest
        ports:
        - containerPort: 8501
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: sgind-secrets
              key: database-url
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
---
apiVersion: v1
kind: Service
metadata:
  name: sgind-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8501
  selector:
    app: sgind
```

```bash
# Deploy
kubectl apply -f kubernetes/deployment.yaml
kubectl get pods
kubectl logs -f pod/sgind-app-xxxxx
```

### Configuración de Nginx (Reverse Proxy)

```nginx
# /etc/nginx/sites-available/sgind
upstream sgind_app {
    server 127.0.0.1:8501;
}

server {
    listen 80;
    listen [::]:80;
    server_name sgind.poli.edu.co;

    # Redirect HTTP → HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name sgind.poli.edu.co;

    ssl_certificate /etc/letsencrypt/live/sgind.poli.edu.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sgind.poli.edu.co/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://sgind_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support para Streamlit
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# Activar
sudo ln -s /etc/nginx/sites-available/sgind /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Certificado SSL (Let's Encrypt)
sudo certbot certonly --nginx -d sgind.poli.edu.co
```

### Monitoreo en Producción

```bash
# Ver logs
journalctl -u sgind -f
tail -f /var/log/sgind_pipeline.log

# Health check
curl -s http://localhost:8501/health || echo "DOWN"

# Uptime monitoring (Sentry, DataDog, etc)
# Integrar con tools de APM
```

---

## Checklists

### Pre-Launch Checklist

- [ ] Tests pasando (pytest -v)
- [ ] Pipeline ejecutando sin errores
- [ ] Dashboard carga correctamente
- [ ] BD respaldada
- [ ] Documentación actualizada
- [ ] Team capacitado
- [ ] Runbook creado

### Post-Launch Checklist

- [ ] Monitorear logs por 24h
- [ ] Validar correctitud de datos
- [ ] Obtener feedback de usuarios
- [ ] Arreglar bugs reportados
- [ ] Documentar lecciones aprendidas

---

## Soporte y Recursos

### Contactos

- **Tech Lead:** biinstitucional@poli.edu.co
- **GitHub Issues:** https://github.com/poli/sistema-indicadores/issues
- **Documentation:** /docs/

### Archivos de Configuración

- `.env.example` → Variables de entorno
- `config/settings.toml` → Umbrales, rutas, validaciones
- `core/config.py` → Constantes, colores, mapeos
- `.streamlit/config.toml` → Tema y comportamiento UI
- `docker-compose.yml` → Stack de contenedores
- `Dockerfile` → Imagen Docker

### Logs Útiles

```bash
# Pipeline
tail -f artifacts/pipeline_run_*.log

# Streamlit
# Directamente en console (Ctrl+C para ver)

# PostgreSQL (si usar Docker)
docker-compose logs postgres
```

---

**Última actualización:** 11 de abril de 2026  
**Next Review:** 15 de mayo de 2026  
**Maintainer:** Equipo de BI Institucional
