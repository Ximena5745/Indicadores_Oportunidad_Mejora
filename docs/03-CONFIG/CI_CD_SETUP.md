# 🔄 CI/CD Setup Documentación

**Fecha:** 11 de abril de 2026  
**Status:** ✅ GitHub Actions configurado

---

## 📋 Workflows Implementados

### 1. **Tests Workflow** (`.github/workflows/test.yml`)

Ejecuta automáticamente en:
- `push` a `main` o `develop`
- `pull_request` contra `main` o `develop`

**Qué hace:**
- ✅ Ejecuta pytest con cobertura (Python 3.10 y 3.11)
- ✅ Genera reporte de cobertura (XML, HTML, terminal)
- ✅ Sube a Codecov (opcional)
- ✅ Comenta en PRs con resumen de cobertura

**Test Thresholds:**
- 🟢 Verde: coverage ≥ 80%
- 🟡 Naranja: coverage 60-79%
- 🔴 Rojo: coverage < 60%

### 2. **Lint Workflow** (`.github/workflows/lint.yml`)

Ejecuta automáticamente en:
- `push` a `main` o `develop`
- `pull_request` contra `main` o `develop`

**Qué hace:**
- ✅ Lint con **ruff** (fast Python linter)
- ✅ Format check con **ruff format**
- ✅ Type checking con **mypy**
- ✅ Security scan con **bandit**
- ✅ Compilation check (syntax validation)

**Nota:** Todos tienen `continue-on-error: true` (warnings, no bloquean PRs en MVP)

### 3. **Staging Deploy Workflow** (`.github/workflows/deploy-staging.yml`)

Ejecuta automáticamente en:
- `push` a `develop` branch
- Manual trigger (workflow_dispatch)

**Qué hace:**
- ✅ Notifica Render.com para deploy (si está configurado)
- ✅ Espera 30 segundos para propagación
- ✅ Ejecuta health check en staging URL
- ✅ Reporta status

**Requisitos:**
Configure en GitHub (Settings → Secrets):
- `RENDER_DEPLOY_HOOK_URL`: URL del deploy hook de Render.com
- `STAGING_URL`: URL del ambiente staging (e.g., https://sgind-staging.render.com)

---

## 🔧 Pre-commit Hooks Setup

### Instalación Local

```bash
# 1. Instalar pre-commit
pip install pre-commit

# 2. Instalar hooks (corre una sola vez)
pre-commit install

# 3. Correr manualmente en todos los archivos (opcional)
pre-commit run --all-files
```

### Qué hace cada hook

| Hook | Acción |
|------|--------|
| `trailing-whitespace` | Elimina espacios en blanco al final de líneas |
| `end-of-file-fixer` | Asegura newline al final de archivos |
| `check-yaml` | Valida YAML syntax |
| `check-large-files` | Bloquea archivos >1MB |
| `check-json` | Valida JSON syntax |
| `debug-statements` | Detecta `breakpoint()` y `pdb` |
| `ruff` | Linting + auto-fix |
| `ruff-format` | Auto-formateo de código |
| `mypy` | Type checking (solo core/ y services/) |
| `bandit` | Security scanning |

### Comportamiento en Git

Cuando haces `git commit`:

```
1. Pre-commit hooks corren automáticamente
2. Si detectan issues:
   - Auto-fix lo que puede (ruff, formatting)
   - Reporta lo que no puede arreglar
3. Si hay cambios, necesitas `git add` de nuevo y retry commit
4. Si todo OK → commit procede
```

**Ejemplo:**
```bash
$ git commit -m "Add feature"
# → ruff finds trailing whitespace
# → ruff removes it automatically
# → You need to git add and commit again
```

### Skip hooks (no recomendado)

```bash
git commit --no-verify  # Salta PRE-COMMIT checks (solo emergencias)
```

---

## 📊 Coverage & Quality Gates

### Coverage Requirements

| Branch | Min Coverage | Auto-fail? |
|--------|--------------|-----------|
| `main` | 85% | ❌ No (warning only) |
| `develop` | 80% | ❌ No (warning only) |
| PR merge | 80% | ❌ No (warning only in MVP) |

**En Fase 2+:** Activar bloqueo (require branch protection rules)

### GitHub Branch Protection Rules (Recomendado)

En **Settings → Branches → main**:

```
✅ Require a pull request before merging
✅ Dismiss stale pull request approvals
✅ Require status checks to pass:
   - Tests / test (ubuntu-latest)
   - Lint Filter & Format Check / lint
✅ Require branches to be up to date
✅ Include administrators
✅ Require code reviews: 1
```

---

## 🚀 Local Development Workflow

### Primero, instalar deps

```bash
# Instalar main + dev dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Instalar pre-commit hooks
pre-commit install
```

### Workflow diario

```bash
# 1. Create feature branch
git checkout -b feature/my-feature

# 2. Make changes
# (pre-commit hooks run on each commit)

# 3. Run tests locally (antes de push)
pytest tests/ --cov=core --cov-report=term

# 4. Push
git push origin feature/my-feature

# 5. GitHub Actions runs automatically:
#    - test.yml (tests + coverage)
#    - lint.yml (linting + types)

# 6. Create PR on GitHub
# 7. Merge after review + checks pass
```

### Commands útiles

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_calculos.py

# Run with coverage
pytest tests/ --cov=core --cov-report=html

# Run linting locally
ruff check core/ services/

# Auto-fix linting issues
ruff check core/ services/ --fix

# Format code
ruff format core/ services/

# Type check
mypy core/ services/

# Security check
bandit -r core/ services/

# Run pre-commit on all files
pre-commit run --all-files
```

---

## 📈 Monitoring & Debugging

### GitHub Actions Dashboard

Go to: **Settings → Actions**

View:
- ✅ Successful workflows
- ❌ Failed workflows (check logs)
- ⏱️ Execution time
- 🔄 Latest runs

### Debugging a failed workflow

1. Click on failed workflow run
2. Expand job logs
3. Look for error message
4. Common issues:
   - Missing imports → Fix code
   - Test failures → Debug locally
   - Timeout → Optimize test or increase timeout
   - Environment variable missing → Add to GitHub Secrets

### Troubleshooting

| Issue | Solution |
|-------|----------|
| **Test timeout** | Increase `timeout-minutes` in workflow |
| **Cache miss** | Delete cache, re-run job |
| **Dependency error** | Update `requirements.txt` + commit |
| **Coverage not uploading** | Check Codecov token in secrets |
| **Pre-commit fails** | Run `pre-commit run --all-files` locally |

---

## 🔐 Secrets Management

### Required Secrets (in GitHub Settings → Secrets)

```yaml
RENDER_DEPLOY_HOOK_URL: <your-render-hook>
STAGING_URL: https://sgind-staging.render.com
CODECOV_TOKEN: <optional, for auto-upload>
```

### How to add

1. Go to repo Settings
2. → Secrets and variables → Actions
3. → New repository secret
4. Name + Value
5. Click "Add secret"

---

## 📝 Next Steps (Fase 2)

### Inmediato

- [ ] Configure GitHub branch protection rules
- [ ] Add Codecov integration (optional free tier)
- [ ] Configure Render deploy hook (for deploy-staging)
- [ ] Run `pre-commit install` locally on machine

### Phase 2 Enhancements

- [ ] Add E2E tests (Selenium / Playwright)
- [ ] Add performance benchmarks
- [ ] Add deployment to production (GitHub environments)
- [ ] Add Slack notifications on deploy
- [ ] Add SLA dashboard

---

## 📚 References

- **GitHub Actions Docs:** https://docs.github.com/actions
- **Pre-commit Docs:** https://pre-commit.com
- **Ruff Docs:** https://docs.astral.sh/ruff
- **Pytest Docs:** https://docs.pytest.org
- **Codecov:** https://about.codecov.io

---

**Documento Generado:** 11 de abril de 2026  
**Version:** 1.0  
**Status:** ✅ Ready to use

Para setup completo, ver sección "Local Development Workflow" arriba.
