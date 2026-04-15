# 📋 DECISIÓN: NO a Redis Cloud

**Fecha:** 11 de abril de 2026  
**Decisor:** Usuario Final  
**Status:** ✅ DECIDIDA Y DOCUMENTADA

---

## 🎯 Decisión

```
CACHE STRATEGY: ❌ NO REDIS CLOUD
├─ Razón: No hay presupuesto de inversión
├─ Alternativa: Mantener local cache (@st.cache_data)
├─ Timeline: Mantener hasta que load real lo requiera
└─ Re-eval: SÍ si usuarios + performance lo necesitan
```

---

## 📊 Impactos

### Positivos ✅
- **Cost:** $0/month (sin cambio)
- **Simplicity:** Mantienen infraestructura actual
- **No new tools:** Nada que mantener/debuggear

### Limitaciones ⚠️
- **Scaling:** Max ~10-15 concurrent users
- **No compartido:** Cada usuario carga datos independientemente
- **No persistente:** Cache se pierde si app reinicia

---

## 🚀 Plan de Acción

### Fase 2 (Semana 3-4): Optimización Local

En lugar de Redis, optimizamos cache local:

1. **Lazy Loading Improvements**
   - Implement selective column loading (Excel)
   - Paginate large datasets
   - Async data loading donde possible

2. **Cache TTL Strategy**
   - Optimize `@st.cache_data(ttl=300)` values
   - Implement cache warming on startup
   - Smart invalidation triggers

3. **Monitoring**
   - Add cache hit/miss metrics
   - Track Streamlit memory usage
   - Performance dashboards

### Producción: Monitor Real Load

Una vez en producción con usuarios reales:
- Track concurrent user count
- Monitor ETL duration + timeouts
- Record cache effectiveness

**Si load requiere:** Re-evaluar Redis en futuro (Fase 3+)

---

## 📝 Alternativas Descartadas

| Alternativa | Por qué NO |
|-------------|-----------|
| **Redis Cloud** | Sin presupuesto |
| **Local Redis** | Requiere setup + mantenimiento |
| **CDN** | Overkill para datos internos |
| **Database Cache (PG)** | Más lento que Redis |

---

## 🔄 Road to Scale (Si necesario)

Cuando load real > 15 concurrent users:

```
OPCIÓN A (Recomendada): Redis Cloud
  - Cost: ~$20-50/month
  - Effort: 16h integration
  - Payback: Mejor performance para N users

OPCIÓN B: Render.com Scale Up
  - Cost: $100+/month (dyno upgrade)
  - Effort: 2h config
  - Payback: Mejor hardware, no cache compartida

OPCIÓN C: Hybrid (Local + CDN)
  - Cost: $0-50/month
  - Effort: 20h implementation
  - Payback: Middle ground
```

**Recommendation:** Si llega a 10+ users, usar OPCIÓN A (Redis, costo-beneficio mejor).

---

## ✅ Documentación Actualizada

- FASE_2_PLAN.md: Updated roadmap + budget (232h, $0 infra)
- REDIS_CACHING_PLAN.md: Decision gate marked as ❌ NO
- services/caching_strategy.py: Ready if future decision changes to YES

---

## 📌 Recordatorio Futuro

**SÍ llegamos a Fase 3 y tenemos usuarios reales:**
1. Check `REDIS_CACHING_PLAN.md` § "POC: Implementación Mínima"
2. Estimate cost ($20-50/month) vs. performance gain
3. Budget decision
4. Implement services/caching_strategy.py integration

---

**Decisión tomada como irreversible para Fase 2.**  
**Re-evaluar en Fase 3+ basado en user load real.**

---

**Firmado:** Chat Agent  
**Autoridad:** Resultado de decisión usuario  
**Efectiva:** 11 de abril de 2026
