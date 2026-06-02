# 🏗️ CI/CD Architecture - Diagramas y Flujos

## 1. Flujo General de Cambios

```
┌─────────────────────────────────────────────────────────────────┐
│                     DESARROLLADOR                               │
│                                                                 │
│  git add, commit, push                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
         ┌───────────────────────────────────┐
         │   GitHub Detecta Push/PR          │
         │   (Path Filtering)                │
         └────┬───────────────────┬──────────┘
              │                   │
    ┌─────────▼────┐    ┌────────▼──────────┐
    │ ¿Cambio en   │    │ ¿Cambio en       │
    │ converters/? │    │ dashboards/?     │
    └─────────┬────┘    └────────┬──────────┘
              │                  │
          SÍ  │              SÍ  │
              │                  │
    ┌─────────▼────────┐   ┌─────▼──────────────┐
    │ ✅ converters-ci │   │ ✅ dashboards-ci   │
    │ (3-5 min)        │   │ (2-3 min)          │
    └─────────┬────────┘   └─────┬──────────────┘
              │                  │
              │                  │
              └────────┬─────────┘
                       │
                       ▼
         ┌─────────────────────────┐
         │ ✅ integration.yml      │
         │ (5-10 min)              │
         │ SIEMPRE CORRE           │
         └────────┬────────────────┘
                  │
        ┌─────────▼──────────┐
        │ ¿Status OK?        │
        └────┬────────┬──────┘
             │        │
          ✅ │        │ ❌
             │        │
        ┌────▼─┐   ┌──▼─────┐
        │ MERGE│   │ REVIEW │
        │ OK   │   │ CHANGES│
        └──────┘   └────────┘
```

---

## 2. Arquitectura de Workflows

```
┌────────────────────────────────────────────────────────────────────┐
│                    GITHUB ACTIONS                                  │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ 🔵 converters-ci.yml (Path: converters/**)                  │ │
│  │ Trigger: Push/PR                                            │ │
│  │ ┌────────────────────────────────────────────────────────┐  │ │
│  │ │ job: test (matrix Python 3.8-3.11)                    │  │ │
│  │ │   └─ pytest (coverage >80%)                           │  │ │
│  │ │   └─ codecov upload                                   │  │ │
│  │ ├─ job: lint                                             │  │ │
│  │ │   └─ flake8, black, isort, pylint, bandit            │  │ │
│  │ └─ job: performance (solo en main)                       │  │ │
│  │     └─ pytest -m slow                                    │  │ │
│  └────────────────────────────────────────────────────────────┘  │ │
│                                                                    │ │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ 🟢 dashboards-ci.yml (Path: dashboards/**, data/**)       │ │
│  │ Trigger: Push/PR                                            │ │
│  │ ┌────────────────────────────────────────────────────────┐  │ │
│  │ │ job: validate                                          │  │ │
│  │ │   └─ htmlhint                                          │  │ │
│  │ │   └─ file structure checks                            │  │ │
│  │ ├─ job: data-validation                                  │  │ │
│  │ │   └─ validate_json_schema.py                          │  │ │
│  │ └─ job: build-check                                      │  │ │
│  │     └─ verify no build needed                           │  │ │
│  └────────────────────────────────────────────────────────────┘  │ │
│                                                                    │ │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ 🟡 integration.yml (No path filter - SIEMPRE)              │ │
│  │ Trigger: Push/PR (siempre)                                  │ │
│  │ ┌────────────────────────────────────────────────────────┐  │ │
│  │ │ job: e2e-pipeline                                      │  │ │
│  │ │   ├─ Prepare test CSV                                 │  │ │
│  │ │   ├─ Run converters                                   │  │ │
│  │ │   ├─ Validate JSON output                             │  │ │
│  │ │   ├─ Generate index.json                              │  │ │
│  │ │   └─ Validate schema                                  │  │ │
│  │ └─ job: cross-component-validation                       │  │ │
│  │     └─ Verify dashboards can load data                  │  │ │
│  └────────────────────────────────────────────────────────────┘  │ │
│                                                                    │ │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ 🟣 deploy.yml (Manual - workflow_dispatch)               │ │
│  │ Trigger: Manual en GitHub Actions                         │ │
│  │ Inputs:                                                   │ │
│  │   - environment: staging | production                     │ │
│  │   - component: converters | dashboards | both            │ │
│  │ ┌────────────────────────────────────────────────────────┐  │ │
│  │ │ job: build                                             │  │ │
│  │ │   └─ Crear artefacto según component                  │  │ │
│  │ ├─ job: deploy-staging (condicional)                     │  │ │
│  │ │   ├─ SSH to staging                                    │  │ │
│  │ │   ├─ Extract + install                                │  │ │
│  │ │   └─ Health check                                      │  │ │
│  │ ├─ job: request-production-approval                      │  │ │
│  │ │   └─ Comment en PR pidiendo aprobación                │  │ │
│  │ └─ job: deploy-production (condicional)                  │  │ │
│  │     ├─ Backup                                            │  │ │
│  │     ├─ SSH to production                                 │  │ │
│  │     ├─ Extract + install                                │  │ │
│  │     ├─ Health check                                      │  │ │
│  │     └─ Create GitHub release                            │  │ │
│  └────────────────────────────────────────────────────────────┘  │ │
│                                                                    │ │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3. Path Filtering Logic

```
                        PUSH/PR detectado
                              │
                    Examinar archivos cambiados
                              │
                ┌─────────────┼─────────────┐
                │             │             │
          ¿Tiene en       ¿Tiene en    ¿Tiene en
         converters/?    dashboards/?  .github/?
          (cualquier)     (cualquier)   (workflows)
           archivo        archivo
                │             │             │
           YES │         YES │         YES │
                ▼             ▼             ▼
         ┌────────────┐ ┌────────────┐ ┌──────────────────┐
         │Run         │ │Run         │ │Determinar qué   │
         │converters- │ │dashboards- │ │ejecutar:         │
         │ci.yml      │ │ci.yml      │ │- Si .yml cambió  │
         │            │ │            │ │  ejecutar ese   │
         │+ integration│ │+ integration│ │- Si yml == crc  │
         │            │ │            │ │  no re-ejecutar │
         └────────────┘ └────────────┘ └──────────────────┘
```

---

## 4. Dependencias Entre Workflows

```
┌─────────────────────────────────────────────────┐
│  converters-ci.yml          dashboards-ci.yml   │
│  ├─ test (parallel matrix)  ├─ validate         │
│  ├─ lint                    ├─ data-validation  │
│  └─ performance             └─ build-check      │
│      │                           │               │
│      └───────┬───────────────────┘               │
│              │                                   │
│              ▼                                   │
│  ┌──────────────────────────────────────────┐   │
│  │  integration.yml (SIEMPRE)               │   │
│  │  Requiere:                               │   │
│  │  ├─ e2e-pipeline (CSV → JSON)           │   │
│  │  └─ cross-component validation          │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘

✅ converters-ci + dashboards-ci = ✅ integration
❌ Si alguno falla, integration.yml igual corre (robustez)
```

---

## 5. Deployment Flow (deploy.yml)

```
                    ┌─────────────────────┐
                    │ Manual Trigger:     │
                    │ environment = ???   │
                    │ component = ???     │
                    └────────┬────────────┘
                             │
                    ┌────────▼─────────┐
                    │ job: build       │
                    │                  │
                    │ Según component: │
                    │ ├─ converters    │ → release-dashboard-converters-{sha}.tar.gz
                    │ ├─ dashboards    │ → release-dashboard-dashboards-{sha}.tar.gz
                    │ └─ both          │ → release-dashboard-complete-{sha}.tar.gz
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
    ┌─────────▼──────────┐      ┌──────────▼───────┐
    │ environment ==     │      │ environment ==   │
    │ "staging"?         │      │ "production"?    │
    └────────┬──────────┘      └────────┬─────────┘
             │                         │
         YES │                     YES │
             │                         │
    ┌────────▼──────────────┐   ┌──────▼──────────────────┐
    │ job: deploy-staging   │   │ job: deploy-production  │
    │ ├─ SSH upload         │   │ ├─ Backup              │
    │ ├─ Extract            │   │ ├─ SSH upload          │
    │ ├─ Install deps       │   │ ├─ Extract             │
    │ └─ Health check       │   │ ├─ Install deps        │
    └────────┬──────────────┘   │ ├─ Health check        │
             │                  │ └─ Create release      │
             │                  └──────┬───────────────┘
             │                         │
             └────────┬────────────────┘
                      │
        ┌─────────────▼──────────────┐
        │ job: request-approval      │
        │ (comment en PR)            │
        │ Pedir aprobación manual    │
        └────────────────────────────┘
```

---

## 6. Data Flow: CSV → Converters → Dashboards

```
┌──────────────────────────┐
│  data/input/             │
│  ├─ incidencias.csv      │
│  └─ postmortem.csv       │
└────────┬─────────────────┘
         │
         │ converters/cli/
         │ convert_incidents.py
         │ convert_postmortems.py
         │
         ▼
┌──────────────────────────┐
│  data/output/            │
│  ├─ incidencias.json     │
│  ├─ postmortem.json      │
│  └─ index.json ◄────┐    │
└────────┬──────────────┘   │
         │                  │
         │ build_index.py ──┘
         │
         ▼
┌──────────────────────────┐
│ dashboards/              │
│ ├─ index.html ──┐        │
│ ├─ dashboard    │ fetch  │
│ │  -portal.html │        │
│ │   (loads      │        │
│ │   ../data/)   │        │
│ ├─ massive-    │        │
│ │  incidents    │        │
│ │  -dashboard   │        │
│ │  .html ───────┘        │
│ └─ postmortem- │        │
│    dashboard   │        │
│    .html ───────┘        │
└──────────────────────────┘

Integration Test:
  CSV → JSON → index.json → ✅ Dashboards can load
```

---

## 7. Status Checks en PR

```
Pull Request #123
├─ Conversation
├─ Changes
├─ Checks  ◄─────────────────────┐
│                                 │
│  ┌─ Converters CI ──────────┐   │
│  │ ✅ test (coverage OK)    │   │
│  │ 🟡 lint (warnings, no fail) │
│  │ ✅ performance           │   │
│  │ ✅ Overall: SUCCESS      │   │
│  └──────────────────────────┘   │
│                                 │
│  ┌─ Dashboards CI ──────────┐   │
│  │ ✅ validate              │   │
│  │ 🟡 data-validation       │   │
│  │ ✅ build-check           │   │
│  │ ✅ Overall: SUCCESS      │   │
│  └──────────────────────────┘   │
│                                 │
│  ┌─ Integration Tests ──────┐   │
│  │ 🟡 e2e-pipeline          │   │
│  │ 🟡 cross-component       │   │
│  │ ✅ Overall: SUCCESS      │   │
│  └──────────────────────────┘   │
│                                 │
│  ← All checks passed, ready to merge!
```

---

## 8. Decision Tree: ¿Qué Workflow Se Ejecuta?

```
                        PUSH/PR
                          │
              ¿Cambio en converters/?
                    │           │
                   NO          SÍ
                    │           │
         ¿Cambio en │      ┌────┴─────────┐
         dashboards/?      │              │
            │      │    ¿Cambio en       │
           NO     SÍ   dashboards/?     │
            │      │       │        │     │
            │      │      NO       SÍ    │
            │      │       │        │    │
            ▼      ▼       ▼        ▼    ▼
        ┌─────┐ ┌────┐ ┌─────┐ ┌────┐┌────┐
        │Only │ │Both│ │Only │ │Both││Both│
        │Dash │ │Run │ │Conv │ │Run ││Run │
        │      │ │All │ │     │ │All ││All │
        └──┬──┘ └─┬──┘ └──┬──┘ └─┬──┘└─┬──┘
           │      │       │      │     │
           ▼      ▼       ▼      ▼     ▼
       ┌────────────────────────────────────┐
       │  SIEMPRE corre:                    │
       │  ✅ integration.yml (E2E test)     │
       └────────────────────────────────────┘
```

---

## 9. Error Escalation Path

```
❌ TEST FALLA EN CONVERTERS-CI
    │
    ├─ Coverage < 80%
    │   └─ pytest --cov=src → agrega tests
    │
    ├─ Syntax error
    │   └─ black src/ → auto-fix format
    │
    └─ Import issues
        └─ isort src/ → auto-sort imports

❌ DEPLOYMENT FALLA
    │
    ├─ SSH key error
    │   └─ GitHub Settings → Secrets → update SSH_PRIVATE_KEY
    │
    ├─ Path not found
    │   └─ Verificar directorios en servidor (SSH manual)
    │
    └─ Health check failed
        └─ Curl manual a URL staging/production

❌ INTEGRATION FAIL
    │
    └─ CSV not found
        └─ Crear test data en converters/tests/test_data/
```

---

## 10. Timeline: Desde Push Hasta Production

```
t=0    git push
       │
t=1    ├─ GitHub detects push
       │  └─ Inicia workflows
       │
t=2    ├─ converters-ci starts
       │  ├─ test (2-3 min)
       │  ├─ lint (1 min)
       │  └─ performance (1 min)
       │
t=3    ├─ dashboards-ci starts
       │  └─ (2-3 min paralelo)
       │
t=5    ├─ integration starts
       │  └─ (5-10 min)
       │
t=15   ├─ ✅ All workflows pass
       │  └─ PR ready to merge
       │
t=16   ├─ Merge PR to main
       │  └─ Workflows corre again en main
       │
t=30   ├─ ✅ All main workflows pass
       │  └─ Ready for deployment
       │
t=31   ├─ Manual: GitHub Actions → Deploy
       │  ├─ Select environment (staging/production)
       │  ├─ Select component (converters/dashboards/both)
       │  └─ Run workflow
       │
t=35   ├─ Staging deployment completes
       │  ├─ Health check pass
       │  └─ Comment en PR pidiendo aprobación
       │
t=40   ├─ Manual approval en workflow
       │  └─ Approve → Production
       │
t=50   └─ Production deployment completes
          ├─ Backup made
          ├─ New version live
          └─ GitHub release created
```

---

## 11. Componentes Arquitectura

```
┌────────────────────────────────────────────────────┐
│            Release Dashboard Application            │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────────┐        ┌─────────────────┐  │
│  │    Converters    │        │   Dashboards    │  │
│  │  (Python)        │        │  (HTML/CSS/JS)  │  │
│  │                  │        │                 │  │
│  │ ├─ CLI tools     │        │ ├─ index.html   │  │
│  │ ├─ Validators    │        │ ├─ portal       │  │
│  │ ├─ Parsers       │        │ ├─ massive-inc  │  │
│  │ ├─ CSV→JSON      │        │ └─ postmortem   │  │
│  │ └─ KPI calc      │        │                 │  │
│  │                  │        │                 │  │
│  └────────┬─────────┘        └────────┬────────┘  │
│           │                           │            │
│           └─────────────┬─────────────┘            │
│                         │                          │
│                    ┌────▼────┐                     │
│                    │ data/   │                     │
│                    │ input/  │ ← CSVs             │
│                    │ output/ │ ← JSONs            │
│                    │ errors/ │ ← Reports          │
│                    └────┬────┘                     │
│                         │                          │
│                    ┌────▼──────────┐               │
│                    │ GitHub Actions│               │
│                    │ (CI/CD)       │               │
│                    │               │               │
│                    │ ├─ converters-ci              │
│                    │ ├─ dashboards-ci              │
│                    │ ├─ integration                │
│                    │ └─ deploy                     │
│                    └──────────────┘               │
└────────────────────────────────────────────────────┘
```

---

**Última actualización:** 2 de Junio de 2026
**Versión:** 1.0
