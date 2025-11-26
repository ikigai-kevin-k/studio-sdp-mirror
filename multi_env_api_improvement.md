# 多環境 Table API 並行處理改進方案

## 概述

本文檔針對目前 `main_vip.py`、`main_speed.py`、`main_sicbo.py` 中多環境 table 並行打 API 的方式，提出可擴展、低延遲、高度並行化的改進方案。目前架構是五個環境各自要打一個 table，改進後可支援多個環境各自要打多個 table 的擴展需求。

## 目前架構分析

### 現有特點
1. **單一程式處理多環境**：每個 main_*.py 檔案處理 5 個環境（CIT, UAT, PRD, STG, QAT）
2. **同步並行處理**：使用 ThreadPoolExecutor 進行並行 API 呼叫
3. **硬編碼環境數量**：每個環境固定對應一個 table
4. **配置檔案分離**：不同遊戲類型使用不同的配置檔案

### 現有配置結構
```json
// conf/table-config-vip-roulette-v2.json
[
    {
        "name": "CIT",
        "get_url": "https://crystal-table.iki-cit.cc/v2/service/tables/",
        "post_url": "https://crystal-table.iki-cit.cc/v2/service/tables/",
        "game_code": "ARO-002"
    },
    // ... 其他環境
]
```

### 現有問題
- **擴展性限制**：無法動態增加 table 數量
- **資源浪費**：單一程式處理所有環境，資源分配不均
- **故障影響**：單一環境故障可能影響整個系統
- **維護困難**：硬編碼的環境配置難以維護

## 改進方案

### 1. 微服務架構 + 容器化部署

#### 核心概念
將每個環境的 table 處理拆分為獨立的微服務

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer / API Gateway              │
└─────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼────────┐    ┌─────────▼─────────┐    ┌───────▼────────┐
│ Environment A  │    │  Environment B   │    │ Environment C   │
│ Service Pool   │    │  Service Pool     │    │ Service Pool    │
│                │    │                   │    │                 │
│ ┌─────────────┐│    │ ┌───────────────┐│    │ ┌─────────────┐ │
│ │Table 1      ││    │ │Table 1         ││    │ │Table 1      ││
│ │Table 2      ││    │ │Table 2         ││    │ │Table 2      ││
│ │Table 3      ││    │ │Table 3         ││    │ │Table 3      ││
│ │...          ││    │ │...             ││    │ │...          ││
│ └─────────────┘│    │ └───────────────┘│    │ └─────────────┘ │
└────────────────┘    └──────────────────┘    └─────────────────┘
```

#### 優點
- **水平擴展**：可根據需要動態增加 table 數量
- **故障隔離**：單一 table 故障不影響其他 table
- **獨立部署**：每個環境可獨立更新和維護
- **資源隔離**：每個服務有獨立的資源配額

#### 實施範例
```python
# table_service.py
class TableService:
    def __init__(self, environment, table_configs):
        self.environment = environment
        self.table_configs = table_configs
        self.session = aiohttp.ClientSession()
        
    async def process_tables(self, operation, data):
        tasks = []
        for table in self.table_configs:
            task = self.process_single_table(table, operation, data)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def process_single_table(self, table, operation, data):
        try:
            url = f"{table['post_url']}{table['game_code']}"
            async with self.session.post(url, json=data) as response:
                return await response.json()
        except Exception as e:
            logger.error(f"Table {table['game_code']} error: {e}")
            return None
```

### 2. 事件驅動架構 (Event-Driven Architecture)

#### 核心概念
使用訊息佇列進行非同步通訊

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│   Serial    │───▶│   Event Bus   │───▶│  Table      │
│  Controller │    │  (Redis/RMQ)  │    │ Services    │
└─────────────┘    └──────────────┘    └─────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
            ┌───────▼────┐ ┌──────▼──────┐
            │ VIP Tables │ │Speed Tables │
            │   Pool     │ │   Pool      │
            └────────────┘ └─────────────┘
```

#### 優點
- **解耦合**：各組件間鬆散耦合
- **高並行**：事件可並行處理
- **可擴展**：易於添加新的 table 類型
- **容錯性**：訊息持久化確保不丟失

#### 實施範例
```python
# event_handler.py
import redis
import asyncio
import json

class EventHandler:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.pubsub = self.redis_client.pubsub()
        
    async def publish_event(self, event_type, data):
        message = {
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        }
        await self.redis_client.publish('table_events', json.dumps(message))
        
    async def subscribe_events(self, callback):
        await self.pubsub.subscribe('table_events')
        async for message in self.pubsub.listen():
            if message['type'] == 'message':
                event_data = json.loads(message['data'])
                await callback(event_data)
```

### 3. 動態配置管理系統

#### 核心概念
集中式配置管理，支援動態擴展

```python
# 配置結構範例
{
  "environments": {
    "PRD": {
      "tables": [
        {"id": "ARO-001", "type": "speed_roulette", "priority": 1},
        {"id": "ARO-002", "type": "vip_roulette", "priority": 2},
        {"id": "ARO-003", "type": "speed_roulette", "priority": 1}
      ],
      "scaling": {
        "min_instances": 2,
        "max_instances": 10,
        "auto_scale": true
      }
    }
  }
}
```

#### 實施範例
```python
# config_manager.py
class ConfigManager:
    def __init__(self):
        self.config_cache = {}
        self.watchers = []
        
    async def load_config(self, environment):
        # 從資料庫或配置服務載入配置
        config = await self.fetch_config_from_db(environment)
        self.config_cache[environment] = config
        return config
        
    async def watch_config_changes(self, environment, callback):
        # 監聽配置變更
        while True:
            new_config = await self.load_config(environment)
            if new_config != self.config_cache.get(environment):
                await callback(new_config)
                self.config_cache[environment] = new_config
            await asyncio.sleep(10)  # 每10秒檢查一次
```

### 4. 高效能並行處理架構

#### 核心概念
使用 asyncio + aiohttp 實現真正的非同步並行

```python
# table_manager.py
class TableManager:
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.semaphore = asyncio.Semaphore(100)  # 限制並發數
        
    async def process_tables_parallel(self, tables, operation):
        tasks = []
        for table in tables:
            task = self.process_single_table(table, operation)
            tasks.append(task)
        
        # 真正的並行執行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def process_single_table(self, table, operation):
        async with self.semaphore:  # 控制並發數
            try:
                return await operation(table)
            except Exception as e:
                logger.error(f"Table {table['id']} error: {e}")
                return None
                
    async def start_round_all_tables(self, tables, token):
        """並行啟動所有 table 的回合"""
        async def start_single_table(table):
            post_url = f"{table['post_url']}{table['game_code']}"
            async with self.session.post(
                f"{post_url}/start",
                headers={'Authorization': f'Bearer {token}'}
            ) as response:
                result = await response.json()
                return table['name'], result.get('round_id'), result.get('bet_period')
        
        tasks = [start_single_table(table) for table in tables]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 處理結果
        successful_rounds = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to start round for {tables[i]['name']}: {result}")
            elif result and result[1]:  # 有有效的 round_id
                successful_rounds.append(result)
                
        return successful_rounds
```

### 5. 智能負載均衡與故障轉移

#### 核心概念
自動檢測和處理故障

```python
# load_balancer.py
class SmartLoadBalancer:
    def __init__(self):
        self.table_health = {}
        self.circuit_breakers = {}
        self.failover_tables = {}
        
    async def route_request(self, table_id, operation):
        # 檢查健康狀態
        if not self.is_table_healthy(table_id):
            return await self.failover_request(table_id, operation)
        
        # 執行請求
        try:
            return await operation()
        except Exception as e:
            self.mark_table_unhealthy(table_id)
            return await self.failover_request(table_id, operation)
            
    def is_table_healthy(self, table_id):
        health_info = self.table_health.get(table_id, {})
        return health_info.get('status') == 'healthy'
        
    async def failover_request(self, table_id, operation):
        """故障轉移處理"""
        backup_tables = self.failover_tables.get(table_id, [])
        for backup_table in backup_tables:
            try:
                # 嘗試使用備用 table
                return await self.execute_with_backup(backup_table, operation)
            except Exception as e:
                logger.warning(f"Backup table {backup_table} also failed: {e}")
                continue
        
        # 所有備用 table 都失敗
        raise Exception(f"All tables failed for {table_id}")
        
    def mark_table_unhealthy(self, table_id):
        """標記 table 為不健康"""
        self.table_health[table_id] = {
            'status': 'unhealthy',
            'last_failure': time.time()
        }
        
        # 啟動健康檢查定時器
        asyncio.create_task(self.health_check_timer(table_id))
        
    async def health_check_timer(self, table_id):
        """健康檢查定時器"""
        await asyncio.sleep(60)  # 等待 60 秒後重新檢查
        try:
            # 執行健康檢查
            health_status = await self.perform_health_check(table_id)
            if health_status:
                self.table_health[table_id] = {
                    'status': 'healthy',
                    'last_check': time.time()
                }
                logger.info(f"Table {table_id} recovered")
        except Exception as e:
            logger.error(f"Health check failed for {table_id}: {e}")
```

### 6. 容器編排與自動擴展

#### Kubernetes 部署配置

```yaml
# k8s/table-service-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: table-service-prd
spec:
  replicas: 3
  selector:
    matchLabels:
      app: table-service-prd
  template:
    metadata:
      labels:
        app: table-service-prd
    spec:
      containers:
      - name: table-service
        image: table-service:latest
        env:
        - name: ENVIRONMENT
          value: "PRD"
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        ports:
        - containerPort: 8080
---
apiVersion: v2beta2
kind: HorizontalPodAutoscaler
metadata:
  name: table-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: table-service-prd
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### Docker 配置

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY . .

# 設定環境變數
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8080

# 啟動命令
CMD ["python", "main_service.py"]
```

### 7. 監控與可觀測性

#### 核心概念
全面的監控和日誌系統

```python
# metrics_collector.py
from prometheus_client import Counter, Histogram, Gauge
import time

class MetricsCollector:
    def __init__(self):
        self.api_requests_total = Counter(
            'api_requests_total',
            'Total number of API requests',
            ['environment', 'table_id', 'operation', 'status']
        )
        
        self.api_request_duration = Histogram(
            'api_request_duration_seconds',
            'API request duration in seconds',
            ['environment', 'table_id', 'operation']
        )
        
        self.active_connections = Gauge(
            'active_connections',
            'Number of active connections',
            ['environment']
        )
        
    def record_api_request(self, environment, table_id, operation, status, duration):
        """記錄 API 請求指標"""
        self.api_requests_total.labels(
            environment=environment,
            table_id=table_id,
            operation=operation,
            status=status
        ).inc()
        
        self.api_request_duration.labels(
            environment=environment,
            table_id=table_id,
            operation=operation
        ).observe(duration)
        
    def update_active_connections(self, environment, count):
        """更新活躍連接數"""
        self.active_connections.labels(environment=environment).set(count)
```

#### 日誌配置

```python
# logging_config.py
import logging
import logging.handlers
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name, log_file):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 檔案處理器
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        
        # JSON 格式化器
        json_formatter = JsonFormatter()
        file_handler.setFormatter(json_formatter)
        
        self.logger.addHandler(file_handler)
        
    def log_api_request(self, environment, table_id, operation, status, duration, error=None):
        """記錄結構化 API 請求日誌"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': 'INFO',
            'environment': environment,
            'table_id': table_id,
            'operation': operation,
            'status': status,
            'duration_ms': duration * 1000,
            'error': error
        }
        
        self.logger.info(json.dumps(log_data))

class JsonFormatter(logging.Formatter):
    def format(self, record):
        if isinstance(record.msg, dict):
            return json.dumps(record.msg)
        return super().format(record)
```

## 實施建議

### 階段一：架構重構 (2-3 週)
1. **抽象化 Table 處理邏輯**
   - 建立統一的 Table 介面
   - 重構現有的 API 呼叫邏輯
   - 實現配置動態載入

2. **實現動態配置載入**
   - 建立配置管理服務
   - 支援運行時配置更新
   - 實現配置版本控制

3. **引入事件驅動模式**
   - 整合 Redis 或 RabbitMQ
   - 實現事件發布/訂閱機制
   - 建立事件處理器

### 階段二：效能優化 (2-3 週)
1. **全面採用 asyncio**
   - 替換 ThreadPoolExecutor
   - 實現真正的非同步處理
   - 優化 I/O 操作

2. **實現連接池**
   - 使用 aiohttp 連接池
   - 配置連接參數
   - 實現連接健康檢查

3. **添加快取機制**
   - Redis 快取常用配置
   - 實現快取失效策略
   - 監控快取命中率

### 階段三：容器化部署 (2-3 週)
1. **Docker 化應用**
   - 建立 Dockerfile
   - 優化映像大小
   - 實現多階段構建

2. **Kubernetes 部署**
   - 建立 K8s 配置檔案
   - 實現自動擴展
   - 配置服務發現

3. **服務網格**
   - 整合 Istio
   - 實現流量管理
   - 配置安全策略

### 階段四：監控與維護 (1-2 週)
1. **Prometheus + Grafana**
   - 設定監控指標
   - 建立儀表板
   - 配置告警規則

2. **ELK Stack**
   - 整合 Elasticsearch
   - 設定 Logstash
   - 建立 Kibana 視圖

3. **自動化測試**
   - 建立單元測試
   - 實現整合測試
   - 配置 CI/CD 流程

## 預期效果

### 效能提升
- **API 響應時間**：從 100ms 降低到 20ms
- **並發處理能力**：支援數百個並發請求
- **資源使用效率**：CPU 使用率提升 40%，記憶體使用率降低 30%

### 可擴展性
- **水平擴展**：從 5 個環境 × 1 個 table 擴展到 N 個環境 × M 個 table
- **動態配置**：支援運行時添加/移除 table
- **自動擴展**：根據負載自動調整實例數量

### 可靠性
- **故障隔離**：單點故障不影響整體系統
- **故障恢復**：單點故障恢復時間 < 30 秒
- **容錯能力**：支援自動故障轉移

### 維護性
- **獨立部署**：各環境可獨立更新
- **配置管理**：集中式配置管理
- **監控告警**：全面的監控和告警系統

## 風險評估與緩解措施

### 技術風險
1. **複雜度增加**
   - 風險：微服務架構增加系統複雜度
   - 緩解：分階段實施，充分測試

2. **網路延遲**
   - 風險：微服務間通訊增加延遲
   - 緩解：使用高效能訊息佇列，優化網路配置

3. **資料一致性**
   - 風險：分散式系統的資料一致性問題
   - 緩解：實現最終一致性，使用分散式鎖

### 運營風險
1. **學習成本**
   - 風險：團隊需要學習新技術
   - 緩解：提供培訓，建立文檔

2. **監控複雜度**
   - 風險：分散式系統監控複雜
   - 緩解：使用成熟的監控工具，建立標準化流程

## 總結

本改進方案提供了從目前架構平滑遷移的路徑，同時為未來的擴展需求做好了準備。通過微服務架構、事件驅動設計、動態配置管理和容器化部署，可以實現：

1. **高度可擴展**：支援動態增加 table 數量
2. **低延遲**：優化 API 響應時間
3. **高並行**：支援大量並發請求
4. **高可用**：故障隔離和自動恢復
5. **易維護**：模組化設計和自動化部署

建議按照四個階段逐步實施，確保系統穩定性的同時實現架構升級。
