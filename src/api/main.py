from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import sqlite3
import json
import uuid
import asyncio
from datetime import datetime
import os
import sys
import httpx
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api_server.log')
    ]
)
logger = logging.getLogger(__name__)

# Add project paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import data migration modules
try:
    from data_migration.migration_service import MigrationService
    from data_migration.data_mapper import DataMapper
    from data_migration.remote_writer import RemoteWriter
    MIGRATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"数据迁移模块导入失败: {e}")
    MIGRATION_AVAILABLE = False

app = FastAPI(
    title="MultiAgent Deep Research API",
    description="多智能体深度研究系统 API - 支持完整研究流程和 Perplexity 报告生成",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with full request body"""
    start_time = time.time()
    
    # Log request info
    logger.info(f"=== Incoming Request ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    # For POST/PUT requests, log the body
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
        if body:
            try:
                # Try to parse as JSON for pretty printing
                json_body = json.loads(body)
                logger.info(f"Request Body (JSON):\n{json.dumps(json_body, indent=2, ensure_ascii=False)}")
                
                # Save request JSON for masterflow and report tasks
                if request.url.path == "/api/research/task" and request.method == "POST":
                    task_type = json_body.get("task_type", "").lower()
                    if task_type in ["masterflow", "report"]:
                        # Save to backend/src/request.json
                        request_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "request.json")
                        os.makedirs(os.path.dirname(request_json_path), exist_ok=True)
                        
                        # Add metadata
                        save_data = json_body.copy()
                        save_data["_saved_at"] = datetime.now().isoformat()
                        save_data["_request_path"] = str(request.url.path)
                        save_data["_task_type"] = task_type
                        
                        with open(request_json_path, 'w', encoding='utf-8') as f:
                            json.dump(save_data, f, ensure_ascii=False, indent=2)
                        
                        logger.info(f"Request JSON saved to: {request_json_path}")
                        
            except:
                # If not JSON, log as string
                logger.info(f"Request Body (Raw): {body.decode('utf-8', errors='ignore')}")
        else:
            logger.info("Request Body: Empty")
        
        # Recreate request with body for downstream processing
        from starlette.datastructures import Headers
        from starlette.requests import Request as StarletteRequest
        
        async def receive():
            return {"type": "http.request", "body": body}
        
        request = StarletteRequest(request.scope, receive)
    
    # Process request
    response = await call_next(request)
    
    # Log response info
    process_time = time.time() - start_time
    logger.info(f"=== Response ===")
    logger.info(f"Status Code: {response.status_code}")
    logger.info(f"Process Time: {process_time:.3f}s")
    logger.info("="*50)
    
    return response

# ========== 枚举类型 ==========
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"

class TaskType(str, Enum):
    MASTER_FLOW = "master_flow"
    PERPLEXITY_REPORT = "perplexity_report"

class RequestTaskType(str, Enum):
    MASTERFLOW = "masterflow"
    REPORT = "report"

class ArtifactsType(str, Enum):
    T1 = "T1"
    T2 = "T2" 
    T3 = "T3"
    T4 = "T4"
    A1 = "A1"
    A2 = "A2"
    A3 = "A3"
    A4 = "A4"
    A5 = "A5"
    A6 = "A6"
    A7 = "A7"
    A8 = "A8"
    A9 = "A9"
    GGP = "GGP"
    SNT = "SNT"
    MES = "MES"
    PSE = "PSE"
    DCS_DCC = "DCS/DCC"
    DIP = "DIP"
    CIS = "CIS"
    RMA = "RMA"

# ========== 数据迁移相关模型 ==========
class DataMigrationRequest(BaseModel):
    artifact_id: int = Field(..., gt=0, description="工件ID，用于数据迁移的外键")
    company_id: int = Field(3, gt=0, description="公司ID，默认为3")
    created_by: int = Field(3, gt=0, description="创建者ID，默认为3")
    source_db_path: Optional[str] = Field("research_data.db", description="源数据库路径，默认为research_data.db")
    limit: Optional[int] = Field(None, gt=0, description="限制迁移的记录数")
    dry_run: bool = Field(False, description="是否为试运行模式（不实际写入数据）")
    
    class Config:
        schema_extra = {
            "example": {
                "artifact_id": 3,
                "company_id": 3,
                "created_by": 3,
                "source_db_path": "research_data.db",
                "limit": 100,
                "dry_run": False
            }
        }

class DataMigrationResponse(BaseModel):
    success: bool
    task_id: str
    message: str
    artifact_id: int
    estimated_duration: str
    status_url: str

class MigrationStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    current_step: Optional[str] = None
    artifact_id: int
    migration_type: Optional[str] = None
    source_records: Optional[int] = None
    transformed_records: Optional[int] = None
    valid_records: Optional[int] = None
    invalid_records: Optional[int] = None
    insert_result: Optional[Dict] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None

# ========== 新增的 Pydantic 模型 ==========
class CompanyInfo(BaseModel):
    company_id: str = Field(..., min_length=1, description="公司唯一标识符")
    company_data: Optional[str] = Field(None, description="公司相关数据信息")

class UserIntlPref(BaseModel):
    label: str = Field(..., description="偏好标签")
    options: List[str] = Field(..., description="偏好选项列表")

class TaskConfig(BaseModel):
    user_intl_prefs: List[UserIntlPref] = Field(..., description="用户国际化偏好配置")

class ProductInfo(BaseModel):
    tech_specs: Optional[Dict[str, Any]] = Field(None, description="技术规格信息")
    product_sku: Optional[Dict[str, Any]] = Field(None, description="产品SKU信息")

class NewAPIRequest(BaseModel):
    user_id: int = Field(..., gt=0, description="用户ID")
    artifact_id: int = Field(..., gt=0, description="工件ID")
    artifacts_type: ArtifactsType = Field(..., description="工件类型")
    artifact_task_id: str = Field(..., min_length=1, description="工件任务ID")
    task_type: RequestTaskType = Field(..., description="任务类型（masterflow/report）")
    company: CompanyInfo = Field(..., description="公司信息")
    task_config: TaskConfig = Field(..., description="任务配置信息")
    product: ProductInfo = Field(..., description="产品信息")
    callback_url: Optional[str] = Field(None, description="任务完成回调URL")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": 101,
                "artifact_id": 1,
                "artifacts_type": "A1",
                "artifact_task_id": "123",
                "task_type": "report",
                "company": {
                    "company_id": "hurrain_awg_2024",
                    "company_data": "HurRain公司专注于空气制水（AWG）技术，主打产品A16型号空气制水机"
                },
                "task_config": {
                    "user_intl_prefs": [
                        {
                            "label": "目标市场偏好",
                            "options": ["发达国家市场（美国、欧盟、日本等）"]
                        }
                    ]
                },
                "product": {
                    "tech_specs": {
                        "safety_standards": [
                            {
                                "title": "99.99% contaminant removal efficiency"
                            }
                        ],
                        "certification_info": [
                            {
                                "title": "ISO certification (shown in logo on brochure)"
                            }
                        ]
                    },
                    "product_sku": {
                        "products": [
                            {
                                "title": "A5T Industrial-Grade Large-Capacity Advanced Material Air-to-Water Generator",
                                "attributes": [
                                    {
                                        "key": "Dimensions",
                                        "value": "5153mm X 2200mm X 2300mm (Including air outlet)"
                                    }
                                ]
                            }
                        ]
                    }
                },
                "callback_url": "https://webhook.site/your-unique-url"
            }
        }

class TaskResponse(BaseModel):
    success: bool
    user_id: int
    artifact_id: int
    artifacts_type: str
    artifact_task_id: str
    task_id: Optional[str] = None
    message: str
    estimated_duration: Optional[str] = None
    status_url: Optional[str] = None

class TaskStatusResponse(BaseModel):
    task_id: str
    task_type: str
    status: str
    progress: int
    current_step: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_files: Optional[List[str]] = None
    error_message: Optional[str] = None
    artifact_id: Optional[int] = None
    artifact_task_id: Optional[str] = None
    user_id: Optional[str] = None
    artifacts_id: Optional[str] = None

# ========== 原有模型 ==========
class ResearchRequest(BaseModel):
    artifactsID: str
    userID: str

class ResearchResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data_id: Optional[int] = None

# Database paths
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "research_data.db")
TASKS_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tasks.db")

# ========== 任务管理器 ==========
class TaskManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_task_table()
    
    def init_task_table(self):
        """初始化任务表和研究数据表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建research_tasks表 - 现在在单独的tasks.db中
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS research_tasks (
                task_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                artifacts_id TEXT NOT NULL,
                user_data_id TEXT NOT NULL,
                artifact_id INTEGER NOT NULL,
                artifact_task_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                current_step TEXT,
                request_data JSON,
                result_data JSON,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        # 创建research_data表 - 也移到tasks.db中
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS research_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artifacts_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                data JSON,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON research_tasks(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_artifacts_id ON research_tasks(artifacts_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON research_tasks(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_research_data_user_id ON research_data(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_research_data_artifacts_id ON research_data(artifacts_id)')
        
        conn.commit()
        conn.close()
    
    def create_task(self, user_id: str, artifacts_id: str, user_data_id: str,
                   artifact_id: int, artifact_task_id: str,
                   task_type: TaskType, request_data: Dict[Any, Any]) -> str:
        """创建新任务"""
        # 打印回调参数（如果有）
        callback_url = request_data.get('callback_url') if isinstance(request_data, dict) else None
        if callback_url:
            logger.info(f"[TaskManager] 回调参数 callback_url: {callback_url}")
        else:
            logger.info(f"[TaskManager] 未检测到回调参数 callback_url")

        task_id = f"{task_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO research_tasks 
            (task_id, user_id, artifacts_id, user_data_id, artifact_id, artifact_task_id, task_type, request_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (task_id, user_id, artifacts_id, user_data_id, artifact_id, artifact_task_id, task_type.value, json.dumps(request_data)))

        conn.commit()
        conn.close()

        return task_id
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          progress: int = None, current_step: str = None,
                          result_data: Dict = None, error_message: str = None):
        """更新任务状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        update_fields = ["status = ?"]
        params = [status.value]
        
        if progress is not None:
            update_fields.append("progress = ?")
            params.append(progress)
        
        if current_step is not None:
            update_fields.append("current_step = ?")
            params.append(current_step)
            
        if result_data is not None:
            update_fields.append("result_data = ?")
            params.append(json.dumps(result_data))
            
        if error_message is not None:
            update_fields.append("error_message = ?")
            params.append(error_message)
        
        if status == TaskStatus.RUNNING:
            update_fields.append("started_at = ?")
            params.append(datetime.now().isoformat())
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            update_fields.append("completed_at = ?") 
            params.append(datetime.now().isoformat())
        
        params.append(task_id)
        
        cursor.execute(f'''
            UPDATE research_tasks 
            SET {', '.join(update_fields)}
            WHERE task_id = ?
        ''', params)
        
        conn.commit()
        conn.close()
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT task_id, task_type, status, progress, current_step, 
                   created_at, started_at, completed_at, result_data, error_message,
                   artifact_id, artifact_task_id, user_id, artifacts_id
            FROM research_tasks WHERE task_id = ?
        ''', (task_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        return {
            "task_id": row[0],
            "task_type": row[1], 
            "status": row[2],
            "progress": row[3] or 0,
            "current_step": row[4],
            "created_at": row[5],
            "started_at": row[6],
            "completed_at": row[7],
            "result_data": json.loads(row[8]) if row[8] else None,
            "error_message": row[9],
            "artifact_id": row[10],
            "artifact_task_id": row[11],
            "user_id": row[12],
            "artifacts_id": row[13]
        }

# 初始化任务管理器 - 使用单独的tasks.db文件
task_manager = TaskManager(TASKS_DB_PATH)

# ========== 回调通知函数 ==========
async def send_callback_notification(callback_url: str, artifact_task_id: str, artifact_id: int, status: str, result_data: Dict = None, error_message: str = None):
    """发送任务完成回调通知
    
    成功回调包含: artifact_task_id, artifact_id, status, timestamp, result
    失败回调包含: artifact_task_id, artifact_id, status, timestamp, error
    """
    if not callback_url:
        return

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 构建回调 payload
            payload = {
                "artifact_task_id": artifact_task_id,
                "artifact_id": str(artifact_id),  # 转换为字符串以保持一致性
                "status": status,
                "timestamp": datetime.now().isoformat(),
            }

            # 成功时添加 result，失败时添加 error
            if status == "completed" and result_data:
                payload["result"] = result_data
            elif status == "failed" and error_message:
                payload["error"] = error_message

            # 打印回调请求内容
            logger.info("=" * 60)
            logger.info(f"[Callback] 发送回调通知到: {callback_url}")
            logger.info(f"[Callback] 请求Headers: Content-Type: application/json")
            logger.info(f"[Callback] 请求Body:")
            logger.info(json.dumps(payload, ensure_ascii=False, indent=2))

            # 发送 POST 请求
            response = await client.post(
                callback_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # 记录响应状态
            logger.info(f"[Callback] 响应状态码: {response.status_code}")
            
            # 尝试解析响应体
            try:
                response_json = response.json()
                logger.info(f"[Callback] 响应Body:")
                logger.info(json.dumps(response_json, ensure_ascii=False, indent=2))
                
                # 检查响应格式是否符合预期
                if response.status_code == 200:
                    if response_json.get("success") == True:
                        logger.info(f"[Callback] ✅ 回调成功: {response_json.get('message', '回调接收成功')}")
                        if "received_at" in response_json:
                            logger.info(f"[Callback] 接收时间: {response_json['received_at']}")
                    else:
                        logger.warning(f"[Callback] ⚠️ 回调接收但处理失败: {response_json.get('message', '未知错误')}")
                elif response.status_code == 422:
                    logger.error(f"[Callback] ❌ 验证错误 (422): {response_json}")
                elif response.status_code >= 400:
                    logger.error(f"[Callback] ❌ 回调失败 ({response.status_code}): {response_json.get('message', '未知错误')}")
                    
            except Exception as json_error:
                # 响应体不是有效的 JSON
                logger.warning(f"[Callback] 响应体非JSON格式: {response.text[:500]}")
                if response.status_code == 200:
                    logger.info(f"[Callback] ✅ 回调成功 (状态码200，但响应非JSON)")
                else:
                    logger.error(f"[Callback] ❌ 回调失败 (状态码{response.status_code})")
            
            logger.info("=" * 60)

    except httpx.TimeoutException:
        logger.error(f"[Callback] ❌ 回调超时 (30秒): {callback_url}")
    except httpx.ConnectError:
        logger.error(f"[Callback] ❌ 无法连接到回调URL: {callback_url}")
    except Exception as e:
        logger.error(f"[Callback] ❌ 发送回调通知出错: {callback_url} - 错误: {str(e)}")

# ========== 后台任务处理函数 ==========
async def run_master_flow_task(task_id: str, request_data: Dict):
    """执行 Master Flow 后台任务"""
    try:
        task_manager.update_task_status(
            task_id, TaskStatus.RUNNING, 
            progress=0, current_step="初始化研究流程..."
        )
        
        # 导入并执行 master_flow
        from master_flow.master_flow import master_flow_run
        
        task_manager.update_task_status(
            task_id, TaskStatus.RUNNING,
            progress=10, current_step="开始交互式规划..."
        )
        
        # 执行完整的 master_flow
        artifact_id = request_data.get("artifact_id", 1)
        user_id = request_data.get("user_id", 3)
        
        # 处理company_id，从company对象中获取
        company_info = request_data.get("company", {})
        logger.info(f"[Master Flow] 原始company对象: {company_info}")
        
        if isinstance(company_info, dict):
            company_id_raw = company_info.get("company_id", "3")
            logger.info(f"[Master Flow] 从company.company_id获取: {company_id_raw}")
        else:
            company_id_raw = "3"
            logger.warning(f"[Master Flow] company不是字典格式，使用默认值: {company_id_raw}")
        
        # 将company_id转换为整数
        try:
            company_id = int(company_id_raw)
            logger.info(f"[Master Flow] company_id转换成功: {company_id_raw} -> {company_id}")
        except (ValueError, TypeError) as e:
            company_id = 3
            logger.error(f"[Master Flow] company_id转换失败: {company_id_raw}, 错误: {e}, 使用默认值: {company_id}")
        
        logger.info(f"[Master Flow] 最终参数: artifact_id={artifact_id}, company_id={company_id}, user_id={user_id}")
        
        # 额外的调试输出（使用print确保能看到）
        print(f"🔍 [API Debug] 调用master_flow_run的参数:")
        print(f"🔍 [API Debug]   artifact_id: {artifact_id}")
        print(f"🔍 [API Debug]   company_id: {company_id}")
        print(f"🔍 [API Debug]   user_id: {user_id}")
        
        result = await master_flow_run(
            artifact_id=artifact_id, 
            company_id=company_id, 
            user_id=user_id
        )
        # await asyncio.sleep(2)  # 模拟执行时间
        
        result_data = {
            "message": "Master Flow 执行完成",
            "result_path": result.get("output_path", "研究完成") if isinstance(result, dict) else "研究完成",
            "research_title": request_data.get("research_title", "")
        }
        
        task_manager.update_task_status(
            task_id, TaskStatus.COMPLETED,
            progress=100, current_step="研究流程完成",
            result_data=result_data
        )
        
        # 发送回调通知
        callback_url = request_data.get("callback_url") or request_data.get("notification_callback")
        if callback_url:
            artifact_task_id = request_data.get("artifact_task_id", task_id)
            artifact_id = request_data.get("artifact_id", 0)
            await send_callback_notification(
                callback_url, artifact_task_id, artifact_id, "completed", result_data
            )
        
    except Exception as e:
        error_msg = f"Master Flow 执行失败: {str(e)}"
        task_manager.update_task_status(
            task_id, TaskStatus.FAILED,
            error_message=error_msg
        )
        logger.error(f"Master Flow 任务 {task_id} 失败: {str(e)}")
        
        # 发送失败回调通知
        callback_url = request_data.get("callback_url") or request_data.get("notification_callback")
        if callback_url:
            artifact_task_id = request_data.get("artifact_task_id", task_id)
            artifact_id = request_data.get("artifact_id", 0)
            await send_callback_notification(
                callback_url, artifact_task_id, artifact_id, "failed", None, error_msg
            )

async def run_perplexity_report_task(task_id: str, request_data: Dict):
    """执行 Perplexity 报告后台任务"""
    try:
        logger.info(f"Starting Perplexity report task: {task_id}")
        logger.info(f"Request data: {json.dumps(request_data, indent=2, ensure_ascii=False)}")
        
        task_manager.update_task_status(
            task_id, TaskStatus.RUNNING,
            progress=0, current_step="初始化 Perplexity 报告生成..."
        )
        
        # 导入并执行 perplexity 报告生成
        from topic_report_perplexity.report_perplexity_sonar import TopicReportPerplexityGenerator
        
        generator = TopicReportPerplexityGenerator()
        
        task_manager.update_task_status(
            task_id, TaskStatus.RUNNING,
            progress=30, current_step="正在生成 Perplexity 报告..."
        )
        
        # 使用异步方法执行报告生成
        result_path = await generator.generate_report(
            topic_id=request_data["topic_id"],
            use_stream=request_data.get("use_stream", True)
        )
        # await asyncio.sleep(2)  # 模拟执行时间
        # result_path = "模拟报告路径"
        
        logger.info(f"Perplexity report generated successfully for {request_data['topic_id']}")
        logger.info(f"Report path: {result_path}")
        
        result_data = {
            "message": "Perplexity 报告生成完成",
            "report_path": result_path,
            "topic_id": request_data["topic_id"]
        }
        
        task_manager.update_task_status(
            task_id, TaskStatus.COMPLETED,
            progress=100, current_step="Perplexity 报告生成完成",
            result_data=result_data
        )
        
        logger.info(f"Task {task_id} completed successfully")
        
        # 发送回调通知
        callback_url = request_data.get("callback_url")
        if callback_url:
            artifact_task_id = request_data.get("artifact_task_id", task_id)
            artifact_id = request_data.get("artifact_id", 0)
            await send_callback_notification(
                callback_url, artifact_task_id, artifact_id, "completed", result_data
            )
        
    except Exception as e:
        error_msg = f"Perplexity 报告生成失败: {str(e)}"
        task_manager.update_task_status(
            task_id, TaskStatus.FAILED,
            error_message=error_msg
        )
        logger.error(f"Perplexity 任务 {task_id} 失败: {str(e)}")
        
        # 发送失败回调通知
        callback_url = request_data.get("callback_url")
        if callback_url:
            artifact_task_id = request_data.get("artifact_task_id", task_id)
            artifact_id = request_data.get("artifact_id", 0)
            await send_callback_notification(
                callback_url, artifact_task_id, artifact_id, "failed", None, error_msg
            )

def init_database():
    """Initialize database with required tables if they don't exist"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create research_results_local table (new unified structure)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS "research_results_local" (
            -- 主键
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- 外键字段（从API获取）
            company_id INTEGER NOT NULL,
            artifact_id INTEGER NOT NULL,
            created_by INTEGER NOT NULL,
            
            -- 基础信息字段
            name VARCHAR(255) NOT NULL,
            url VARCHAR(500) NOT NULL,
            reference_type VARCHAR(100) NOT NULL DEFAULT 'uncategorized',
            publisher VARCHAR(255),
            
            -- 内容字段
            raw_content TEXT,
            
            -- 评估字段
            credibility INTEGER DEFAULT 2,
            related_assessment INTEGER DEFAULT 80,
            status INTEGER DEFAULT 1,
            
            -- 统计字段
            word_count INTEGER DEFAULT 0,
            reading_time INTEGER DEFAULT 0,
            file_size INTEGER DEFAULT 0,
            file_path VARCHAR(500) DEFAULT 'root',
            
            -- 时间字段
            collection_time TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            deleted_at TIMESTAMP,
            
            -- 同步状态字段（新增）
            pushed INTEGER DEFAULT 0,
            
            -- 约束
            UNIQUE(url)
        )
    ''')
    
    # Create indexes for better performance
    indexes = [
        'CREATE INDEX IF NOT EXISTS idx_url ON "research_results_local"(url);',
        'CREATE INDEX IF NOT EXISTS idx_name ON "research_results_local"(name);',
        'CREATE INDEX IF NOT EXISTS idx_company_artifact ON "research_results_local"(company_id, artifact_id);',
        'CREATE INDEX IF NOT EXISTS idx_created_by ON "research_results_local"(created_by);',
        'CREATE INDEX IF NOT EXISTS idx_reference_type ON "research_results_local"(reference_type);',
        'CREATE INDEX IF NOT EXISTS idx_credibility ON "research_results_local"(credibility);',
        'CREATE INDEX IF NOT EXISTS idx_status ON "research_results_local"(status);',
        'CREATE INDEX IF NOT EXISTS idx_collection_time ON "research_results_local"(collection_time);',
        'CREATE INDEX IF NOT EXISTS idx_created_at ON "research_results_local"(created_at);',
        'CREATE INDEX IF NOT EXISTS idx_pushed ON "research_results_local"(pushed);',
        'CREATE INDEX IF NOT EXISTS idx_unpushed ON "research_results_local"(pushed, created_at);'
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)
    
    # research_data表已移动到tasks.db中，不再在research_data.db中创建
    
    conn.commit()
    conn.close()

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_database()
    logger.info(f"数据库初始化完成: {DB_PATH}")
    logger.info("FastAPI 服务启动完成 - 运行在端口 8088")
    logger.info("访问 http://192.168.12.155:8088/docs 查看 API 文档")
    logger.info("日志将输出到控制台和 api_server.log 文件")

# ========== 新增的 API 接口 ==========

@app.post("/api/research/task", 
         response_model=TaskResponse,
         summary="研究任务处理",
         description="根据task_type执行Master Flow研究流程或Perplexity报告生成")
async def process_research_task(request: NewAPIRequest, background_tasks: BackgroundTasks):
    """统一的研究任务处理接口"""
    try:
        # Log the incoming request
        logger.info("="*60)
        logger.info("Processing research task request")
        logger.info(f"Request data: {request.model_dump_json(indent=2)}")
        
        # 将新格式转换为内部使用的格式
        internal_request = {
            "user_id": str(request.user_id),
            "artifact_id": request.artifact_id,
            "artifacts_id": f"{request.artifacts_type.value}_{request.company.company_id}",
            "artifact_task_id": request.artifact_task_id,
            "user_data_id": f"data_{request.user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "company_info": {
                "company_id": request.company.company_id,
                "company_data": request.company.company_data,
            },
            "task_config": {
                "user_intl_prefs": [pref.model_dump() for pref in request.task_config.user_intl_prefs]
            },
            "product": {
                "tech_specs": request.product.tech_specs,
                "product_sku": request.product.product_sku
            },
            "artifacts_type": request.artifacts_type.value,
            "callback_url": request.callback_url,
            "task_type": request.task_type.value
        }
        
        # 根据task_type决定任务类型和处理逻辑
        if request.task_type == RequestTaskType.MASTERFLOW:
            task_type = TaskType.MASTER_FLOW
            estimated_duration = "15-30分钟"
            message = "Master Flow 研究流程已启动，请稍后查询任务状态"
        elif request.task_type == RequestTaskType.REPORT:
            task_type = TaskType.PERPLEXITY_REPORT
            estimated_duration = "3-5分钟"
            message = "Perplexity 报告生成已启动"
            # 添加 topic_id 用于 Perplexity 报告
            internal_request["topic_id"] = f"topic_{request.artifacts_type.value}"
            internal_request["use_stream"] = True
        else:
            raise ValueError(f"不支持的任务类型: {request.task_type}")
        
        # 创建任务
        task_id = task_manager.create_task(
            user_id=str(request.user_id),
            artifacts_id=internal_request["artifacts_id"],
            user_data_id=internal_request["user_data_id"],
            artifact_id=request.artifact_id,
            artifact_task_id=request.artifact_task_id,
            task_type=task_type,
            request_data=internal_request
        )
        
        logger.info(f"Task created successfully: {task_id}")
        logger.info(f"Task type: {task_type.value}")
        logger.info(f"User ID: {request.user_id}")
        logger.info(f"Artifact: {request.artifacts_type.value}")
        
        # 启动相应的后台任务
        if request.task_type == RequestTaskType.MASTERFLOW:
            background_tasks.add_task(
                run_master_flow_task,
                task_id,
                internal_request
            )
        elif request.task_type == RequestTaskType.REPORT:
            background_tasks.add_task(
                run_perplexity_report_task,
                task_id,
                internal_request
            )
        
        return TaskResponse(
            success=True,
            user_id=request.user_id,
            artifact_id=request.artifact_id,
            artifacts_type=request.artifacts_type.value,
            artifact_task_id=request.artifact_task_id,
            task_id=task_id,
            message=message,
            estimated_duration=estimated_duration,
            status_url=f"/api/research/status/{task_id}"
        )
        
    except Exception as e:
        # 在错误情况下，也需要提供必需的字段
        return TaskResponse(
            success=False,
            user_id=request.user_id,
            artifact_id=request.artifact_id,
            artifacts_type=request.artifacts_type.value,
            artifact_task_id=request.artifact_task_id,
            task_id=None,
            message=f"处理失败: {str(e)}",
            estimated_duration=None,
            status_url=None
        )


@app.get("/api/research/status/{task_id}", 
        response_model=TaskStatusResponse,
        summary="查询任务状态",
        description="根据任务ID查询任务执行状态和进度")
async def get_task_status(task_id: str):
    """获取任务状态"""
    task_info = task_manager.get_task_status(task_id)
    
    if not task_info:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 构建结果文件列表
    result_files = []
    if task_info.get("result_data"):
        result_data = task_info["result_data"]
        if "report_path" in result_data:
            result_files.append(result_data["report_path"])
        if "result_path" in result_data:
            result_files.append(result_data["result_path"])
    
    return TaskStatusResponse(
        task_id=task_info["task_id"],
        task_type=task_info["task_type"],
        status=task_info["status"],
        progress=task_info["progress"],
        current_step=task_info["current_step"],
        created_at=task_info["created_at"],
        started_at=task_info["started_at"],
        completed_at=task_info["completed_at"],
        result_files=result_files if result_files else None,
        error_message=task_info["error_message"],
        artifact_id=task_info.get("artifact_id"),
        artifact_task_id=task_info.get("artifact_task_id"),
        user_id=task_info.get("user_id"),
        artifacts_id=task_info.get("artifacts_id")
    )

# ========== 保留原有的 API 接口 ==========

@app.get("/", summary="健康检查")
async def root():
    """Health check endpoint"""
    return {
        "status": "active", 
        "message": "MultiAgent Deep Research API is running",
        "version": "2.0.0",
        "port": 8088,
        "docs_url": "/docs"
    }

@app.post("/api/research/create", response_model=ResearchResponse)
async def create_research_data(request: ResearchRequest):
    """
    Create a new research data entry
    
    Args:
        request: ResearchRequest containing artifactsID and userID
    
    Returns:
        ResearchResponse indicating success or failure
    """
    try:
        conn = sqlite3.connect(TASKS_DB_PATH)  # 使用tasks.db
        cursor = conn.cursor()
        
        # Prepare initial data
        initial_data = {
            "artifacts_id": request.artifactsID,
            "user_id": request.userID,
            "status": "initialized",
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "source": "api"
            }
        }
        
        # Insert into database
        cursor.execute('''
            INSERT INTO research_data (artifacts_id, user_id, data, status)
            VALUES (?, ?, ?, ?)
        ''', (
            request.artifactsID,
            request.userID,
            json.dumps(initial_data),
            "initialized"
        ))
        
        # Get the inserted ID
        data_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return ResearchResponse(
            success=True,
            message=f"Research data created successfully with ID: {data_id}",
            data_id=data_id
        )
        
    except Exception as e:
        # Log the error
        logger.error(f"Error creating research data: {str(e)}")
        
        return ResearchResponse(
            success=False,
            message=f"Failed to create research data: {str(e)}",
            data_id=None
        )

@app.get("/api/research/{data_id}")
async def get_research_data(data_id: int):
    """
    Get research data by ID
    
    Args:
        data_id: The ID of the research data entry
    
    Returns:
        The research data entry or 404 if not found
    """
    try:
        conn = sqlite3.connect(TASKS_DB_PATH)  # 使用tasks.db
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, artifacts_id, user_id, created_at, status, data, updated_at
            FROM research_data
            WHERE id = ?
        ''', (data_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "artifacts_id": row[1],
                "user_id": row[2],
                "created_at": row[3],
                "status": row[4],
                "data": json.loads(row[5]) if row[5] else None,
                "updated_at": row[6]
            }
        else:
            raise HTTPException(status_code=404, detail="Research data not found")
            
    except Exception as e:
        logger.error(f"Error fetching research data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/research/user/{user_id}")
async def get_user_research_data(user_id: str):
    """
    Get all research data for a specific user
    
    Args:
        user_id: The user ID
    
    Returns:
        List of research data entries for the user
    """
    try:
        conn = sqlite3.connect(TASKS_DB_PATH)  # 使用tasks.db
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, artifacts_id, user_id, created_at, status, data
            FROM research_data
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "artifacts_id": row[1],
                "user_id": row[2],
                "created_at": row[3],
                "status": row[4],
                "data": json.loads(row[5]) if row[5] else None
            })
        
        return {"user_id": user_id, "count": len(results), "data": results}
        
    except Exception as e:
        logger.error(f"Error fetching user research data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== JSON持久化接口 ==========

@app.post("/api/persist-json")
async def persist_json_data(request: Request):
    """
    将请求的JSON数据持久化到 backend/src/api.json 文件
    每次请求都会覆盖文件内容
    """
    try:
        # 获取请求的JSON数据
        json_data = await request.json()
        
        # 添加时间戳信息
        json_data["_persistence_info"] = {
            "timestamp": datetime.now().isoformat(),
            "request_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 确定文件路径 (backend/src/api.json)
        current_dir = os.path.dirname(os.path.abspath(__file__))  # backend/src/api/
        parent_dir = os.path.dirname(current_dir)  # backend/src/
        file_path = os.path.join(parent_dir, "api.json")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 写入JSON文件（覆盖模式）
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON数据已持久化到: {file_path}")
        
        return {
            "success": True,
            "message": "JSON数据持久化成功",
            "file_path": file_path,
            "data_size": len(json.dumps(json_data)),
            "timestamp": datetime.now().isoformat()
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {str(e)}")
        raise HTTPException(status_code=400, detail=f"无效的JSON格式: {str(e)}")
    except Exception as e:
        logger.error(f"JSON持久化失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"持久化失败: {str(e)}")

@app.get("/api/get-persisted-json")
async def get_persisted_json():
    """
    获取持久化的JSON数据
    """
    try:
        # 确定文件路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        file_path = os.path.join(parent_dir, "api.json")
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="持久化文件不存在")
        
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # 添加文件信息
        file_stat = os.stat(file_path)
        file_info = {
            "file_path": file_path,
            "file_size": file_stat.st_size,
            "last_modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
        }
        
        return {
            "success": True,
            "data": json_data,
            "file_info": file_info
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON读取错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"JSON文件格式错误: {str(e)}")
    except Exception as e:
        logger.error(f"获取持久化数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"读取失败: {str(e)}")

# ========== 新增的数据库测试接口 ==========

@app.post("/api/test/create-research-record")
async def create_research_record(
    company_id: int,
    artifact_id: int, 
    created_by: int,
    name: str,
    url: str,
    reference_type: str = "uncategorized",
    publisher: str = None,
    raw_content: str = None
):
    """创建研究结果记录（测试新表结构）"""
    try:
        from src.search_agent.tools.database import DatabaseManager
        
        db_manager = DatabaseManager(DB_PATH)
        
        # 准备数据
        current_time = datetime.now().isoformat()
        research_data = {
            "company_id": company_id,
            "artifact_id": artifact_id,
            "created_by": created_by,
            "name": name[:255],
            "url": url[:500],
            "reference_type": reference_type,
            "publisher": publisher[:255] if publisher else None,
            "raw_content": raw_content,
            "credibility": 2,
            "related_assessment": 80,
            "status": 1,
            "word_count": len(raw_content) if raw_content else 0,
            "reading_time": max(1, len(raw_content or "") // 200),
            "file_size": len((raw_content or "").encode('utf-8')),
            "file_path": "root",
            "collection_time": current_time,
            "created_at": current_time,
            "updated_at": current_time,
            "deleted_at": None,
            "pushed": 0
        }
        
        # 插入数据
        success = db_manager.insert_research_result(research_data)
        
        if success:
            return {
                "success": True,
                "message": "研究记录创建成功",
                "data": research_data
            }
        else:
            raise HTTPException(status_code=500, detail="数据插入失败")
            
    except Exception as e:
        logger.error(f"创建研究记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")

@app.get("/api/test/research-records")
async def get_research_records(limit: int = 10):
    """获取研究记录列表（测试新表结构）"""
    try:
        from src.search_agent.tools.database import DatabaseManager
        
        db_manager = DatabaseManager(DB_PATH)
        results = db_manager.get_all_research_results(limit=limit)
        
        return {
            "success": True,
            "message": f"获取到 {len(results)} 条记录",
            "data": results,
            "total": len(results)
        }
    except Exception as e:
        logger.error(f"获取研究记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

@app.get("/api/test/unpushed-records")
async def get_unpushed_records(limit: int = 10):
    """获取未推送的记录（测试同步状态）"""
    try:
        from src.search_agent.tools.database import DatabaseManager
        
        db_manager = DatabaseManager(DB_PATH)
        records = db_manager.get_unpushed_records(limit=limit)
        
        return {
            "success": True,
            "message": f"获取到 {len(records)} 条未推送记录", 
            "data": records,
            "total": len(records)
        }
    except Exception as e:
        logger.error(f"获取未推送记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")

@app.get("/api/test/sync-stats")
async def get_sync_statistics():
    """获取同步统计信息"""
    try:
        from src.search_agent.tools.database import DatabaseManager
        
        db_manager = DatabaseManager(DB_PATH)
        stats = db_manager.get_sync_statistics()
        
        return {
            "success": True,
            "message": "获取同步统计成功",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取同步统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")

@app.put("/api/test/mark-pushed/{record_id}")
async def mark_record_pushed(record_id: int):
    """标记记录为已推送"""
    try:
        from src.search_agent.tools.database import DatabaseManager
        
        db_manager = DatabaseManager(DB_PATH)
        success = db_manager.update_pushed_status(record_id, 1)
        
        if success:
            return {
                "success": True,
                "message": f"记录 {record_id} 已标记为已推送"
            }
        else:
            raise HTTPException(status_code=404, detail="记录不存在或更新失败")
    except Exception as e:
        logger.error(f"标记推送状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@app.get("/api/test/database-info") 
async def get_database_info():
    """获取数据库信息"""
    try:
        from src.search_agent.tools.database import DatabaseManager
        
        db_manager = DatabaseManager(DB_PATH)
        
        # 获取记录统计
        total_count = db_manager.get_record_count(include_deleted=True)
        active_count = db_manager.get_record_count(include_deleted=False)
        
        # 获取同步统计
        sync_stats = db_manager.get_sync_statistics()
        
        return {
            "success": True,
            "message": "数据库信息获取成功",
            "data": {
                "database_path": DB_PATH,
                "table_name": "research_results_local",
                "record_counts": {
                    "total": total_count,
                    "active": active_count,
                    "deleted": total_count - active_count
                },
                "sync_statistics": sync_stats
            }
        }
    except Exception as e:
        logger.error(f"获取数据库信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取信息失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("=" * 60)
    logger.info("🚀 MultiAgent Deep Research API 启动中...")
    logger.info("📋 可用接口:")
    logger.info("   - Master Flow: POST /api/research/master-flow")
    logger.info("   - Perplexity Report: POST /api/research/perplexity-report")
    logger.info("   - 任务状态: GET /api/research/status/{task_id}")
    logger.info("   - 数据库测试: GET /api/test/*")
    logger.info("📖 API 文档: http://192.168.12.155:8088/docs")
    logger.info("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8088, reload=False)