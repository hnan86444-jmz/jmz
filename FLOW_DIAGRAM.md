# 项目流程图

## 完整系统流程图

### 主流程图

```mermaid
flowchart TD
    Start([用户发起请求<br/>例如: 我想去法国旅行]) --> Init[Orchestrator Agent<br/>初始化工作流]
    
    Init --> CheckGraph{工作流图<br/>是否存在?}
    
    CheckGraph -->|否| CreatePlanner[创建 Planner 节点]
    CheckGraph -->|是| CheckPaused{工作流是否<br/>处于暂停状态?}
    
    CheckPaused -->|是| Resume[从暂停节点恢复]
    CheckPaused -->|否| Continue[继续执行]
    
    CreatePlanner --> FindPlanner[通过 MCP 查找<br/>Planner Agent Card]
    FindPlanner --> ConnectPlanner[通过 A2A 连接<br/>Planner Agent]
    ConnectPlanner --> SendPlan[发送用户查询<br/>给 Planner]
    
    SendPlan --> PlannerProcess[Planner Agent 处理]
    PlannerProcess --> ExtractInfo[提取旅行信息<br/>预算/日期/目的地等]
    ExtractInfo --> GenerateTasks[生成任务列表]
    GenerateTasks --> ReturnPlan[返回任务列表和<br/>旅行信息]
    
    ReturnPlan --> BuildGraph[构建工作流图<br/>为每个任务创建节点]
    BuildGraph --> ProcessTasks[开始处理任务]
    
    Resume --> ProcessTasks
    Continue --> ProcessTasks
    
    ProcessTasks --> GetNextTask[获取下一个任务节点]
    GetNextTask --> CheckComplete{所有任务<br/>是否完成?}
    
    CheckComplete -->|是| Aggregate[聚合所有结果]
    CheckComplete -->|否| FindAgent[通过 MCP find_agent<br/>查找匹配的 Task Agent]
    
    FindAgent --> GetAgentCard[获取 Agent Card]
    GetAgentCard --> ConnectTask[通过 A2A 连接<br/>Task Agent]
    ConnectTask --> ExecuteTask[执行任务]
    
    ExecuteTask --> TaskProcess[Task Agent 处理]
    TaskProcess --> UseTool{需要调用<br/>MCP 工具?}
    
    UseTool -->|是| CallTool[调用 MCP 工具<br/>query_travel_data]
    CallTool --> QueryDB[(查询 SQLite 数据库)]
    QueryDB --> ReturnData[返回数据]
    ReturnData --> TaskProcess
    
    UseTool -->|否| CheckInput{需要用户<br/>输入?}
    CallTool --> CheckInput
    
    CheckInput -->|是| Pause[暂停工作流<br/>等待用户输入]
    Pause --> UserInput[用户提供输入]
    UserInput --> Resume
    
    CheckInput -->|否| TaskComplete[任务完成]
    TaskComplete --> StoreResult[存储任务结果]
    StoreResult --> GetNextTask
    
    Aggregate --> GenerateSummary[生成最终摘要]
    GenerateSummary --> ReturnResult[返回结果给用户]
    ReturnResult --> End([结束])
    
    style Start fill:#e1f5ff
    style End fill:#e1f5ff
    style Init fill:#fff4e1
    style PlannerProcess fill:#e8f5e9
    style TaskProcess fill:#e8f5e9
    style Pause fill:#ffebee
    style Aggregate fill:#f3e5f5
```

## 详细子流程

### 1. Planner Agent 处理流程

```mermaid
flowchart LR
    Start([接收用户查询]) --> Parse[解析查询内容]
    Parse --> Extract[提取关键信息]
    
    Extract --> CheckBudget{预算信息<br/>是否完整?}
    CheckBudget -->|否| AskBudget[询问预算]
    AskBudget --> WaitBudget[等待用户输入]
    WaitBudget --> CheckBudget
    
    CheckBudget -->|是| CheckDate{日期信息<br/>是否完整?}
    CheckDate -->|否| AskDate[询问日期]
    AskDate --> WaitDate[等待用户输入]
    WaitDate --> CheckDate
    
    CheckDate -->|是| CheckDest{目的地信息<br/>是否完整?}
    CheckDest -->|否| AskDest[询问目的地]
    AskDest --> WaitDest[等待用户输入]
    WaitDest --> CheckDest
    
    CheckDest -->|是| Generate[生成任务列表]
    Generate --> Task1[任务1: 预订机票]
    Generate --> Task2[任务2: 预订酒店]
    Generate --> Task3[任务3: 预订租车]
    
    Task1 --> Format[格式化输出]
    Task2 --> Format
    Task3 --> Format
    
    Format --> Return([返回 TaskList])
    
    style Start fill:#e1f5ff
    style Return fill:#e1f5ff
    style AskBudget fill:#ffebee
    style AskDate fill:#ffebee
    style AskDest fill:#ffebee
```

### 2. Task Agent 执行流程

```mermaid
flowchart TD
    Start([接收任务请求]) --> Parse[解析任务描述]
    Parse --> ConnectMCP[连接到 MCP Server]
    ConnectMCP --> GetTools[获取可用工具列表]
    
    GetTools --> Analyze[分析任务需求]
    Analyze --> NeedDB{需要查询<br/>数据库?}
    
    NeedDB -->|是| BuildSQL[构建 SQL 查询]
    BuildSQL --> CallTool[调用 query_travel_data]
    CallTool --> ExecuteSQL[(执行 SQL)]
    ExecuteSQL --> GetResults[获取查询结果]
    
    NeedDB -->|否| NeedPlaces{需要查询<br/>地点信息?}
    GetResults --> ProcessData[处理数据]
    
    NeedPlaces -->|是| CallPlaces[调用 query_places_data]
    CallPlaces --> PlacesAPI[调用 Google Places API]
    PlacesAPI --> GetPlaces[获取地点信息]
    GetPlaces --> ProcessData
    
    NeedPlaces -->|否| CheckInfo{信息是否<br/>足够?}
    ProcessData --> CheckInfo
    
    CheckInfo -->|否| AskUser[请求用户输入]
    AskUser --> WaitInput[等待用户响应]
    WaitInput --> ProcessData
    
    CheckInfo -->|是| FormatResult[格式化结果]
    FormatResult --> Return([返回任务结果])
    
    style Start fill:#e1f5ff
    style Return fill:#e1f5ff
    style AskUser fill:#ffebee
    style ExecuteSQL fill:#e8f5e9
    style PlacesAPI fill:#e8f5e9
```

### 3. MCP Server Agent 发现流程

```mermaid
flowchart TD
    Start([接收 find_agent 请求]) --> GetQuery[获取查询文本]
    GetQuery --> GenerateEmbed[生成查询嵌入向量<br/>使用 embedding-001]
    
    GenerateEmbed --> LoadCards[加载所有 Agent Cards]
    LoadCards --> GetEmbeddings[获取预计算的<br/>Agent Card 嵌入]
    
    GetEmbeddings --> Calculate[计算相似度<br/>点积运算]
    Calculate --> Compare[比较所有相似度分数]
    Compare --> FindMax[找到最高分]
    FindMax --> GetCard[获取匹配的 Agent Card]
    GetCard --> Return([返回 Agent Card])
    
    style Start fill:#e1f5ff
    style Return fill:#e1f5ff
    style GenerateEmbed fill:#fff4e1
    style Calculate fill:#e8f5e9
```

### 4. 工作流状态转换流程

```mermaid
stateDiagram-v2
    [*] --> INITIALIZED: 创建 WorkflowGraph
    
    INITIALIZED --> READY: 添加第一个节点
    
    READY --> RUNNING: 开始执行工作流
    
    RUNNING --> PROCESSING: 处理当前节点
    
    PROCESSING --> CHECKING: 检查节点状态
    
    CHECKING --> COMPLETED: 节点完成
    CHECKING --> PAUSED: 需要用户输入
    CHECKING --> ERROR: 发生错误
    
    COMPLETED --> NEXT_NODE: 移动到下一个节点
    NEXT_NODE --> RUNNING: 继续执行
    NEXT_NODE --> COMPLETED_ALL: 所有节点完成
    
    PAUSED --> WAITING: 等待用户输入
    WAITING --> RESUME: 收到用户输入
    RESUME --> RUNNING: 恢复执行
    
    ERROR --> RETRY: 重试
    RETRY --> RUNNING: 重新执行
    ERROR --> FAILED: 失败
    
    COMPLETED_ALL --> AGGREGATING: 聚合结果
    AGGREGATING --> SUMMARY: 生成摘要
    SUMMARY --> [*]: 完成
    
    FAILED --> [*]: 终止
```

### 5. 数据流详细图

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant O as Orchestrator
    participant P as Planner
    participant M as MCP Server
    participant T as Task Agent
    participant D as Database
    
    U->>O: 1. 发送查询请求
    Note over O: 初始化工作流图
    
    O->>M: 2. 查找 Planner Agent Card
    M-->>O: 3. 返回 Agent Card
    
    O->>P: 4. 通过 A2A 发送查询
    Note over P: 解析查询，提取信息
    
    alt 信息不完整
        P-->>O: 5a. 请求用户输入
        O-->>U: 5b. 转发问题
        U->>O: 5c. 提供输入
        O->>P: 5d. 发送补充信息
    end
    
    P->>P: 6. 生成任务列表
    P-->>O: 7. 返回 TaskList
    
    Note over O: 为每个任务创建节点
    
    loop 每个任务
        O->>M: 8. find_agent(任务描述)
        M->>M: 9. 计算嵌入相似度
        M-->>O: 10. 返回匹配的 Agent Card
        
        O->>T: 11. 通过 A2A 执行任务
        Note over T: 分析任务需求
        
        T->>M: 12. 获取工具列表
        M-->>T: 13. 返回工具列表
        
        T->>M: 14. 调用 query_travel_data(SQL)
        M->>D: 15. 执行 SQL 查询
        D-->>M: 16. 返回数据
        M-->>T: 17. 返回查询结果
        
        T->>T: 18. 处理数据，格式化结果
        T-->>O: 19. 返回任务结果
        
        Note over O: 存储结果到 results 数组
    end
    
    Note over O: 所有任务完成
    
    O->>O: 20. 聚合所有结果
    O->>O: 21. 生成最终摘要
    O-->>U: 22. 返回完整结果
    
    Note over U: 显示旅行规划结果
```

### 6. 错误处理和重试流程

```mermaid
flowchart TD
    Start([执行操作]) --> Execute[执行]
    Execute --> Check{执行成功?}
    
    Check -->|是| Success([成功])
    
    Check -->|否| CheckType{错误类型?}
    
    CheckType -->|网络错误| RetryNet[重试网络请求]
    CheckType -->|数据错误| ValidateData[验证数据]
    CheckType -->|Agent错误| CheckAgent[检查 Agent 状态]
    CheckType -->|工具错误| CheckTool[检查工具可用性]
    
    RetryNet --> CountRetry{重试次数<br/>< 3?}
    CountRetry -->|是| Wait[等待 2 秒]
    Wait --> Execute
    CountRetry -->|否| LogError[记录错误]
    
    ValidateData --> FixData[修复数据]
    FixData --> Execute
    
    CheckAgent --> Reconnect[重新连接 Agent]
    Reconnect --> Execute
    
    CheckTool --> CheckMCP{MCP Server<br/>可用?}
    CheckMCP -->|是| RetryTool[重试工具调用]
    CheckMCP -->|否| Alert[告警: MCP 不可用]
    RetryTool --> Execute
    
    LogError --> Fail([失败])
    Alert --> Fail
    
    style Success fill:#e8f5e9
    style Fail fill:#ffebee
    style RetryNet fill:#fff4e1
    style Alert fill:#ffebee
```

### 7. 并发执行流程（未来优化）

```mermaid
flowchart TD
    Start([接收任务列表]) --> Analyze[分析任务依赖]
    Analyze --> BuildDAG[构建依赖图 DAG]
    
    BuildDAG --> Identify{识别可并行<br/>执行的任务}
    
    Identify -->|有独立任务| Parallel[并行执行组]
    Identify -->|无独立任务| Sequential[顺序执行]
    
    Parallel --> Group1[任务组1<br/>并行执行]
    Parallel --> Group2[任务组2<br/>并行执行]
    Parallel --> Group3[任务组3<br/>并行执行]
    
    Group1 --> Task1A[任务1A]
    Group1 --> Task1B[任务1B]
    
    Group2 --> Task2A[任务2A]
    Group2 --> Task2B[任务2B]
    Group2 --> Task2C[任务2C]
    
    Task1A --> Wait1[等待组1完成]
    Task1B --> Wait1
    Task2A --> Wait2[等待组2完成]
    Task2B --> Wait2
    Task2C --> Wait2
    
    Wait1 --> CheckDep{检查依赖}
    Wait2 --> CheckDep
    
    CheckDep -->|有依赖| Sequential
    CheckDep -->|无依赖| Continue[继续执行]
    
    Sequential --> NextTask[执行下一个任务]
    NextTask --> CheckMore{还有任务?}
    CheckMore -->|是| NextTask
    CheckMore -->|否| Aggregate[聚合结果]
    
    Continue --> Aggregate
    Aggregate --> Done([完成])
    
    style Start fill:#e1f5ff
    style Done fill:#e1f5ff
    style Parallel fill:#e8f5e9
    style Sequential fill:#fff4e1
```

## 关键决策点

### 决策树：任务执行策略

```mermaid
flowchart TD
    Start([收到任务]) --> CheckType{任务类型?}
    
    CheckType -->|机票预订| AirFlow[Air Ticketing Agent]
    CheckType -->|酒店预订| HotelFlow[Hotel Booking Agent]
    CheckType -->|租车预订| CarFlow[Car Rental Agent]
    CheckType -->|其他| DefaultFlow[默认处理]
    
    AirFlow --> CheckInfo{信息完整?}
    HotelFlow --> CheckInfo
    CarFlow --> CheckInfo
    DefaultFlow --> CheckInfo
    
    CheckInfo -->|是| Execute[执行任务]
    CheckInfo -->|否| AskUser[询问用户]
    
    AskUser --> Wait[等待响应]
    Wait --> Validate{响应有效?}
    
    Validate -->|是| Execute
    Validate -->|否| Retry[重试询问]
    Retry --> AskUser
    
    Execute --> CheckResult{执行成功?}
    CheckResult -->|是| Return[返回结果]
    CheckResult -->|否| HandleError[处理错误]
    
    HandleError --> CheckRetry{可重试?}
    CheckRetry -->|是| RetryExec[重试执行]
    CheckRetry -->|否| ReturnError[返回错误]
    
    RetryExec --> Execute
    Return --> End([结束])
    ReturnError --> End
    
    style Start fill:#e1f5ff
    style End fill:#e1f5ff
    style AskUser fill:#ffebee
    style HandleError fill:#ffebee
```

## 时序图：完整交互流程

```mermaid
sequenceDiagram
    participant User
    participant Orchestrator
    participant Planner
    participant MCP
    participant AirAgent
    participant HotelAgent
    participant CarAgent
    participant Database
    
    User->>Orchestrator: 1. 查询: "我想去法国旅行，预算5000美元"
    
    Orchestrator->>MCP: 2. find_agent("规划旅行")
    MCP-->>Orchestrator: 3. Planner Agent Card
    
    Orchestrator->>Planner: 4. A2A: 执行规划任务
    Planner->>Planner: 5. 分析查询，提取信息
    Planner-->>Orchestrator: 6. TaskList + TripInfo
    
    Note over Orchestrator: 创建任务节点: 机票、酒店、租车
    
    Orchestrator->>MCP: 7. find_agent("预订机票")
    MCP-->>Orchestrator: 8. Air Ticketing Agent Card
    
    Orchestrator->>AirAgent: 9. A2A: 执行机票预订
    AirAgent->>MCP: 10. 获取工具
    MCP-->>AirAgent: 11. 工具列表
    AirAgent->>MCP: 12. query_travel_data("SELECT * FROM flights...")
    MCP->>Database: 13. SQL 查询
    Database-->>MCP: 14. 航班数据
    MCP-->>AirAgent: 15. 查询结果
    AirAgent->>AirAgent: 16. 处理并格式化
    AirAgent-->>Orchestrator: 17. 机票预订结果
    
    Orchestrator->>MCP: 18. find_agent("预订酒店")
    MCP-->>Orchestrator: 19. Hotel Booking Agent Card
    
    Orchestrator->>HotelAgent: 20. A2A: 执行酒店预订
    HotelAgent->>MCP: 21. query_travel_data("SELECT * FROM hotels...")
    MCP->>Database: 22. SQL 查询
    Database-->>MCP: 23. 酒店数据
    MCP-->>HotelAgent: 24. 查询结果
    HotelAgent-->>Orchestrator: 25. 酒店预订结果
    
    Orchestrator->>MCP: 26. find_agent("预订租车")
    MCP-->>Orchestrator: 27. Car Rental Agent Card
    
    Orchestrator->>CarAgent: 28. A2A: 执行租车预订
    CarAgent->>MCP: 29. query_travel_data("SELECT * FROM cars...")
    MCP->>Database: 30. SQL 查询
    Database-->>MCP: 31. 租车数据
    MCP-->>CarAgent: 32. 查询结果
    CarAgent-->>Orchestrator: 33. 租车预订结果
    
    Note over Orchestrator: 所有任务完成
    
    Orchestrator->>Orchestrator: 34. 聚合结果
    Orchestrator->>Orchestrator: 35. 生成摘要
    Orchestrator-->>User: 36. 返回完整旅行规划
```

## 流程图说明

### 主要流程阶段

1. **初始化阶段**
   - Orchestrator 接收用户请求
   - 创建工作流图
   - 查找 Planner Agent

2. **规划阶段**
   - Planner 解析用户查询
   - 提取旅行信息
   - 生成任务列表

3. **执行阶段**
   - 为每个任务查找匹配的 Agent
   - 通过 A2A 协议执行任务
   - Task Agent 使用 MCP 工具查询数据

4. **聚合阶段**
   - 收集所有任务结果
   - 生成最终摘要
   - 返回给用户

### 关键特性

- **动态发现**: 通过 MCP 动态查找 Agent，无需硬编码
- **状态管理**: 工作流支持暂停、恢复、重试
- **错误处理**: 完善的错误处理和重试机制
- **用户交互**: 支持在流程中请求用户输入
- **可扩展性**: 易于添加新的 Agent 和工具
