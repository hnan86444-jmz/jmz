# 代码分析：MCP 服务器启动入口

## 代码位置
`src/a2a_mcp/__init__.py`

## 功能概述

这是一个使用 **Click** 框架构建的命令行接口（CLI），作为项目的入口点，用于启动 MCP (Model Context Protocol) 服务器。

## 详细分析

### 1. 导入依赖

```python
import click
from a2a_mcp.mcp import server
```

- **`click`**: Python 命令行工具库，用于创建 CLI 接口
- **`server`**: MCP 服务器的实际实现模块

### 2. 命令行选项定义

#### 2.1 `--run` / `command` 选项
```python
@click.option('--run', 'command', default='mcp-server', help='Command to run')
```

**功能**: 指定要运行的命令类型
- **参数名**: `command`（在代码中使用）
- **CLI 标志**: `--run`
- **默认值**: `'mcp-server'`
- **说明**: 目前只支持 `mcp-server`，但设计上支持扩展其他服务器类型

**使用示例**:
```bash
uv run a2a-mcp --run mcp-server
# 或简写（使用默认值）
uv run a2a-mcp
```

#### 2.2 `--host` 选项
```python
@click.option(
    '--host',
    'host',
    default='localhost',
    help='Host on which the server is started or the client connects to',
)
```

**功能**: 指定服务器绑定的主机地址
- **默认值**: `'localhost'`
- **说明**: 
  - `localhost`: 仅本地访问
  - `0.0.0.0`: 允许所有网络接口访问
  - 特定 IP: 绑定到指定 IP 地址

**使用示例**:
```bash
# 本地访问（默认）
uv run a2a-mcp --host localhost

# 允许外部访问
uv run a2a-mcp --host 0.0.0.0

# 绑定到特定 IP
uv run a2a-mcp --host 192.168.1.100
```

#### 2.3 `--port` 选项
```python
@click.option(
    '--port',
    'port',
    default=10100,
    help='Port on which the server is started or the client connects to',
)
```

**功能**: 指定服务器监听的端口号
- **默认值**: `10100`
- **说明**: 
  - 这是 MCP Server 的默认端口
  - 其他 Agent 使用 10101-10105 端口
  - 确保端口未被占用

**使用示例**:
```bash
# 使用默认端口
uv run a2a-mcp --port 10100

# 使用自定义端口
uv run a2a-mcp --port 10200
```

#### 2.4 `--transport` 选项
```python
@click.option(
    '--transport',
    'transport',
    default='stdio',
    help='MCP Transport',
)
```

**功能**: 指定 MCP 传输协议
- **默认值**: `'stdio'`（标准输入输出）
- **可选值**:
  - `'stdio'`: 标准输入输出，用于进程间通信
  - `'sse'`: Server-Sent Events，用于 HTTP 通信
- **说明**: 根据使用场景选择不同的传输方式

**使用示例**:
```bash
# 使用 stdio（默认）
uv run a2a-mcp --transport stdio

# 使用 SSE（用于 Web 集成）
uv run a2a-mcp --transport sse
```

### 3. 主函数实现

```python
def main(command, host, port, transport) -> None:
    # TODO: Add other servers, perhaps dynamic port allocation
    if command == 'mcp-server':
        server.serve(host, port, transport)
    else:
        raise ValueError(f'Unknown run option: {command}')
```

#### 功能分析

1. **命令路由**
   - 根据 `command` 参数决定启动哪个服务器
   - 目前只支持 `mcp-server`
   - 其他命令会抛出 `ValueError`

2. **服务器启动**
   - 调用 `server.serve(host, port, transport)` 启动 MCP 服务器
   - 传递所有配置参数

3. **扩展性设计**
   - `TODO` 注释表明未来可能支持：
     - 其他类型的服务器
     - 动态端口分配（避免端口冲突）

#### 错误处理

```python
raise ValueError(f'Unknown run option: {command}')
```

- 当传入未知的 `command` 时，抛出清晰的错误信息
- 帮助用户快速定位问题

## 代码设计模式

### 1. 命令模式 (Command Pattern)
- 使用 Click 装饰器定义命令和选项
- 将命令行参数映射到函数参数

### 2. 工厂模式 (Factory Pattern)
- `main` 函数根据 `command` 参数创建不同的服务器实例
- 为未来扩展预留接口

### 3. 依赖注入
- 通过函数参数传递配置，而非硬编码
- 提高代码的可测试性和灵活性

## 使用场景

### 场景 1: 开发环境
```bash
# 使用默认配置启动
uv run a2a-mcp --run mcp-server
```

### 场景 2: 生产环境
```bash
# 绑定到所有网络接口，使用自定义端口
uv run a2a-mcp --host 0.0.0.0 --port 10100 --transport sse
```

### 场景 3: 多实例运行
```bash
# 实例 1
uv run a2a-mcp --port 10100

# 实例 2（不同端口）
uv run a2a-mcp --port 10200
```

## 代码改进建议

### 1. 添加输入确认（已注释）
```python
# input("按回车键开始启动服务器...")
```
**建议**: 
- 开发环境可以保留，便于调试
- 生产环境应移除或通过 `--no-confirm` 选项控制

### 2. 添加日志输出
```python
import logging

logger = logging.getLogger(__name__)

def main(command, host, port, transport) -> None:
    logger.info(f"Starting {command} on {host}:{port} with transport {transport}")
    # ...
```

### 3. 添加配置验证
```python
def validate_port(port):
    if not (1024 <= port <= 65535):
        raise click.BadParameter(f"Port must be between 1024 and 65535, got {port}")

@click.option('--port', 'port', default=10100, callback=validate_port)
```

### 4. 支持环境变量
```python
@click.option(
    '--port',
    'port',
    default=lambda: int(os.getenv('MCP_PORT', '10100')),
    help='Port number'
)
```

### 5. 添加健康检查
```python
def main(command, host, port, transport) -> None:
    if command == 'mcp-server':
        try:
            server.serve(host, port, transport)
        except OSError as e:
            if e.errno == 98:  # Address already in use
                logger.error(f"Port {port} is already in use")
                sys.exit(1)
            raise
```

## 完整改进版本示例

```python
"""Convenience methods to start servers."""

import logging
import os
import sys

import click

from a2a_mcp.mcp import server

logger = logging.getLogger(__name__)


def validate_port(ctx, param, value):
    """Validate port number."""
    if not (1024 <= value <= 65535):
        raise click.BadParameter(f"Port must be between 1024 and 65535, got {value}")
    return value


@click.command()
@click.option(
    '--run',
    'command',
    default=lambda: os.getenv('A2A_MCP_COMMAND', 'mcp-server'),
    help='Command to run',
)
@click.option(
    '--host',
    'host',
    default=lambda: os.getenv('A2A_MCP_HOST', 'localhost'),
    help='Host on which the server is started',
)
@click.option(
    '--port',
    'port',
    default=lambda: int(os.getenv('A2A_MCP_PORT', '10100')),
    callback=validate_port,
    help='Port on which the server is started',
)
@click.option(
    '--transport',
    'transport',
    default=lambda: os.getenv('A2A_MCP_TRANSPORT', 'stdio'),
    type=click.Choice(['stdio', 'sse'], case_sensitive=False),
    help='MCP Transport protocol',
)
@click.option(
    '--confirm',
    'confirm',
    is_flag=True,
    default=False,
    help='Require confirmation before starting',
)
def main(command, host, port, transport, confirm) -> None:
    """Start A2A MCP servers."""
    logger.info(f"Starting {command} on {host}:{port} with transport {transport}")
    
    if confirm:
        click.echo(f"About to start {command} on {host}:{port}")
        if not click.confirm("Continue?"):
            click.echo("Aborted.")
            sys.exit(0)
    
    try:
        if command == 'mcp-server':
            server.serve(host, port, transport)
        else:
            raise ValueError(f'Unknown run option: {command}')
    except OSError as e:
        if e.errno == 98:  # Address already in use
            logger.error(f"Port {port} is already in use. Please choose another port.")
            sys.exit(1)
        raise
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
```

## 总结

### 优点
1. ✅ **简洁明了**: 代码结构清晰，易于理解
2. ✅ **灵活配置**: 支持命令行参数自定义
3. ✅ **可扩展**: 预留了扩展其他服务器的接口
4. ✅ **标准化**: 使用 Click 框架，符合 Python CLI 最佳实践

### 可改进点
1. ⚠️ **错误处理**: 可以添加更详细的错误处理和日志
2. ⚠️ **参数验证**: 可以添加端口范围、传输类型等验证
3. ⚠️ **环境变量支持**: 可以支持从环境变量读取配置
4. ⚠️ **健康检查**: 可以添加启动前的端口检查

### 在项目中的作用
- **入口点**: 作为 `a2a-mcp` 命令的入口
- **配置管理**: 统一管理服务器启动配置
- **服务路由**: 根据命令类型启动不同的服务
