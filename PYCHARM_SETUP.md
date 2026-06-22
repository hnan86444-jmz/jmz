# PyCharm 中启动 a2a-mcp 配置指南

## 方法一：使用 Python 运行配置（推荐）

### 步骤 1: 创建运行配置

1. **打开运行配置**
   - 点击 PyCharm 顶部菜单：`Run` → `Edit Configurations...`
   - 或点击工具栏的运行配置下拉菜单 → `Edit Configurations...`

2. **添加新配置**
   - 点击左上角的 `+` 号
   - 选择 `Python`

3. **配置参数**

   **基本设置**:
   ```
   Name: a2a-mcp MCP Server
   Script path: [项目路径]/src/a2a_mcp/__init__.py
   Parameters: --run mcp-server --host localhost --port 10100 --transport sse
   Working directory: [项目路径]
   Python interpreter: [选择项目的虚拟环境]
   ```

   **详细配置**:
   - **Name**: `a2a-mcp MCP Server`
   - **Script path**: 
     ```
     $ProjectFileDir$/src/a2a_mcp/__init__.py
     ```
     或绝对路径：
     ```
     C:\Users\24514\Desktop\a2a-samples\samples\python\agents\a2a_mcp\src\a2a_mcp\__init__.py
     ```
   - **Parameters**: 
     ```
     --run mcp-server --host localhost --port 10100 --transport sse
     ```
   - **Working directory**: 
     ```
     $ProjectFileDir$
     ```
     或：
     ```
     C:\Users\24514\Desktop\a2a-samples\samples\python\agents\a2a_mcp
     ```

### 步骤 2: 配置环境变量

1. **在运行配置中添加环境变量**
   - 在运行配置窗口中，找到 `Environment variables`
   - 点击右侧的文件夹图标
   - 添加以下环境变量：

   ```
   OPENAI_API_KEY=your_api_key_here
   ```

2. **或使用 .env 文件**
   - 在 `Environment variables` 中添加：
   ```
   ENV_FILE=.env
   ```
   - 确保项目根目录有 `.env` 文件

### 步骤 3: 配置 Python 解释器

1. **选择虚拟环境**
   - 在运行配置的 `Python interpreter` 下拉菜单中
   - 选择项目的虚拟环境（`.venv`）
   - 如果没有，点击 `Show All` → `+` → 选择 `.venv` 目录

2. **验证依赖**
   - 确保虚拟环境中已安装所有依赖
   - 可以在 PyCharm 的 Terminal 中运行：
     ```bash
     uv sync
     ```

### 步骤 4: 运行

- 点击运行按钮（绿色三角形）
- 或使用快捷键：`Shift + F10`

---

## 方法二：使用 uv 命令运行

### 步骤 1: 创建 Shell 脚本运行配置

1. **添加新配置**
   - 点击 `+` → 选择 `Shell Script`

2. **配置参数**

   ```
   Name: a2a-mcp (uv)
   Script text: 
   cd $ProjectFileDir$ && uv run --env-file .env a2a-mcp --run mcp-server --transport sse --port 10100
   
   Working directory: $ProjectFileDir$
   ```

### 步骤 2: 运行

- 直接运行配置即可

---

## 方法三：使用 Python 模块运行（最灵活）

### 步骤 1: 创建运行配置

1. **添加 Python 配置**
   - 点击 `+` → 选择 `Python`

2. **配置参数**

   ```
   Name: a2a-mcp Module
   Module name: a2a_mcp
   Parameters: --run mcp-server --host localhost --port 10100 --transport sse
   Working directory: $ProjectFileDir$
   Python interpreter: [选择虚拟环境]
   ```

   **注意**: 使用 `Module name` 而不是 `Script path`

### 步骤 2: 配置环境变量

- 与方法一相同，添加 `OPENAI_API_KEY` 环境变量

---

## 完整配置示例

### 配置 1: MCP Server（默认）

```
Name: MCP Server
Script path: $ProjectFileDir$/src/a2a_mcp/__init__.py
Parameters: --run mcp-server --host localhost --port 10100 --transport sse
Working directory: $ProjectFileDir$
Python interpreter: [项目虚拟环境]
Environment variables:
  OPENAI_API_KEY=your_api_key_here
```

### 配置 2: MCP Server（生产环境）

```
Name: MCP Server (Production)
Script path: $ProjectFileDir$/src/a2a_mcp/__init__.py
Parameters: --run mcp-server --host 0.0.0.0 --port 10100 --transport sse
Working directory: $ProjectFileDir$
Python interpreter: [项目虚拟环境]
Environment variables:
  OPENAI_API_KEY=your_api_key_here
```

### 配置 3: MCP Server（自定义端口）

```
Name: MCP Server (Port 10200)
Script path: $ProjectFileDir$/src/a2a_mcp/__init__.py
Parameters: --run mcp-server --host localhost --port 10200 --transport sse
Working directory: $ProjectFileDir$
Python interpreter: [项目虚拟环境]
Environment variables:
  OPENAI_API_KEY=your_api_key_here
```

---

## 使用 .env 文件

### 方法 A: 在运行配置中加载 .env

1. **安装 python-dotenv**（如果还没有）
   ```bash
   uv add python-dotenv
   ```

2. **修改代码加载 .env**
   - 在 `src/a2a_mcp/__init__.py` 开头添加：
   ```python
   from dotenv import load_dotenv
   import os
   
   # 加载 .env 文件
   load_dotenv()
   ```

3. **运行配置中不需要手动设置环境变量**

### 方法 B: 使用环境变量文件

在运行配置的 `Environment variables` 中：
```
ENV_FILE=$ProjectFileDir$/.env
```

---

## 调试配置

### 设置断点调试

1. **在代码中设置断点**
   - 在 `src/a2a_mcp/__init__.py` 或 `src/a2a_mcp/common/mcp_server.py` 中点击行号左侧

2. **使用调试模式运行**
   - 点击调试按钮（绿色虫子图标）
   - 或使用快捷键：`Shift + F9`

3. **调试配置**
   - 使用与方法一相同的配置
   - 确保 `Attach to subprocess` 选项已启用（如果需要）

---

## 常见问题解决

### 问题 1: 模块未找到

**错误**: `ModuleNotFoundError: No module named 'a2a_mcp'`

**解决方案**:
1. 确保项目根目录被标记为 `Sources Root`
   - 右键项目根目录 → `Mark Directory as` → `Sources Root`
2. 确保虚拟环境正确配置
3. 在 Terminal 中运行 `uv sync` 安装依赖

### 问题 2: 环境变量未加载

**错误**: `OPENAI_API_KEY is not set`

**解决方案**:
1. 检查运行配置中的环境变量设置
2. 确保 `.env` 文件在项目根目录
3. 使用 `python-dotenv` 自动加载 `.env` 文件

### 问题 3: 端口已被占用

**错误**: `OSError: [Errno 98] Address already in use`

**解决方案**:
1. 修改运行配置中的端口号
2. 或在 Terminal 中查找并关闭占用端口的进程：
   ```bash
   # Windows
   netstat -ano | findstr :10100
   taskkill /PID <PID> /F
   ```

### 问题 4: Click 命令未识别

**错误**: `AttributeError: module 'a2a_mcp' has no attribute 'main'`

**解决方案**:
1. 确保使用 `Script path` 指向 `__init__.py`
2. 或使用 `Module name: a2a_mcp` 方式运行

---

## 快速启动模板

### 模板 1: 基础配置（复制粘贴到运行配置）

```json
{
  "name": "a2a-mcp MCP Server",
  "type": "python",
  "request": "launch",
  "program": "${workspaceFolder}/src/a2a_mcp/__init__.py",
  "args": [
    "--run",
    "mcp-server",
    "--host",
    "localhost",
    "--port",
    "10100",
    "--transport",
    "sse"
  ],
  "console": "integratedTerminal",
  "cwd": "${workspaceFolder}",
  "env": {
    "OPENAI_API_KEY": "your_api_key_here"
  },
  "python": "${workspaceFolder}/.venv/Scripts/python.exe"
}
```

### 模板 2: 使用 .env 文件

```json
{
  "name": "a2a-mcp (with .env)",
  "type": "python",
  "request": "launch",
  "module": "a2a_mcp",
  "args": [
    "--run",
    "mcp-server",
    "--transport",
    "sse"
  ],
  "console": "integratedTerminal",
  "cwd": "${workspaceFolder}",
  "envFile": "${workspaceFolder}/.env"
}
```

---

## 推荐配置流程

### 第一次设置

1. ✅ **打开项目**
   - 在 PyCharm 中打开项目目录

2. ✅ **配置 Python 解释器**
   - `File` → `Settings` → `Project: a2a-mcp` → `Python Interpreter`
   - 选择或创建虚拟环境（`.venv`）

3. ✅ **安装依赖**
   - 在 Terminal 中运行：`uv sync`

4. ✅ **创建 .env 文件**
   - 在项目根目录创建 `.env` 文件
   - 添加：`OPENAI_API_KEY=your_api_key_here`

5. ✅ **创建运行配置**
   - 使用"方法一"创建运行配置
   - 设置环境变量或使用 `.env` 文件

6. ✅ **测试运行**
   - 点击运行按钮
   - 检查控制台输出，确认服务器启动成功

---

## 多配置管理

### 创建配置组

可以创建多个运行配置，方便切换：

1. **MCP Server (开发)**
   - 端口: 10100
   - 主机: localhost
   - 传输: sse

2. **MCP Server (测试)**
   - 端口: 10200
   - 主机: localhost
   - 传输: sse

3. **MCP Server (生产)**
   - 端口: 10100
   - 主机: 0.0.0.0
   - 传输: sse

### 使用配置模板

1. 创建第一个配置后
2. 右键配置 → `Copy Configuration`
3. 修改参数创建新配置

---

## 快捷键设置

### 自定义快捷键

1. `File` → `Settings` → `Keymap`
2. 搜索 "Run" 或 "Debug"
3. 为常用配置设置快捷键

### 常用快捷键（默认）

- `Shift + F10`: 运行当前配置
- `Shift + F9`: 调试当前配置
- `Ctrl + Shift + F10`: 运行当前文件
- `Ctrl + Shift + F9`: 调试当前文件

---

## 日志查看

### 在 PyCharm 中查看日志

1. **控制台输出**
   - 运行后，日志会显示在 PyCharm 底部的 `Run` 窗口

2. **保存日志**
   - 右键控制台 → `Save console output to file`

3. **过滤日志**
   - 使用控制台的搜索功能
   - 或配置日志级别（通过环境变量）

---

## 总结

### 推荐方法

**最简单**: 使用方法一（Python 运行配置）
- 直接运行 `__init__.py`
- 配置简单直观
- 支持调试

**最灵活**: 使用方法三（模块运行）
- 使用模块名运行
- 更符合 Python 包结构

**最接近命令行**: 使用方法二（Shell 脚本）
- 完全模拟命令行执行
- 适合熟悉命令行的开发者

### 快速检查清单

- [ ] Python 解释器已配置（虚拟环境）
- [ ] 依赖已安装（`uv sync`）
- [ ] `.env` 文件已创建并配置
- [ ] 运行配置已创建
- [ ] 环境变量已设置（或使用 .env）
- [ ] 端口未被占用
- [ ] 可以成功运行

按照以上步骤配置后，就可以在 PyCharm 中方便地启动和管理 `a2a-mcp` 服务器了！
