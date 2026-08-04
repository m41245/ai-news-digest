# AI News Digest

A production-oriented AI-powered news aggregation and daily digest platform built with **Python**, **FastAPI**, **Clean Architecture**, and modern engineering practices.

The project is designed to collect articles from multiple RSS sources, organize and categorize them, generate AI-powered summaries, and produce high-quality daily news digests through a scalable and maintainable architecture.

> **Project Status:** Active Development 🚧

---

# Features

## Implemented

* Clean Architecture project structure
* Domain-driven design principles
* Domain entities and business models
* Repository interfaces (Ports)
* SQLAlchemy ORM models
* Repository implementations
* Database session management
* Strict static type checking with MyPy
* Ruff linting and formatting
* Poetry dependency management
* Configuration management using Pydantic Settings
* Production-ready project layout

## In Progress

* RSS feed ingestion
* AI-powered article summarization
* Article categorization
* FastAPI REST API
* Celery background workers
* Digest generation pipeline

## Planned

* Daily scheduled digest generation
* PDF and HTML digest export
* Authentication and authorization
* Monitoring and observability
* Docker deployment
* CI/CD pipeline
* Comprehensive automated testing

---

# Tech Stack

| Category              | Technology        |
| --------------------- | ----------------- |
| Language              | Python 3.12       |
| API                   | FastAPI           |
| Database              | PostgreSQL        |
| ORM                   | SQLAlchemy 2.x    |
| Migrations            | Alembic           |
| Queue                 | Celery            |
| Cache / Broker        | Redis             |
| AI                    | OpenAI, Anthropic |
| HTTP Client           | HTTPX             |
| RSS Parsing           | Feedparser        |
| Configuration         | Pydantic Settings |
| Dependency Management | Poetry            |
| Type Checking         | MyPy (Strict)     |
| Linting               | Ruff              |
| Testing               | Pytest            |

---

# Architecture

This project follows **Clean Architecture**, separating business rules from infrastructure concerns.

```text
src/
└── ai_news_digest/
    ├── core/
    ├── domain/
    │   ├── models/
    │   ├── enums/
    │   └── ports/
    ├── infrastructure/
    │   ├── database/
    │   ├── mappers/
    │   └── repositories/
    ├── application/
    └── api/
```

Core business logic remains independent of frameworks, databases, and external services.

---

# Development Standards

The project emphasizes maintainability and code quality.

* Strict type checking using MyPy
* Ruff linting and formatting
* Repository pattern
* Separation of concerns
* Dependency inversion
* Asynchronous database access
* Production-oriented project organization

---

# Getting Started

## Clone the repository

```bash
git clone <repository-url>
cd ai-news-digest
```

## Install dependencies

```bash
poetry install
```

## Activate the environment

```bash
poetry shell
```

## Run static analysis

```bash
poetry run mypy
poetry run ruff check .
```

---

# Roadmap

* Complete RSS ingestion pipeline
* Integrate AI summarization providers
* Build digest generation service
* Expose REST API endpoints
* Add background processing with Celery
* Expand automated test coverage
* Containerize the application
* Configure CI/CD workflows

---

# Current Status

The foundational architecture and persistence layer are complete. Development is currently focused on implementing the application workflows, API endpoints, background processing, and AI-powered news summarization.

---

# License

This project is licensed under the MIT License.
