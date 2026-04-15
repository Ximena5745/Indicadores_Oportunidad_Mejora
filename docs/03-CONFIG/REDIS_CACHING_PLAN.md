# 🔴 REDIS CACHING PLAN — Architecture & Decision Guide

**Fecha:** 11 de abril de 2026  
**Status:** 📋 Análisis + Recomendación  
**Decision Required:** SemanaWeek 1 (antes de Fase 2 dev)

---

## 🎯 Problema

Actualmente, SGIND usa **caché local en Streamlit** (`@st.cache_data`, `@st.cache_resource`):

```python
@st.cache_data(ttl=300)
def cargar_dataset():
    return pd.read_excel(...)  # Cached por 5 minutos
```

**Limitaciones:**

| Limitación | Impacto | Criticidad |
|-----------|--------|-----------|
| **No compartida entre users** | Cada usuario carga datos independientemente | 🔴 Alto |
| **No persistente** | Pierden caché si app reinicia | 🟡 Medio |
| **No escalable** | Con 10+ usuarios concurrentes, → N lecturas de Excel | 🔴 Alto |
| **Memory per instance** | En Render.com con múltiples dynos, N×RAM | 🟡 Medio |

**Escenario actual (Render.com Single Dyno):**
- 1 usuario → 1 caché local ✅
- 3 usuarios concurrentes → 3 cargas paralelas (no compartidas) ⚠️
- 10+ usuarios durante peak hours → Slowdown 🔴

---

## 💡 Solución: Redis

**Redis** es un almacenamiento clave-valor en memoria con:
- ✅ Compartible entre instancias (servidores Render)
- ✅ Persistencia opcional
- ✅ TTL automático (expiración)
- ✅ Muy rápido (<1ms latencia)

---

## 📊 Análisis Comparativo

### Opción A: Local Cache Only (Status Quo)

```
┌─────────────────┐
│ Render Dyno #1  │
│  Streamlit App  │
│  - Local Cache  │  ← Caché SOLO en este dyno
│  └─ DataFrame   │
└─────────────────┘

User 1 → Lee Excel 1 × (first time)
User 2 → Lee Excel 1 × (doesn't share cache)
User 3 → Lee Excel 1 × (doesn't share cache)
```

**Ventajas:**
- ✅ Zero setup
- ✅ Grati (sin costo)
- ✅ Simple debugging

**Desventajas:**
- ❌ No escalable (N users = N reads)
- ❌ No persistente
- ❌ Memory leak risk en apps largas

**Cost:** $0/month  
**Scaling:** Max ~5 concurrent users (before timeout)  
**Best For:** Dev local / single user

---

### Opción B: Redis Cloud (Recommended)

```
┌───────────────────────────────────────────────┐
│              Render.com (Multiple Dynos)       │
├─────────────────┬──────────────────────────────┤
│ Dyno #1         │ Dyno #2                      │
│ Streamlit App   │ Streamlit App                │
└──┬──────────────┴──────────────┬───────────────┘
   │                             │
   └─────────────────┬───────────┘
                     ↓
         ┌──────────────────────────┐
         │   Redis Cloud            │
         │  (Shared Cache)          │
         │  ┌────────────────────┐  │
         │  │ key: dataset_hash  │  │
         │  │ value: DataFrame   │  │
         │  │ TTL: 300s          │  │
         │  └────────────────────┘  │
         └──────────────────────────┘

User 1 → Redis HIT (fast)
User 2 → Redis HIT (fast)
User 3 → Redis HIT (fast)
```

**Ventajas:**
- ✅ Caché compartida (1 read → many hits)
- ✅ Escalable a 100+ concurrent users
- ✅ Persistencia opcional
- ✅ Soporta complex types (JSON, DataFrames via pickle)

**Desventajas:**
- 🔴 Costo extra ($10-50/month dependiendo tamaño)
- 🔴 Latencia red (1-5ms vs 0.1ms local)
- 🔴 Complejidad debugging

**Cost:** $10-50/month (Redis Cloud free tier es muy limitado)  
**Scaling:** 100+ concurrent users easily  
**Best For:** Production + multi-dyno scaling

---

### Opción C: Hybrid (Local + Redis Fallback)

```python
def get_cached_data(key, loader_func):
    try:
        # Try Redis first (fast, shared)
        return redis_client.get(key)
    except RedisError:
        # Fall back to local cache
        return local_cache.get_or_load(key, loader_func)
```

**Ventajas:**
- ✅ Best of both worlds
- ✅ Handles Redis downtime gracefully
- ✅ Staged rollout (test locally, deploy to prod)

**Desventajas:**
- 🔴 Komplejo code path
- 🔴 Debugging errors tricky

---

## 🏆 RECOMENDACIÓN

### Para Fase 2: **Opción B (Redis Cloud)**

**Razón:**

1. **Fase 1 análisis** mostró que carga de Excel es cuello de botella principal
2. **Render.com scale** — múltiples dynos → necesita cache compartido
3. **Costo-beneficio** — $20/month << 1 FTE de optimization (~$3,000)
4. **OKRs Fase 2** — Target ETL <5min, necesita caché compartido

**Timeline:**

- **Semana 1:** Decision (esta semana)
- **Semana 3:** Implementar Redis client
- **Semana 4:** Test en staging
- **Semana 5:** Production rollout

---

## 📋 POC: Implementación Mínima

### Paso 1: Provisionar Redis Cloud

```bash
# Redis Cloud (https://redis.com/try-free/)
# Sign up → Create free database (25 MB, good for POC)
# Get connection string: redis://default:PASSWORD@HOST:PORT
```

### Paso 2: Instalar cliente Python

```bash
pip install redis
```

### Paso 3: Código POC

```python
# services/caching_strategy.py

import redis
import pickle
import os
from typing import Optional, Callable, Any

class CacheStrategy:
    def __init__(self, use_redis: bool = True):
        self.use_redis = use_redis
        self.redis_client = None
        
        if use_redis:
            try:
                redis_url = os.getenv("REDIS_URL")
                if redis_url:
                    self.redis_client = redis.from_url(redis_url)
                    self.redis_client.ping()  # Test connection
                    print("✅ Redis connected")
            except Exception as e:
                print(f"⚠️  Redis unavailable: {e}, falling back to local")
                self.use_redis = False
    
    def get(self, key: str) -> Optional[Any]:
        """Get from cache."""
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                return pickle.loads(data) if data else None
            except Exception as e:
                print(f"Redis get error: {e}")
                return None
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """Set in cache."""
        if self.redis_client:
            try:
                data = pickle.dumps(value)
                self.redis_client.setex(key, ttl_seconds, data)
                return True
            except Exception as e:
                print(f"Redis set error: {e}")
                return False
        return False

# Usage
cache = CacheStrategy(use_redis=True)

# Try to get
df = cache.get("dataset_key")

# If not cached, load and cache
if df is None:
    df = pd.read_excel("data.xlsx")
    cache.set("dataset_key", df, ttl_seconds=300)
```

### Paso 4: Integrar en data_loader.py

```python
from services.caching_strategy import CacheStrategy

cache = CacheStrategy(use_redis=True) 

@st.cache_resource
def _get_cache():
    return CacheStrategy(use_redis=True)

def cargar_dataset() -> pd.DataFrame:
    cache = _get_cache()
    
    # Try Redis first
    df = cache.get("dataset_official")
    if df is not None:
        print("✅ Cache HIT")
        return df
    
    # Load and cache
    print("�x Cache MISS → Loading...")
    path = DATA_OUTPUT / "Resultados Consolidados.xlsx"
    df = pd.read_excel(path, sheet_name="Consolidado Semestral")
    
    # Cache for 5 minutes
    cache.set("dataset_official", df, ttl_seconds=300)
    
    return df
```

---

## 💻 Arquitectura Completa (Fase 2)

```
┌────────────────────────────────────────────────────────────┐
│                  SGIND Fase 2 Caching                       │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Request kommer in (User loads app)                        │
│      ↓                                                      │
│  ┌──────────────────────────────────────────────┐          │
│  │ cargar_dataset()                             │          │
│  │  1. Check Streamlit @st.cache_resource (0ms)│          │
│  │  2. Check Redis (1-2ms)                      │          │
│  │  3. Load Excel (3-4s if needed)              │          │
│  │  4. Cache result in both                     │          │
│  └──────────────────────────────────────────────┘          │
│      ↓                                                      │
│  ┌──────────────────────────────────────────────┐          │
│  │ Application Logic                            │          │
│  │  - Enrich with CMI                           │          │
│  │  - Calculate cumplimiento                    │          │
│  │  - Render visualizations                     │          │
│  └──────────────────────────────────────────────┘          │
│      ↓                                                      │
│  Response sent (fast!)                                     │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

**Performance Gains:**

| Scenario | Time | Notes |
|----------|------|-------|
| First user load | 5s | Excel read (no cache) |
| Subsequent users (Redis hit) | 1s | Deserialize + render |
| 10 concurrent users (all cache hits) | 1s each | No Excel bottleneck |

---

## 🔄 Decisión Tomada

**DECISIÓN FINAL:**

```
┌─────────────────────────────────────────────┐
│ ❌ NO A REDIS CLOUD                         │
│                                             │
│ Razón: No hay presupuesto de inversión     │
│        (11 de abril de 2026)                │
│                                             │
│ → Mantener local cache (status quo)        │
│ → Optimizar otras estrategias              │
│ → Re-evaluar si load real lo requiere     │
│                                             │
└─────────────────────────────────────────────┘
```

**Implicaciones:**
- ✅ Cost: $0/month (sin cambio)
- ⚠️ Scaling: Max ~10-15 concurrent users
- 🟢 Simple: No new infrastructure
- 📊 Monitor: Track performance en producción

---

## 📊 Cost-Benefit Analysis

### If YES (Redis Cloud):

| Aspecto | Valor |
|--------|-------|
| **Cost** | $20/month (development) + $50+/month (prod) |
| **Performance Gain** | 3-5x speedup with 10+ users |
| **Scalability** | 100+ concurrent users supported |
| **Development Time** | 16-20h (Fase 2 Week 3-4) |
| **ROI** | Break-even at 3+ concurrent users |

### If NO (Local Cache Only):

| Aspecto | Valor |
|--------|-------|
| **Cost** | $0/month |
| **Performance** | Good for <5 concurrent users, degrades after |
| **Scalability** | Max ~10 users before timeout |
| **Workaround for Scale** | Increase Render dyno size (more expensive) |
| **Future Technical Debt** | Will need Redis later anyway |

**Recomendación:** SÍ, costo es bajo vs. beneficio futuro.

---

## 🔄 Roadmap Caching (Fase 2-3)

### Semana 1 (Esta): Decision
- [ ] Revisar analysis
- [ ] Presupuesto aprobado o NO
- [ ] Comunicar decisión al team

### Semana 3-4: Implementación (if YES)
- [ ] Setup Redis Cloud account
- [ ] Implement CacheStrategy wrapper
- [ ] Integrate en data_loader.py
- [ ] Tests + staging validation

### Semana 5: Production
- [ ] Set REDIS_URL en Render.com secrets
- [ ] Monitor performance metrics
- [ ] Document for operations

### Future (Fase 3):
- [ ] Evaluar otras strategies (CDN, edge caching)
- [ ] Implement cache invalidation events
- [ ] Dashboard para cache hit rates

---

## 📚 References

- **Redis Documentation:** https://redis.io/docs/
- **Redis Cloud Free Tier:** https://redis.com/try-free/
- **Python redis-py:** https://github.com/redis/redis-py
- **Render.com Environment Variables:** https://render.com/docs/environment-variables

---

**Documento Generado:** 11 de abril de 2026  
**Version:** 1.0 — Decision Gate  
**Próximo Paso:** Presentar a stakeholders, obtener aprobación en Semana 1
