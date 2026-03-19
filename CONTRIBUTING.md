# 贡献指南

感谢你对 Agent Marketplace 的关注！欢迎贡献代码、文档或反馈。

## 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发环境设置](#开发环境设置)
- [代码规范](#代码规范)
- [提交信息规范](#提交信息规范)
- [测试要求](#测试要求)
- [Pull Request 流程](#pull-request-流程)

---

## 行为准则

请阅读并遵守我们的 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。

## 如何贡献

### 报告 Bug

1. 在 GitHub Issues 中搜索是否已有类似问题
2. 使用 Issue 模板创建新问题，包含：
   - 复现步骤
   - 期望行为
   - 实际行为
   - 环境信息

### 提出新功能

1. 先在 Issues 中讨论功能需求
2. 获得认可后，Fork 项目
3. 创建功能分支 `feature/your-feature`
4. 提交 Pull Request

---

## 开发环境设置

### 前置要求

- **Python 3.11+**
- **Node.js 18+**（如需前端）
- **Git**

### 步骤

```bash
# 1. Fork 并克隆项目
git clone https://github.com/your-username/agent-marketplace.git
cd agent-marketplace

# 2. 创建虚拟环境（推荐）
python -m venv venv

# Windows 激活
venv\Scripts\activate

# Linux/Mac 激活
source venv/bin/activate

# 3. 安装依赖
cd backend
pip install -r requirements.txt

# 4. 复制环境变量配置
cp .env.example .env

# 5. 初始化数据库
python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"

# 6. 运行测试确保环境正常
pytest

# 7. 启动开发服务器
python -m uvicorn app.main:app --reload
```

### 前端开发

```bash
cd frontend
npm install
npm run dev
```

---

## 代码规范

### Python

- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- 使用类型提示
- 使用 `black` 格式化代码
- 使用 `isort` 排序导入

```bash
# 安装开发工具
pip install black isort flake8 pytest pytest-cov

# 格式化代码
black .
isort .

# 检查代码风格
black --check .
isort --check .
flake8 .
```

### 配置文件

创建 `pyproject.toml`：

```toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100

[tool.flake8]
max-line-length = 100
exclude = [".git", "__pycache__", "venv"]
```

### 前端

- 遵循 ESLint 规则
- 使用 Prettier 格式化

```bash
cd frontend
npm install
npm run lint
```

---

## 提交信息规范

使用 [Conventional Commits](https://www.conventionalcomments.org/)：

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### 类型

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档修改 |
| `style` | 代码格式 |
| `refactor` | 重构 |
| `test` | 测试 |
| `chore` | 构建/工具 |

### 示例

```
feat(agent): 添加LLM Agent支持

添加基于OpenAI的智能Agent实现
支持规则引擎和LLM混合模式

Closes #123
```

---

## 测试要求

### 运行测试

```bash
# 全部测试
pytest

# 特定模块
pytest tests/test_protocol.py -v

# 带覆盖率
pytest --cov=app --cov-report=html
```

### 新功能测试

- 新功能必须包含单元测试
- 确保所有测试通过
- 建议覆盖率 > 70%

---

## Pull Request 流程

### 1. 创建分支

```bash
git checkout -b feature/amazing-feature
# 或
git checkout -b fix/bug-description
```

### 2. 开发

```bash
# 开发并测试
pytest

# 格式化代码
black .
isort .
```

### 3. 提交

```bash
git add .
git commit -m "feat: 添加新功能"
```

### 4. 推送

```bash
git push origin feature/amazing-feature
```

### 5. 创建 PR

1. 在 GitHub 上创建 Pull Request
2. 填写 PR 模板
3. 关联相关 Issue
4. 等待 CI 检查通过
5. 等待维护者审核

### PR 模板

```markdown
## 描述
<!-- 描述这个 PR 做什么 -->

## 类型
- [ ] 新功能 (feat)
- [ ] Bug 修复 (fix)
- [ ] 文档更新 (docs)
- [ ] 代码重构 (refactor)
- [ ] 测试 (test)
- [ ] 其他 (chore)

## 测试
<!-- 描述如何测试这个更改 -->

## 检查清单
- [ ] 我的代码遵循代码规范
- [ ] 我已经进行了自测
- [ ] 我已经添加了必要的测试
- [ ] 我的更改没有引入新的警告
```

---

## 评审流程

1. CI 检查通过（测试、格式化）
2. 至少一名维护者审核
3. 解决所有评论
4. 合并到主分支

---

## 问题？

- 欢迎在 [Discussions](https://github.com/agent-marketplace/discussions) 中提问
- 可以在 Discord 或 Telegram 联系团队

感谢你的贡献！ 🎉
