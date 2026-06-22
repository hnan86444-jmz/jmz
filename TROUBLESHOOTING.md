# 故障排除：服务器未启动问题

## 问题描述

运行命令后显示 `Process finished with exit code 0`，但服务器没有启动。

## 可能原因和解决方案

### 原因 1: 环境变量未设置（最常见）

**症状**: 程序立即退出，退出代码 0，没有错误信息

**检查方法**:
1. 在 PyCharm 运行配置中检查 `Environment variables`
2. 确认是否有 `OPENAI_API_KEY`

**解决方案**:

#### 方法 A: 在运行配置中设置环境变量

1. 打开运行配置
2. 找到 `Environment variables`
3. 添加：
   ```
   OPENAI_API_KEY=your_actual_api_key_here
   ```

#### 方法 B: 使用 .env 文件（推荐）

1. **在项目根目录创建 `.env` 文件**:
   ```
   OPENAI_API_KEY=your_actual_api_key_here
   ```

2. **修改代码自动加载 .env**:
   
   在 `src/a2a_mcp/__init__.py` 开头添加：
   ```python
   """Convenience methods to start servers."""
   
   import os
   from pathlib import Path
   
   # 加载 .env 文件
   try:
       from dotenv import load_dotenv
       env_path = Path(__file__).parent.parent.parent / '.env'
       load_dotenv(dotenv_path=env_path)
   except ImportError:
       # 如果没有安装 python-dotenv，尝试手动读取
       env_path = Path(__file__).parent.parent.parent / '.env'
       if env_path.exists():
           with open(env_path) as f:
               for line in f:
                   if '=' in line and not line.strip().startswith('#'):
                       key, value = line.strip().split('=', 1)
                       os.environ[key] = value
   
   import click
   from a2a_mcp.common.mcp_server import serve
   ```

3. **安装 python-dotenv**（如果使用方法 B）:
   ```bash
   uv add python-dotenv
   ```

### 原因 2: stdio Transport 在 PyCharm 中不工作

**症状**: 使用 `--transport stdio` 时程序立即退出

**原因**: stdio transport 需要标准输入输出，在 PyCharm 的某些配置下可能无法正常工作

**解决方案**: 使用 `sse` transport

修改运行配置的 Parameters:
```
--run mcp-server --host localhost --port 10100 --transport sse
```

### 原因 3: 缺少日志输出，无法看到错误

**症状**: 程序退出但没有错误信息

**解决方案**: 添加日志配置

在 `src/a2a_mcp/__init__.py` 中添加日志：

```python
"""Convenience methods to start servers."""

import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

import click
from a2a_mcp.common.mcp_server import serve


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
    logger.info(f"Starting {command} with host={host}, port={port}, transport={transport}")
    
    try:
        if command == 'mcp-server':
            logger.info("Calling serve()...")
            serve(host, port, transport)
            logger.info("Server started successfully")
        else:
            raise ValueError(f'Unknown run option: {command}')
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
```

### 原因 4: 异常被静默捕获

**症状**: 程序退出但没有错误信息

**解决方案**: 添加异常处理

在 `src/a2a_mcp/__init__.py` 的 `main` 函数中添加：

```python
def main(command, host, port, transport) -> None:
    """Start A2A MCP servers."""
    try:
        if command == 'mcp-server':
            serve(host, port, transport)
        else:
            raise ValueError(f'Unknown run option: {command}')
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

## 完整的改进版代码

### 改进的 `src/a2a_mcp/__init__.py`

```python
"""Convenience methods to start servers."""

import logging
import os
import sys
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logger.info(f"Loaded .env file from {env_path}")
    else:
        logger.warning(f".env file not found at {env_path}")
except ImportError:
    logger.warning("python-dotenv not installed, .env file will not be auto-loaded")
    # 手动读取 .env（简单实现）
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        logger.info(f"Manually loaded .env file from {env_path}")

import click
from a2a_mcp.common.mcp_server import serve


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
    logger.info("=" * 60)
    logger.info(f"Starting {command}")
    logger.info(f"Host: {host}, Port: {port}, Transport: {transport}")
    logger.info("=" * 60)
    
    # 检查环境变量
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("OPENAI_API_KEY environment variable is not set!")
        logger.error("Please set it in:")
        logger.error("  1. PyCharm Run Configuration -> Environment variables")
        logger.error("  2. Or create a .env file in the project root")
        sys.exit(1)
    else:
        logger.info("OPENAI_API_KEY is set (length: %d)", len(os.getenv('OPENAI_API_KEY')))
    
    try:
        if command == 'mcp-server':
            logger.info("Initializing MCP server...")
            serve(host, port, transport)
            # 注意: serve() 应该阻塞运行，不会返回
            # 如果执行到这里，说明服务器意外退出了
            logger.warning("Server exited unexpectedly")
        else:
            raise ValueError(f'Unknown run option: {command}')
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user (Ctrl+C)")
        sys.exit(0)
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
```

## 诊断步骤

### 步骤 1: 检查环境变量

在 PyCharm Terminal 中运行：

```bash
python -c "import os; print('OPENAI_API_KEY:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"
```

### 步骤 2: 测试直接运行

在 PyCharm Terminal 中运行：

```bash
cd C:\Users\24514\Desktop\mcp-server-demo\a2a_mcp
python src/a2a_mcp/__init__.py --run mcp-server --host localhost --port 10100 --transport sse
```

### 步骤 3: 检查日志输出

运行后查看控制台输出，应该看到：
- 日志配置信息
- 环境变量检查结果
- 服务器启动信息

### 步骤 4: 验证服务器是否运行

如果使用 `sse` transport，服务器应该监听在指定端口。

在另一个 Terminal 中测试：

```bash
# 检查端口是否被占用
netstat -ano | findstr :10100

# 或使用 curl 测试（如果有健康检查端点）
curl http://localhost:10100
```

## PyCharm 运行配置检查清单

- [ ] **Script path**: 指向 `src/a2a_mcp/__init__.py`
- [ ] **Parameters**: `--run mcp-server --host localhost --port 10100 --transport sse`
- [ ] **Working directory**: 项目根目录（包含 `pyproject.toml` 的目录）
- [ ] **Python interpreter**: 选择项目的虚拟环境
- [ ] **Environment variables**: 设置了 `OPENAI_API_KEY` 或使用 `.env` 文件
- [ ] **Transport**: 使用 `sse` 而不是 `stdio`（在 PyCharm 中更可靠）

## 快速修复方案

### 方案 1: 最简单的修复

1. **在运行配置中添加环境变量**:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

2. **修改 Parameters**:
   ```
   --run mcp-server --host localhost --port 10100 --transport sse
   ```

3. **重新运行**

### 方案 2: 使用 .env 文件

1. **创建 `.env` 文件**（在项目根目录）:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

2. **安装 python-dotenv**:
   ```bash
   uv add python-dotenv
   ```

3. **使用上面的改进版代码**（自动加载 .env）

4. **重新运行**

## 验证服务器是否成功启动

### 成功启动的标志

1. **控制台输出**:
   ```
   Starting mcp-server
   Host: localhost, Port: 10100, Transport: sse
   Starting Agent Cards MCP Server
   Agent cards MCP Server at localhost:10100 and transport sse
   ```

2. **进程持续运行**: 程序不会退出，保持运行状态

3. **端口监听**: 使用 `netstat` 或 `lsof` 检查端口

### 如果仍然无法启动

1. **检查完整错误信息**: 查看 PyCharm 控制台的完整输出
2. **尝试命令行运行**: 在 Terminal 中直接运行，看是否有不同
3. **检查依赖**: 确保所有依赖都已安装（`uv sync`）
4. **检查 Python 版本**: 确保使用 Python 3.11+

## 常见错误信息

### 错误 1: `OPENAI_API_KEY is not set`
**解决**: 设置环境变量或创建 `.env` 文件

### 错误 2: `Address already in use`
**解决**: 端口被占用，修改端口号或关闭占用进程

### 错误 3: `ModuleNotFoundError`
**解决**: 运行 `uv sync` 安装依赖

### 错误 4: 程序立即退出无错误
**解决**: 
- 检查环境变量
- 使用 `sse` transport
- 添加日志查看详细输出
