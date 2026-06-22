# PyCharm 配置修复指南（终端可运行但 PyCharm 不行）

## 问题分析

如果**终端可以正常运行**，但 PyCharm 显示 `Process finished with exit code 0`，说明：

✅ 代码没问题  
✅ 环境变量在终端中可用（可能是通过 `.env` 文件或系统环境变量）  
❌ PyCharm 运行配置缺少环境变量或配置不正确

## 快速修复方案

### 方案 1: 复制终端命令到 PyCharm（最简单）

#### 步骤 1: 查看终端中的完整命令

在终端中，你可能是这样运行的：

```bash
# 方式 A: 使用 uv run
uv run --env-file .env a2a-mcp --run mcp-server --transport sse --port 10100

# 方式 B: 直接运行 Python
python src/a2a_mcp/__init__.py --run mcp-server --host localhost --port 10100 --transport sse

# 方式 C: 使用模块方式
python -m a2a_mcp --run mcp-server --host localhost --port 10100 --transport sse
```

#### 步骤 2: 在 PyCharm 中配置环境变量

**关键步骤**：终端能运行说明环境变量已设置（可能是通过 `.env` 文件），但 PyCharm 需要手动配置。

1. **打开运行配置**
   - `Run` → `Edit Configurations...`

2. **添加环境变量**
   - 找到 `Environment variables`
   - 点击右侧的文件夹图标
   - 添加：
     ```
     OPENAI_API_KEY=你的实际API密钥
     ```

3. **或者使用 .env 文件路径**
   ```
   ENV_FILE=$ProjectFileDir$/.env
   ```

### 方案 2: 使用 Shell Script 配置（完全模拟终端）

如果终端使用 `uv run`，可以在 PyCharm 中创建 Shell Script 配置：

1. **创建新配置**
   - `Run` → `Edit Configurations...`
   - 点击 `+` → 选择 `Shell Script`

2. **配置参数**
   ```
   Name: a2a-mcp (Terminal方式)
   Script text: 
   cd $ProjectFileDir$ && uv run --env-file .env a2a-mcp --run mcp-server --transport sse --port 10100
   
   Working directory: $ProjectFileDir$
   ```

3. **运行**
   - 这样完全模拟终端命令

### 方案 3: 修改代码自动加载 .env（推荐）

让代码自动从 `.env` 文件加载环境变量，这样 PyCharm 和终端都能工作：

#### 修改 `src/a2a_mcp/__init__.py`

```python
"""Convenience methods to start servers."""

import os
import sys
from pathlib import Path

# 自动加载 .env 文件
def load_env_file():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                # 解析 KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    # 如果环境变量未设置，则设置它
                    if key and not os.getenv(key):
                        os.environ[key] = value

# 尝试加载 .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    # 如果没有 python-dotenv，使用手动加载
    load_env_file()

import click
from a2a_mcp.mcp import server


@click.command()
@click.option('--run', 'command', default='mcp-server', help='Command to run')
@click.option(
    '--host',
    'host',
    default='localhost',
    help='Host on which the server is started or the client connects to',
)
@click.option(
    '--port',
    'port',
    default=10100,
    help='Port on which the server is started or the client connects to',
)
@click.option(
    '--transport',
    'transport',
    default='stdio',
    help='MCP Transport',
)
def main(command, host, port, transport) -> None:
    """Start A2A MCP servers."""
    # 检查环境变量
    if not os.getenv('OPENAI_API_KEY'):
        print("ERROR: OPENAI_API_KEY is not set!")
        print("Please ensure .env file exists in project root or set environment variable.")
        sys.exit(1)
    
    if command == 'mcp-server':
        server.serve(host, port, transport)
    else:
        raise ValueError(f'Unknown run option: {command}')


if __name__ == '__main__':
    main()
```

## 对比终端和 PyCharm 的差异

### 终端环境
- ✅ 自动读取 `.env` 文件（如果使用 `uv run --env-file .env`）
- ✅ 继承系统环境变量
- ✅ 工作目录通常是项目根目录

### PyCharm 环境
- ❌ 不会自动读取 `.env` 文件（除非代码中实现）
- ❌ 不继承系统环境变量（除非在配置中设置）
- ⚠️ 工作目录需要手动设置

## 完整 PyCharm 配置示例

### 配置 1: Python 运行配置（推荐）

```
Name: a2a-mcp MCP Server
Script path: $ProjectFileDir$/src/a2a_mcp/__init__.py
Parameters: --run mcp-server --host localhost --port 10100 --transport sse
Working directory: $ProjectFileDir$
Python interpreter: [选择项目的虚拟环境]
Environment variables:
  OPENAI_API_KEY=你的实际API密钥
```

### 配置 2: Shell Script 配置（完全模拟终端）

```
Name: a2a-mcp (Shell)
Script text: cd $ProjectFileDir$ && uv run --env-file .env a2a-mcp --run mcp-server --transport sse --port 10100
Working directory: $ProjectFileDir$
```

## 验证步骤

### 1. 检查 .env 文件位置

确保 `.env` 文件在项目根目录（与 `pyproject.toml` 同级）：

```
项目根目录/
├── .env              ← 应该在这里
├── pyproject.toml
├── src/
└── ...
```

### 2. 检查 .env 文件内容

`.env` 文件应该包含：

```
OPENAI_API_KEY=你的实际API密钥
```

### 3. 在 PyCharm Terminal 中测试

在 PyCharm 的 Terminal 中运行：

```bash
# 检查环境变量
python -c "import os; print('OPENAI_API_KEY:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"

# 测试运行
python src/a2a_mcp/__init__.py --run mcp-server --host localhost --port 10100 --transport sse
```

### 4. 对比运行配置

确保 PyCharm 运行配置与终端命令一致：

| 项目 | 终端命令 | PyCharm 配置 |
|------|---------|-------------|
| 工作目录 | 项目根目录 | `$ProjectFileDir$` |
| 环境变量 | 从 `.env` 加载 | 手动设置或代码加载 |
| 参数 | `--run mcp-server ...` | `Parameters` 字段 |
| Transport | `sse` | `--transport sse` |

## 常见问题

### Q1: 为什么终端可以运行但 PyCharm 不行？

**A**: 终端可能通过以下方式获取环境变量：
- `uv run --env-file .env` 自动加载 `.env`
- 系统环境变量
- Shell 配置文件（如 `.bashrc`）

PyCharm 需要：
- 在运行配置中手动设置环境变量
- 或代码中实现自动加载 `.env`

### Q2: 如何让 PyCharm 自动读取 .env？

**A**: 两种方法：
1. **代码中实现**（推荐）：使用上面的改进版代码
2. **安装插件**：安装 "EnvFile" 插件，在运行配置中选择 `.env` 文件

### Q3: 使用 stdio 还是 sse？

**A**: 
- **终端**: 两种都可以
- **PyCharm**: 推荐使用 `sse`，因为 `stdio` 在某些情况下可能无法正常工作

### Q4: 如何确认服务器已启动？

**A**: 
1. **控制台输出**: 应该看到服务器启动日志
2. **进程持续运行**: 程序不会退出
3. **端口检查**: 
   ```bash
   netstat -ano | findstr :10100
   ```

## 推荐解决方案

### 最佳实践（三选一）

#### 选项 1: 修改代码自动加载 .env（最推荐）

- ✅ 终端和 PyCharm 都能工作
- ✅ 不需要手动配置环境变量
- ✅ 代码更健壮

使用上面的"方案 3"代码。

#### 选项 2: 在 PyCharm 配置中设置环境变量

- ✅ 简单直接
- ❌ 需要手动配置
- ❌ 每个配置都要设置

#### 选项 3: 使用 Shell Script 配置

- ✅ 完全模拟终端
- ✅ 不需要修改代码
- ⚠️ 调试可能不如 Python 配置方便

## 快速检查清单

- [ ] `.env` 文件在项目根目录
- [ ] `.env` 文件包含 `OPENAI_API_KEY`
- [ ] PyCharm 运行配置的 `Working directory` 设置为项目根目录
- [ ] PyCharm 运行配置的 `Parameters` 包含 `--transport sse`
- [ ] 如果使用 Python 配置，设置了 `Environment variables` 或代码自动加载 `.env`
- [ ] Python interpreter 选择的是项目虚拟环境

按照以上步骤配置后，PyCharm 应该能够正常运行了！
