# Research: Project Organization & Architecture Foundation

**Date**: 2026-05-14 | **Scope**: Technical decisions for organizational infrastructure

## Decision 1: CI/CD Platform

**Decision**: GitHub Actions  
**Rationale**: Native to GitHub, free tier sufficient for team of 6, simple YAML configuration  
**Alternatives**: GitLab CI (requires migration), Jenkins (unnecessary complexity)

## Decision 2: Configuration Management

**Decision**: Dual approach - .env files for local development, environment variables for production  
**Rationale**: Simple for developers, secure for production, standard practice  
**Config file**: `config/.env.example` as template, `.env` git-ignored locally

## Decision 3: Testing Framework

**Decision**: pytest with minimum 80% code coverage  
**Rationale**: Simple syntax, excellent fixtures, strong CI/CD integration  
**Enforcement**: pytest-cov plugin, build fails if coverage < 80%

## Decision 4: Secret Prevention

**Decision**: Multi-layer approach (pre-commit hook + GitHub secret scanning + .gitignore)  
**Rationale**: Defense in depth, catches issues before and after push  
**Implementation**: Hook script prevents .env commits, GitHub scanning catches any slips

## Decision 5: Documentation Standard

**Decision**: Plain Markdown in `docs/` directory  
**Rationale**: No dependencies, Git-friendly, renders in GitHub UI  
**Scalability**: Can migrate to MkDocs for HTML generation later

## Decision 6: Deployment Approach

**Decision**: Optional Docker (Dockerfile for production, not required locally)  
**Rationale**: Local simplicity (venv + pip), production consistency (Docker)  
**Flexibility**: Team can use Docker locally if preferred

## Decision 7: Versioning

**Decision**: Semantic Versioning (MAJOR.MINOR.PATCH)  
**Rationale**: Industry standard, communicates change impact  
**Storage**: VERSION file at project root, used in git tags for releases

---

## All Research Questions Resolved

Ready for Phase 1: Design & Contracts
