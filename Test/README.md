# Planning Agent 测试文档

这个目录包含了规划代理（Planning Agent）的完整测试套件。

## 测试文件

- `test_planning_agent.py` - 主要测试文件，包含所有测试用例
- `conftest.py` - pytest 配置文件
- `README.md` - 本文档

## 运行测试

### 方法1: 使用测试运行脚本（推荐）

```bash
# 运行所有测试
python run_planning_agent_tests.py

# 只运行单元测试（快速）
python run_planning_agent_tests.py --quick

# 只运行集成测试
python run_planning_agent_tests.py --integration

# 运行特定测试类
python run_planning_agent_tests.py --class Configuration State

# 运行特定测试方法
python run_planning_agent_tests.py --method test_default_configuration

# 详细输出
python run_planning_agent_tests.py --verbose

# 列出所有可用测试
python run_planning_agent_tests.py --list
```

### 方法2: 直接运行测试文件

```bash
# 运行所有测试
python Test/test_planning_agent.py

# 运行特定测试类
python Test/test_planning_agent.py TestPlanningAgentConfiguration

# 运行特定测试方法
python Test/test_planning_agent.py TestPlanningAgentConfiguration.test_default_configuration
```

## 测试类别

### 单元测试

1. **TestPlanningAgentConfiguration** - 配置管理测试
   - 测试默认配置
   - 测试从运行配置创建配置

2. **TestPlanningAgentState** - 状态管理测试
   - 测试状态初始化
   - 测试状态更新和转换
   - 测试状态验证

3. **TestPlanningAgentSchemas** - 数据模式测试
   - 测试需求评估模型
   - 测试规划输出模型
   - 测试JSON验证和格式化

4. **TestPlanningAgentPrompts** - 提示模板测试
   - 测试对话历史格式化
   - 测试参数注入
   - 测试提示模板存在性

5. **TestPlanningAgentErrorHandling** - 错误处理测试
   - 测试各种错误类型
   - 测试安全执行
   - 测试错误统计

6. **TestPlanningAgentGraph** - 工作流图测试
   - 测试需求评估节点
   - 测试澄清生成节点
   - 测试JSON生成节点
   - 测试流程路由

### 集成测试

7. **TestPlanningAgentIntegration** - 集成测试
   - 测试完整工作流
   - 测试状态持久化
   - 测试错误恢复
   - 测试性能和限制

## 环境要求

### 必需环境变量

- `OPENAI_API_KEY` - OpenAI API密钥（集成测试需要）

### Python依赖

```bash
pip install python-dotenv loguru langchain-openai langgraph pydantic
```

## 测试覆盖范围

测试覆盖了规划代理的以下功能：

- ✅ 配置管理
- ✅ 状态管理和转换
- ✅ 数据模式验证
- ✅ 提示模板处理
- ✅ 错误处理和恢复
- ✅ LangGraph工作流
- ✅ 需求评估
- ✅ 澄清问题生成
- ✅ JSON规划生成
- ✅ 完整工作流集成

## 测试结果示例

```
======================================================================
规划代理测试套件
======================================================================

可用的测试类:
  Configuration  - 配置管理测试
  State         - 状态管理测试
  Schemas       - 数据模式测试
  Prompts       - 提示模板测试
  ErrorHandling - 错误处理测试
  Graph         - 工作流图测试
  Integration   - 集成测试 (需要 OPENAI_API_KEY)

✓ 找到 OPENAI_API_KEY - 集成测试可用

运行 40 个测试...
----------------------------------------------------------------------
........................................

----------------------------------------------------------------------
Ran 40 tests in 28.762s

OK

======================================================================
测试结果摘要:
======================================================================
运行测试: 40
失败: 0
错误: 0
跳过: 0
```

## 故障排除

### 常见问题

1. **ImportError: No module named 'planning_agent'**
   - 确保在 `backend` 目录下运行测试
   - 检查 Python 路径设置

2. **集成测试被跳过**
   - 设置 `OPENAI_API_KEY` 环境变量
   - 确保 API 密钥有效

3. **LLM API 调用失败**
   - 检查网络连接
   - 验证 API 密钥权限
   - 检查 API 配额

### 调试技巧

1. **启用详细日志**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **单独运行失败的测试**
   ```bash
   python run_planning_agent_tests.py --method test_specific_method --verbose
   ```

3. **跳过集成测试进行快速调试**
   ```bash
   python run_planning_agent_tests.py --quick
   ```

## 贡献指南

### 添加新测试

1. 在相应的测试类中添加新的测试方法
2. 使用描述性的方法名和文档字符串
3. 遵循现有的测试模式和断言风格
4. 确保测试是独立的，不依赖其他测试的状态

### 测试命名约定

- 测试方法以 `test_` 开头
- 使用描述性名称，如 `test_evaluate_requirement_sufficient`
- 测试类以 `TestPlanningAgent` 开头，后跟功能模块名

### Mock 使用

对于需要外部依赖的测试，使用 `unittest.mock`:

```python
@patch('planning_agent.planning_gragh.ChatOpenAI')
def test_with_mock_llm(self, mock_openai):
    # 设置 mock
    mock_llm_instance = Mock()
    mock_openai.return_value = mock_llm_instance
    
    # 执行测试
    # ...
```

## 性能基准

- 单元测试应在 1 秒内完成
- 集成测试可能需要 10-30 秒（取决于 LLM API 响应时间）
- 完整测试套件通常在 30-60 秒内完成