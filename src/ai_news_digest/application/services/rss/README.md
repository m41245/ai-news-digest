# RSS Service

The RSS service is responsible for downloading RSS and Atom feeds.

## Responsibilities

- Download feed XML
- Handle retries
- Handle timeouts
- Raise typed exceptions
- Return raw XML

## This package does NOT

- Parse XML
- Save articles
- Perform deduplication
- Call AI providers

Those responsibilities belong to higher layers.