---

description: "Task list for Playwright 架构升级"
---

# Tasks: Playwright 架构升级

**Input**: Design documents from `/specs/001-playwright-arch-upgrade/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: 未在规格中要求测试，本任务列表不包含测试任务。

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: Repository root
- Paths shown below use absolute paths per instructions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Update dependencies in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/requirements.txt` (add Playwright + BeautifulSoup4, remove selenium/webdriver-manager if present)
- [X] T002 Create package scaffolding for new modules in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/core/__init__.py` and `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/auth/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Implement `BrowserManager` with async lifecycle, semaphore, and cookie sharing in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/core/browser.py`
- [X] T004 [P] Implement `CrawlerClient` helpers (response capture, fetch_html/json, download) in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/client.py`
- [X] T005 Implement `LoginStrategy` base interface in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/auth/base.py`
- [X] T006 [P] Implement `PasswordLoginStrategy` in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/auth/password.py`
- [X] T007 [P] Implement `QRCodeLoginStrategy` in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/auth/qrcode.py`
- [X] T008 Implement `create_login_strategy` factory in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/auth/__init__.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Constitution-Driven Tasks (Mandatory When Applicable)

**Purpose**: Enforce constitution constraints early to prevent rework

- [X] T009 Remove legacy Selenium files: `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/webdriver_factory.py`, `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/homework_crawler.py`, `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/homework_processor_impl.py`, `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/login_strategies.py`
- [X] T010 Audit and enforce log redaction (no student names/answers) in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/crawler.py` and `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/processor.py`
- [X] T011 Ensure type hints + docstrings for all new public APIs in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/core/browser.py`, `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/client.py`, `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/auth/base.py`, `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/auth/password.py`, `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/auth/qrcode.py`, `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/crawler.py`, `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/processor.py`
- [X] T012 Enforce bounded concurrency with default >8 in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/crawler.py` (via `getattr` default) and confirm semaphore usage in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/core/browser.py`

---

## Phase 3: User Story 1 - 稳定完成作业爬取 (Priority: P1) 🎯 MVP

**Goal**: 稳定完成作业爬取并保存结果，保证登录失败立即退出

**Independent Test**: 使用有效账号与课程配置运行爬取流程，确认结果落盘并可读取

### Implementation for User Story 1

- [X] T013 [US1] Implement async crawl flow (login → fetch tasks → concurrent processing → collect results) in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/crawler.py`
- [X] T014 [P] [US1] Implement `HomeworkProcessor` for student list and answers parsing in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/processor.py`
- [X] T015 [US1] Implement result persistence and overwrite behavior in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/crawler.py`
- [X] T016 [US1] Update async entrypoint and modes in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/main.py`
- [X] T017 [US1] Update manual crawler smoke script in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler_test.py`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - 按课程/班级/作业筛选 (Priority: P2)

**Goal**: 支持按课程、班级、作业名与未批改人数阈值筛选

**Independent Test**: 仅配置单一课程/班级/作业名，运行后仅处理目标范围

### Implementation for User Story 2

- [X] T018 [US2] Add filtering for course/class/homework/min_ungraded in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/crawler.py`
- [X] T019 [US2] Implement class ID mapping and class-specific list URL construction in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/crawler.py`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - 批改模块无缝兼容 (Priority: P3)

**Goal**: 输出结构保持兼容，批改模块无需修改

**Independent Test**: 用迁移后的结果运行批改流程，确保正常完成

### Implementation for User Story 3

- [X] T020 [US3] Align output JSON schema with grader expectations in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/processor.py`
- [X] T021 [US3] Document compatibility validation steps in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/specs/001-playwright-arch-upgrade/quickstart.md`

**Checkpoint**: All user stories should now be independently functional

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T022 [P] Record Playwright MCP crawl verification notes in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/specs/001-playwright-arch-upgrade/quickstart.md`
- [X] T023 Run quickstart validation and update steps in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/specs/001-playwright-arch-upgrade/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **Constitution Tasks**: Can run after Phase 2; some items require P1 files to exist
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2)
- **User Story 2 (P2)**: Depends on US1 baseline crawl flow
- **User Story 3 (P3)**: Depends on US1 output flow; can run in parallel with US2 after US1

### Within Each User Story

- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T003 and T004 can run in parallel (different files)
- T006 and T007 can run in parallel (different files)
- T014 can run in parallel with T013 (different files)

---

## Parallel Example: User Story 1

```bash
Task: "Implement async crawl flow in /Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/crawler.py"
Task: "Implement HomeworkProcessor in /Users/jixiaojian/Desktop/code/Chaoxing_Homework/crawler/processor.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
