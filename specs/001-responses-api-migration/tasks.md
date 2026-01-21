# Tasks: 响应式评分接口迁移

**Input**: Design documents from `/specs/001-responses-api-migration/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Not requested

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 [P] Create response-based client wrapper in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/llm_client.py`
- [X] T002 [P] Create response-based score processor skeleton in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/score_processor_v2.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Update scoring interface to support session init/standard/batch flow in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/interface.py`
- [X] T004 Wire new processor selection and per-homework session routing in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/homework_grader.py`
- [X] T005 Enforce logging + type hints + docstrings in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/llm_client.py`, `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/score_processor_v2.py`, `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/homework_grader.py`, `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/interface.py`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - 高效生成评分标准 (Priority: P1) 🎯 MVP

**Goal**: 分析阶段一次性生成评分标准与样本分数，移除 pass 模式

**Independent Test**: 提供 5-8 名样本答案后生成评分标准与样本分数

### Implementation for User Story 1

- [X] T006 [US1] Implement analysis-stage scoring without pass placeholders in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/score_processor_v2.py`
- [X] T007 [US1] Decouple grading standard from sample scores and persist independently in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/score_processor_v2.py`

**Checkpoint**: User Story 1 should be independently functional

---

## Phase 4: User Story 2 - 复用上下文批量评分 (Priority: P2)

**Goal**: 复用评分上下文并批量评分 3-5 名学生

**Independent Test**: 基于同一作业 session 连续分批评分 3-5 名学生

### Implementation for User Story 2

- [X] T008 [US2] Implement per-homework session initialization and reuse in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/score_processor_v2.py`
- [X] T009 [US2] Implement batch scoring (3-5 students) with retryable partial failure handling in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/score_processor_v2.py`
- [X] T010 [US2] Batch students per homework and invoke session scoring in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/homework_grader.py`

**Checkpoint**: User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - 结果稳定且可追溯 (Priority: P3)

**Goal**: 输出结构稳定、评分依据可追溯、分数一致性可控

**Independent Test**: 同水平作业评分差异不超过 5 分且输出结构兼容

### Implementation for User Story 3

- [X] T011 [US3] Normalize batch scoring outputs to existing schema in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/score_processor_v2.py`
- [X] T012 [US3] Preserve output persistence format in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/grader/file_manager.py`

**Checkpoint**: All user stories should now be independently functional

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T013 Update validation steps in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/specs/001-responses-api-migration/quickstart.md`
- [ ] T014 Run quickstart validation and record results in `/Users/jixiaojian/Desktop/code/Chaoxing_Homework/specs/001-responses-api-migration/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: Depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational
- **User Story 2 (P2)**: Can start after Foundational; depends on US1 artifacts
- **User Story 3 (P3)**: Can start after Foundational; depends on US2 outputs

### Parallel Opportunities

- T001 and T002 can run in parallel (different files)
- User Story 1 tasks are sequential within `grader/score_processor_v2.py`
- User Story 2 tasks are sequential within `grader/score_processor_v2.py`

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate analysis stage without pass placeholders

### Incremental Delivery

1. Complete Setup + Foundational
2. Deliver User Story 1
3. Deliver User Story 2
4. Deliver User Story 3
5. Polish validation updates
