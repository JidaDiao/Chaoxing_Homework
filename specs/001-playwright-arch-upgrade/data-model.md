# Data Model: Playwright 架构升级

## Entities

### Course
- **Fields**: `course_url` (string, unique), `course_name` (string, optional)
- **Notes**: 以课程入口 URL 作为主标识

### Class
- **Fields**: `class_id` (string), `class_name` (string), `course_url` (string)
- **Notes**: `class_id` 在同一课程内唯一

### Homework Task
- **Fields**: `homework_name` (string), `answer_time` (string), `review_url` (string),
  `pending_count` (int), `save_path` (string)
- **Notes**: 唯一键建议为 `class_id + homework_name + answer_time`

### Student
- **Fields**: `name` (string), `review_url` (string)
- **Notes**: 在同一作业任务内按姓名唯一

### Answer Result (输出结构)
- **Fields**:
  - `题目`: `{题目N: {题干: {text: [string], images: [string]}, 正确答案: string}}`
  - `学生回答`: `{学生名: {题目N: {text: [string], images: [string]}}}`
- **Notes**: 结构必须与现有批改模块兼容

## Relationships

- Course 1..* Class
- Class 1..* Homework Task
- Homework Task 1..* Student
- Homework Task 1..1 Answer Result

## Validation Rules

- 课程列表为空时拒绝启动爬取
- `review_url` 不能为空且必须可解析
- `pending_count` 小于等于阈值时可跳过
- 输出路径存在时覆盖同名结果
- 日志不得记录学生姓名与作答内容

## State Transitions

- Homework Task: `待处理` -> `处理中` -> `成功` / `失败`
- Student: `待获取` -> `获取中` -> `成功` / `失败`

## Data Volume Assumptions

- 代表性规模 <= 10 门课、100 个作业
- 单作业学生数量不确定，需支持高并发抓取
