# 本地数据库重构设计文档

## 🎯 重构目标

将本地数据库表结构改为与远程数据库 `research_results` 表结构几乎相同，只多一个 `pushed` 字段，消除复杂的字段映射转换。

## 📊 新的本地表结构：`research_results_local`

### 表结构定义

```sql
CREATE TABLE research_results_local (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 外键字段（从API获取）
    company_id INTEGER NOT NULL,           -- 公司ID
    artifact_id INTEGER NOT NULL,         -- 工件ID
    created_by INTEGER NOT NULL,          -- 创建者ID
    
    -- 基础信息字段
    name VARCHAR(255) NOT NULL,           -- 文献标题
    url VARCHAR(500) NOT NULL,            -- 文献URL
    reference_type VARCHAR(100) NOT NULL DEFAULT 'uncategorized',  -- 英文类型
    publisher VARCHAR(255),               -- 发布商（可空）
    
    -- 内容字段
    raw_content TEXT,                     -- 原始完整内容
    
    -- 评估字段
    credibility INTEGER DEFAULT 2,       -- 可信度(1-3)
    related_assessment INTEGER DEFAULT 80, -- 相关性评估(0-100)
    status INTEGER DEFAULT 1,            -- 状态(1-3)
    
    -- 统计字段
    word_count INTEGER DEFAULT 0,        -- 字数统计
    reading_time INTEGER DEFAULT 0,      -- 阅读时间(分钟)
    file_size INTEGER DEFAULT 0,         -- 文件大小(字节)
    file_path VARCHAR(500) DEFAULT 'root', -- 文件路径
    
    -- 时间字段
    collection_time TIMESTAMP NOT NULL,  -- 收集时间
    created_at TIMESTAMP NOT NULL,       -- 创建时间
    updated_at TIMESTAMP NOT NULL,       -- 更新时间
    deleted_at TIMESTAMP,                -- 删除时间（可空）
    
    -- 同步状态字段（新增）
    pushed INTEGER DEFAULT 0,            -- 是否已推送到远程(0=未推送, 1=已推送)
    
    -- 约束
    UNIQUE(url)
);
```

### 索引创建

```sql
-- 基础查询索引
CREATE INDEX idx_url ON research_results_local(url);
CREATE INDEX idx_name ON research_results_local(name);
CREATE INDEX idx_company_artifact ON research_results_local(company_id, artifact_id);
CREATE INDEX idx_created_by ON research_results_local(created_by);

-- 类型和状态索引
CREATE INDEX idx_reference_type ON research_results_local(reference_type);
CREATE INDEX idx_credibility ON research_results_local(credibility);
CREATE INDEX idx_status ON research_results_local(status);

-- 时间索引
CREATE INDEX idx_collection_time ON research_results_local(collection_time);
CREATE INDEX idx_created_at ON research_results_local(created_at);

-- 同步状态索引（重要）
CREATE INDEX idx_pushed ON research_results_local(pushed);
CREATE INDEX idx_unpushed ON research_results_local(pushed, created_at) WHERE pushed = 0;
```

## 🔄 字段映射关系

### 与远程表的对应关系

| 本地字段 | 远程字段 | 数据类型转换 | 说明 |
|---------|---------|------------|------|
| `id` | `id` | INTEGER → BIGINT | 主键，直接映射 |
| `company_id` | `company_id` | INTEGER → BIGINT | 从API获取 |
| `artifact_id` | `artifact_id` | INTEGER → BIGINT | 从API获取 |
| `created_by` | `created_by` | INTEGER → BIGINT | 从API获取 |
| `name` | `name` | VARCHAR(255) → VARCHAR(255) | 直接映射 |
| `url` | `url` | VARCHAR(500) → VARCHAR(500) | 直接映射 |
| `reference_type` | `reference_type` | VARCHAR(100) → VARCHAR(100) | 直接映射，使用英文枚举 |
| `publisher` | `publisher` | VARCHAR(255) → VARCHAR(255) | 直接映射 |
| `raw_content` | `raw_content` | TEXT → TEXT | 直接映射 |
| `credibility` | `credibility` | INTEGER → SMALLINT | 直接映射 |
| `related_assessment` | `related_assessment` | INTEGER → INTEGER | 直接映射 |
| `status` | `status` | INTEGER → SMALLINT | 直接映射 |
| `word_count` | `word_count` | INTEGER → INTEGER | 直接映射 |
| `reading_time` | `reading_time` | INTEGER → INTEGER | 直接映射 |
| `file_size` | `file_size` | INTEGER → BIGINT | 直接映射 |
| `file_path` | `file_path` | VARCHAR(500) → VARCHAR(500) | 直接映射 |
| `collection_time` | `collection_time` | TIMESTAMP → TIMESTAMP | 直接映射 |
| `created_at` | `created_at` | TIMESTAMP → TIMESTAMP | 直接映射 |
| `updated_at` | `updated_at` | TIMESTAMP → TIMESTAMP | 直接映射 |
| `deleted_at` | `deleted_at` | TIMESTAMP → TIMESTAMP | 直接映射 |
| `pushed` | - | INTEGER | **新增字段**，标记同步状态 |

### 数据类型约束

#### reference_type 枚举值
- `uncategorized` - 未分类
- `official_statistics` - 官方统计数据
- `business_data` - 商业数据
- `real-time_data` - 实时数据
- `academic_research` - 学术研究

#### 数值字段约束
- `credibility`: 1-3 (1=低, 2=中, 3=高)
- `related_assessment`: 0-100 (百分比)
- `status`: 1-3 (1=质量不符, 2=未采用, 3=已采用)
- `pushed`: 0-1 (0=未推送, 1=已推送)

## 🚀 数据流程简化

### 插入数据流程
```python
# 新的简化插入流程
def insert_research_data(data):
    record = {
        "company_id": data["company"]["company_id"],
        "artifact_id": data["artifact_id"], 
        "created_by": data["user_id"],
        "name": data["title"][:255],
        "url": data["url"][:500],
        "reference_type": "business_data",  # 直接使用英文枚举
        "publisher": data.get("publisher"),
        "raw_content": data["content"],
        "credibility": 2,
        "related_assessment": 80,
        "status": 1,
        "word_count": len(data["content"]),
        "reading_time": calculate_reading_time(data["content"]),
        "file_size": len(data["content"].encode('utf-8')),
        "file_path": "root",
        "collection_time": datetime.now(),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "pushed": 0  # 新插入的数据默认未推送
    }
    # 直接插入，无需复杂转换
    insert_to_local_db(record)
```

### 同步数据流程
```python
# 新的简化同步流程
def sync_to_remote():
    # 查询未推送的数据
    unpushed_records = query_unpushed_records()
    
    for record in unpushed_records:
        # 移除本地特有字段
        remote_record = record.copy()
        del remote_record["pushed"]
        
        # 直接插入远程数据库，无需字段映射
        success = insert_to_remote_db(remote_record)
        
        if success:
            # 更新本地推送状态
            update_pushed_status(record["id"], 1)
```

## 🔧 重构代码变更

### 1. DatabaseManager 类更新
- 更新 `create_tables()` 方法
- 更新所有插入/查询方法的字段名
- 添加同步状态管理方法

### 2. API 接口更新
- 修改数据插入逻辑，直接使用新表结构
- 更新字段映射，使用英文枚举值

### 3. 数据同步模块简化
- 移除复杂的字段映射逻辑
- 简化 DataMapper 类，只需处理 `pushed` 字段

## ✅ 优势分析

### 1. 简化数据流
- **消除复杂映射**: 本地和远程字段名称完全一致
- **减少转换错误**: 直接映射，无需数据格式转换
- **提高性能**: 减少数据处理步骤

### 2. 易于维护
- **统一数据结构**: 本地和远程结构几乎相同
- **清晰的同步逻辑**: 只需关注 `pushed` 字段状态
- **简化调试**: 数据格式一致，问题排查更容易

### 3. 扩展性好
- **新字段添加**: 只需同时在本地和远程添加
- **约束保持一致**: 数据约束和验证逻辑相同
- **向后兼容**: 保留所有原有功能

## 📝 迁移计划

### 阶段1: 表结构重构
1. 创建新的表结构定义
2. 更新 DatabaseManager 类
3. 创建数据迁移脚本

### 阶段2: 代码重构
1. 更新数据插入逻辑
2. 简化同步模块
3. 更新 API 接口

### 阶段3: 测试验证
1. 单元测试
2. 集成测试
3. 数据同步测试

### 阶段4: 生产部署
1. 数据备份
2. 表结构迁移
3. 代码部署
4. 验证功能

这个设计将大大简化您的数据处理流程，提高系统的可维护性和性能。
