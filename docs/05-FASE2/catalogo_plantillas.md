# Catálogo de Plantillas - Sistema de Indicadores SGIND

## 1. Resumen de fuentes de datos

| Fuente | Ubicación | Formato | Periodicidad | Estado |
|--------|-----------|---------|--------------|--------|
| Acciones de Mejora | `data/raw/acciones_mejora.xlsx` | Excel | - | Activo |
| Dataset Unificado | `data/raw/Dataset_Unificado.xlsx` | Excel | - | Activo |
| Ficha Técnica | `data/raw/Ficha_Tecnica.xlsx` | Excel | - | Activo |
| Indicadores por CMI | `data/raw/Indicadores por CMI.xlsx` | Excel | - | Activo |
| LMI Reporte | `data/raw/lmi_reporte.xlsx` | Excel | - | Activo |
| OM | `data/raw/OM.xlsx` | Excel | - | Activo |
| Resultados Consolidados | `data/output/Resultados Consolidados.xlsx` | Excel | - | Activo |
| Salidas No Conformes | `data/raw/salidas_no_conformes.xlsx` | Excel | - | Activo |
| Subproceso-Proceso-Area | `data/raw/Subproceso-Proceso-Area.xlsx` | Excel | - | Activo |
| API | `data/raw/API/YYYY.xlsx` | Excel | Anual | Activo |
| Kawak | `data/raw/Kawak/YYYY.xlsx` | Excel | Anual | Activo |
| Fuentes Consolidadas | `data/raw/Fuentes Consolidadas/` | Excel | - | Activo |
| Plan de Acción | `data/raw/Plan de accion/PA_*.xlsx` | Excel | - | Activo |
| Auditoría | `data/raw/Auditoria/*.pdf` | PDF | Anual | Activo |

---

## 2. Detalle de plantillas

**Nota oficial:** para consumo en la app y Gestión OM, la hoja principal es **Consolidado Historico**.

### 2.1 acciones_mejora.xlsx

- **Hoja:** Acciones
- **Columnas (32):** ID, FECHA_IDENTIFICACION, DESCRIPCION, AVANCE, ESTADO, [y 27 más]
- **Descripción:** Registro de acciones de mejora identificadas en auditorías.
- **Usos:** Seguimiento de OM, gestión de acciones correctivas.

### 2.2 Dataset_Unificado.xlsx

- **Hojas:**
  - Unificado (30 columnas): Id, Indicador, Proceso, Periodicidad, Sentido...
  - Unificado (2) (30 columnas): Similar a Unificado
  - Semestral_Original (20 columnas): Id, Indicador, Proceso, Periodicidad, Sentido...
  - Base_Indicadores (13 columnas): Id, Indicador, Clasificación, Subproceso, Periodicidad...
  - Cierres_Original (20 columnas): Id, Indicador, Clasificación, Proceso, Periodicidad...
- **Descripción:** Consolidados históricos de indicadores con diferentes periodicidades.
- **Usos:** Análisis de tendencias, reporte ejecutivo.

### 2.3 Ficha_Tecnica.xlsx

- **Hoja:** Hoja1
- **Columnas (63):** Id Ind, ID Kawak, Nombre del indicador, Unidad, Proceso/Subproceso...
- **Descripción:** Fichas técnicas de cada indicador con metadatos completos.
- **Usos:** Definición y documentación de indicadores.

### 2.4 Indicadores por CMI.xlsx

- **Hojas:**
  - Worksheet (21 columnas): Id, Indicador, Clasificación, Subproceso, Periodicidad...
  - Hoja2 (3 columnas): LÍNEA ESTRATÉGICA, OBJETIVO, META GENERAL
- **Descripción:** Indicadores organizados por Cuadro de Mando Integral (CMI).
- **Usos:** Seguimiento estratégico, alineación con objetivos.

### 2.5 lmi_reporte.xlsx

- **Hojas:**
  - Worksheet (25 columnas): Id, Indicador, Clasificación, Proceso, Tipo...
  - Worksheet (2) (27 columnas): Similar con columnas adicionales
- **Descripción:** Reportes del Sistema de Gestión LMI.
- **Usos:** Reportes operativos.

### 2.6 OM.xlsx

- **Hoja:** Worksheet
- **Columnas (3):** Unnamed: 0, Unnamed: 1, Reporte de acciones de mejora
- **Descripción:** Reporte general de acciones de mejora.
- **Usos:** Vista general de OM.

### 2.7 Resultados_Consolidados_Fuente.xlsx

- **Hojas:**
  - Consolidado Historico (18 columnas): Id, Indicador, Proceso, Periodicidad, Sentido...
  - Consolidado Semestral (18 columnas): Similar
  - Consolidado Cierres (18 columnas): Similar
  - Catalogo Indicadores (14 columnas): Id, Indicador, Clasificacion, Proceso, Periodicidad...
  - Logica (11 columnas): Serie Unica...
  - Variables (8 columnas): Id, Indicador, Proceso, Periodicidad, Sentido...
  - Desglose Series (171 columnas): Series detalladas por indicador
- **Descripción:** Consolidados de resultados con catálogos y lógica de indicadores.
- **Usos:** Análisis detallado, auditoría, seguimiento.

### 2.8 salidas_no_conformes.xlsx

- **Hoja:** SNC
- **Columnas (4):** codigo, id_salida, estado, activo
- **Descripción:** Registro de salidas no conformes.
- **Usos:** Control de calidad, gestión de no conformidades.

### 2.9 Subproceso-Proceso-Area.xlsx

- **Hojas:**
  - Hoja1 (7 columnas): Área, Proceso, Subproceso, Vicerrectoría, Revisión
  - Hoja1 (2) (8 columnas): Área, Subproceso, Proceso, Vicerrectoría, Revisión
  - Hoja2 (4 columnas): Área, Subproceso, ll, Sesiones
  - Rectoria (6 columnas): Área, Subproceso, Proceso, Vicerrectoría, Revisión
  - Hoja3 (2 columnas): Unnamed: 0, Unnamed: 1
  - Facultades (5 columnas): Unidad, Facultad, Escuela, URLS, Enlace Github
  - Facultad (5 columnas): Unidad, Facultad, URLS, Enlace Github, Facultad-Slogan
- **Descripción:** Mapa de procesos, subprocesos, áreas y estructura organizacional.
- **Usos:** Gobernanza, mapeo de responsabilidades.

### 2.10 API/YYYY.xlsx

- **Hoja:** Indicadores
- **Columnas (25):** ID, nombre, clasificacion, sentido, proceso...
- **Descripción:** Indicadores anuales de la fuente API.
- **Periodicidad:** Anual (2022-2026)
- **Usos:** Análisis de tendencias, comparativos anuales.

### 2.11 Kawak/YYYY.xlsx

- **Hoja:** Hoja1 / Worksheet
- **Columnas:** Variable según año (19-27 columnas)
- **Descripción:** Indicadores anuales de la fuente Kawak.
- **Periodicidad:** Anual (2022-2026)
- **Usos:** Análisis de tendencias, comparativos anuales.

### 2.12 Fuentes Consolidadas/Consolidado_API_Kawak.xlsx

- **Hoja:** Sheet1
- **Columnas (26):** ID, nombre, clasificacion, sentido, proceso...
- **Descripción:** Consolidado combinado de fuentes API y Kawak.
- **Usos:** Vista unificada de indicadores.

### 2.13 Fuentes Consolidadas/Indicadores Kawak.xlsx

- **Hoja:** Sheet1
- **Columnas (9):** Año, Id, Indicador, Clasificacion, Proceso...
- **Descripción:** Catálogo de indicadores Kawak por año.
- **Usos:** Referencia de indicadores disponibles.

### 2.14 Plan de accion/PA_*.xlsx

- **Hoja:** Worksheet
- **Columnas (31):** Id Acción, Fecha creación, Clasificación, Avance (%), Estado (Plan de Acción)...
- **Descripción:** Planes de acción derivados de auditorías.
- **Usos:** Seguimiento de acciones, gestión de mejoras.

### 2.15 Auditoria/*.pdf

- **Archivos:**
  - Informe Auditoria Externa Icontec 2025.pdf
  - INFORME AUDITORIA INTERNA FINAL 9001-14001-45001-21001.pdf
- **Descripción:** Informes de auditoría externa e interna.
- **Usos:** Hallazgos de auditoría, acciones correctivas.

---

## 3. Reglas de negocio y validaciones por plantilla

| Plantilla | Validaciones críticas |
|-----------|----------------------|
| acciones_mejora.xlsx | ID único, FECHA_IDENTIFICACION no nula, AVANCE entre 0-100%, ESTADO válido |
| Dataset_Unificado.xlsx | ID único por hoja, Indicador no nulo, Periodicidad válida |
| Ficha_Tecnica.xlsx | ID único, ID Kawak referencial, Nombre indicador no nulo |
| Indicadores por CMI.xlsx | ID único, Clasificación no nula, Línea estratégica no nula |
| Kawak/YYYY.xlsx | ID único, Año coherente, Clasificación no nula |
| API/YYYY.xlsx | ID único, Año coherente, Clasificación no nula |
| Plan de accion/PA_*.xlsx | Id Acción único, Avance 0-100%, Estado válido |
| salidas_no_conformes.xlsx | id_salida único, estado no nulo |

---

## 4. Semaforización estándar

| Nivel | Rango de cumplimiento | Color |
|-------|----------------------|-------|
| Crítico | < 70% o > 120% | 🔴 Rojo |
| Atención | 70% - 80% o 105% - 120% | 🟡 Amarillo |
| Normal | 80% - 105% | 🟢 Verde |

---

## 5. Versiones y cambios

| Fecha | Plantilla | Cambio |
|-------|-----------|--------|
| 2026-04-06 | Versión inicial | Catalogación inicial de todas las plantillas |

---

## 6. Próximos pasos

1. Validar estructura de cada plantilla con usuarios clave.
2. Documentar reglas de negocio específicas por indicador.
3. Implementar módulo de ingesta para cada plantilla.
4. Configurar validaciones y logs de calidad.
5. Versionar y mantener este catálogo actualizado.
