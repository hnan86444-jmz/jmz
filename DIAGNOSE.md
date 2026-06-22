# 诊断指南：PyCharm 无法运行问题

## 已更新的代码

我已经修改了 `src/a2a_mcp/__init__.py`，添加了：
- ✅ 详细的日志输出
- ✅ 自动加载 .env 文件
- ✅ 环境变量检查
- ✅ 完整的错误信息

## 诊断步骤

### 步骤 1: 运行并查看完整输出

1. **在 PyCharm 中运行配置**
2. **查看控制台的完整输出**

现在应该能看到详细的日志，包括：
- 启动信息
- 环境变量检查结果
- 任何错误信息

### 步骤 2: 检查控制台输出

运行后，请告诉我控制台显示了什么。应该会看到类似：

```
2025-01-26 ... - Starting A2A MCP Server
==========================================================
Command: mcp-server
Host: localhost
Port: 10100
Transport: sse
Working directory: C:\Users\...
==========================================================
Looking for .env file at: C:\Users\...\.env
Found .env file, loading environment variables...
Loaded X environment variables from .env file
✓ OPENAI_API_KEY is set (length: XX characters)
Initializing MCP server...
Calling server.serve() - this should block and keep running...
```

### 步骤 3: 常见问题检查

#### 问题 A: 看到 "OPENAI_API_KEY is not set"

**解决方案**:
1. 确保项目根目录有 `.env` 文件
2. `.env` 文件内容：
   ```
   OPENAI_API_KEY=你的实际API密钥
   ```
3. 或者：在 PyCharm 运行配置中添加环境变量

#### 问题 B: 看到 "Server exited unexpectedly"

**可能原因**:
- `server.serve()` 函数内部出错
- Transport 配置问题
- 端口被占用

**解决方案**:
1. 检查端口是否被占用：
   ```bash
   netstat -ano | findstr :10100
   ```
2. 尝试使用不同的端口
3. 确保使用 `sse` transport

#### 问题 C: 没有任何输出

**可能原因**:
- 日志配置问题
- 程序在导入阶段就失败了

**解决方案**:
1. 检查 Python 解释器是否正确
2. 检查依赖是否安装：`uv sync`
3. 尝试在 Terminal 中直接运行

### 步骤 4: 在 Terminal 中测试

在 PyCharm 的 Terminal 中运行：

```bash
# 进入项目目录
cd C:\Users\24514\Desktop\mcp-server-demo\a2a_mcp

# 直接运行 Python
python src/a2a_mcp/__init__.py --run mcp-server --host localhost --port 10100 --transport sse
```

对比 Terminal 和 PyCharm 的输出差异。

## 需要的信息

请提供以下信息，以便进一步诊断：

1. **控制台的完整输出**（从开始到结束的所有内容）
2. **PyCharm 运行配置的截图或详细配置**：
   - Script path
   - Parameters
   - Working directory
   - Environment variables
   - Python interpreter
3. **项目根目录是否有 .env 文件**
4. **.env 文件的内容**（隐藏 API 密钥，只显示格式）

## 快速测试脚本

创建一个测试文件 `test_run.py` 在项目根目录：

```python
import os
import sys
from pathlib import Path

print("=" * 70)
print("诊断信息")
print("=" * 70)
print(f"Python 版本: {sys.version}")
print(f"当前工作目录: {os.getcwd()}")
print(f"Python 路径: {sys.executable}")

# 检查 .env 文件
env_path = Path('.env')
print(f"\n.env 文件路径: {env_path.absolute()}")
print(f".env 文件存在: {env_path.exists()}")

if env_path.exists():
    print("\n.env 文件内容（隐藏敏感信息）:")
    with open(env_path) as f:
        for line in f:
            if '=' in line:
                key = line.split('=')[0].strip()
                print(f"  {key}=***")

# 检查环境变量
print(f"\nOPENAI_API_KEY 环境变量:")
api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    print(f"  ✓ 已设置 (长度: {len(api_key)})")
else:
    print("  ✗ 未设置")

# 尝试导入模块
print("\n尝试导入模块:")
try:
    from a2a_mcp.mcp import server
    print("  ✓ 导入成功")
except Exception as e:
    print(f"  ✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()

print("=" * 70)
```

在 PyCharm 中运行这个测试脚本，查看输出。

## 临时解决方案

如果仍然无法在 PyCharm 中运行，可以：

### 方案 1: 使用 PyCharm Terminal

直接在 PyCharm 的 Terminal 中运行命令，这样和外部终端一样。

### 方案 2: 使用外部终端

在 Windows PowerShell 或 CMD 中运行。

### 方案 3: 创建批处理文件

创建 `run_mcp_server.bat`:

```batch
@echo off
cd /d "%~dp0"
uv run --env-file .env a2a-mcp --run mcp-server --transport sse --port 10100
pause
```

双击运行。

## 下一步

请运行更新后的代码，并告诉我：
1. 控制台显示了什么？
2. 有没有看到 "OPENAI_API_KEY is set" 的消息？
3. 有没有任何错误信息？

有了这些信息，我可以更准确地帮你解决问题。
