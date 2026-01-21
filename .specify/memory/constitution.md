<!-- Sync Impact Report:
Version change: N/A (template) -> 1.0.0
Modified principles: PRINCIPLE_1_NAME (template) -> I. Async Playwright-First
Crawler; PRINCIPLE_2_NAME (template) -> II. Scoped Change & Compatibility;
PRINCIPLE_3_NAME (template) -> III. Managed Browser Lifecycle & Concurrency;
PRINCIPLE_4_NAME (template) -> IV. Type-Safe, Documented, Observable Code;
PRINCIPLE_5_NAME (template) -> V. Explicit
Module Responsibilities
Added sections: Technical Requirements; Migration Constraints & File Protections
Removed sections: None
Templates requiring updates: .specify/templates/plan-template.md (updated),
.specify/templates/spec-template.md (updated), .specify/templates/tasks-template.md
(updated), .specify/templates/checklist-template.md (updated),
.specify/templates/agent-file-template.md (pending)
Follow-up TODOs: TODO(RATIFICATION_DATE) original adoption date unknown
-->
# Chaoxing_Homework Constitution

## Core Principles

### I. Async Playwright-First Crawler
All crawler automation MUST use Playwright async APIs with async/await and
asyncio. Selenium is prohibited. Rationale: ensures a single async architecture
for the migration and avoids mixed sync/async behaviors.

### II. Scoped Change & Compatibility
Changes MUST be limited to the crawler migration. The grader module and
`config/_args.py` plus `config/config_manager.py` MUST NOT be modified.
Configuration access MUST use safe defaults (e.g., `getattr`) to preserve
backward compatibility. Output JSON schema MUST remain unchanged to keep grader
integration stable. Rationale: protects existing grading behavior and users.

### III. Managed Browser Lifecycle & Concurrency
Browser lifecycle MUST be centralized in `core/browser.py` via `BrowserManager`.
All contexts and pages MUST be created and closed through async context managers.
Concurrency MUST be bounded with `asyncio.Semaphore` and never left unbounded.
Rationale: prevents leaks and keeps crawling reliable under load.

### IV. Type-Safe, Documented, Observable Code
All new crawler code MUST include type hints. Each class and public method MUST
have a docstring. Logging MUST use the standard `logging` module; `print` is
forbidden. Rationale: improves maintainability and debugging in async flows.

### V. Explicit Module Responsibilities
Modules MUST keep clear ownership: `core/browser.py` handles browser lifecycle,
`crawler/client.py` wraps page operations and response capture, `crawler/auth/*`
implements login strategies, `crawler/crawler.py` orchestrates the crawl, and
`crawler/processor.py` handles per-homework processing. Rationale: prevents
coupling and keeps the architecture testable.

## Technical Requirements

- Runtime: Python 3.8+
- Browser automation: Playwright async (`playwright>=1.40.0`), `asyncio`
- HTML parsing: BeautifulSoup4
- Dependencies: remove `selenium` and `webdriver-manager`
- Output format: JSON schema MUST remain compatible with the existing grader

## Migration Constraints & File Protections

- Do not modify: `grader/`, `config/_args.py`, `config/config_manager.py`
- Target structure MUST include: `core/browser.py`, `crawler/client.py`,
  `crawler/auth/`, `crawler/crawler.py`, `crawler/processor.py`
- Remove after migration: `crawler/webdriver_factory.py`,
  `crawler/homework_crawler.py`, `crawler/homework_processor_impl.py`,
  `crawler/login_strategies.py`
- Configuration compatibility MUST use safe fallbacks (e.g., `getattr`)

## Governance

- This constitution supersedes all other practices for this repository.
- Amendments MUST include: documented rationale, updated version (semver), and
  migration notes for breaking changes.
- All plans/specs/tasks MUST include a Constitution Check; reviewers MUST block
  changes that violate principles or protected file constraints.
- Runtime guidance lives in `README.md` and the migration brief
  `doc/constitution_Version3.md` until replaced.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): original adoption date
unknown | **Last Amended**: 2026-01-21
