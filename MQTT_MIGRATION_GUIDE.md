# MQTT 重構遷移指南

## 概述

本文檔說明如何從舊的 MQTT 實作遷移到新的統一 MQTT 客戶端 (`UnifiedMQTTClient`)。

## 重構目標

1. **統一介面**：所有遊戲類型使用相同的 MQTT 客戶端介面
2. **消除重複**：移除多個檔案中重複的 `MQTTLogger` 實作
3. **改善配置管理**：集中管理 MQTT 配置和認證資訊
4. **增強錯誤處理**：統一的錯誤處理和重連機制
5. **支援擴展**：輕鬆新增新的遊戲類型（如 Roulette）

## 遷移步驟

### 1. 舊的實作方式

```python
# 舊的 mqttController.py 方式
from mqttController import MQTTController

controller = MQTTController("client_id", "broker", 1883)
await controller.initialize()
await controller.send_detect_command(round_id, input_stream, output_stream)
await controller.cleanup()
```

### 2. 新的統一實作方式

```python
# 新的統一客戶端方式
from mqtt.base_client import UnifiedMQTTClient, BrokerConfig

# 配置多個 broker 支援 failover
broker_configs = [
    BrokerConfig(broker="192.168.20.9", port=1883, priority=1),
    BrokerConfig(broker="192.168.20.10", port=1883, priority=2)
]

# 建立統一客戶端
client = UnifiedMQTTClient(
    client_id="sicbo_client",
    broker_configs=broker_configs
)

# 新增訊息處理器
def sicbo_handler(topic, payload, data):
    # 處理 Sicbo 訊息
    pass

client.add_message_handler("ikg/idp/SBO-001/response", sicbo_handler)

# 連線並使用
await client.connect_with_failover()
client.subscribe("ikg/idp/SBO-001/response")
client.publish("ikg/idp/SBO-001/command", json.dumps(command))
await client.disconnect()
```

## 主要改進

### 1. 統一的連線管理

**舊方式**：
- 每個控制器都有自己的連線邏輯
- 硬編碼的 broker 位址
- 缺乏 failover 機制

**新方式**：
- 統一的連線管理
- 支援多 broker failover
- 自動重連機制

### 2. 標準化的訊息處理

**舊方式**：
- 每個控制器有自己的訊息處理邏輯
- 重複的 JSON 解析程式碼
- 缺乏統一的錯誤處理

**新方式**：
- 統一的訊息處理框架
- 支援多個訊息處理器
- 自動 JSON 解析和錯誤處理

### 3. 改善的配置管理

**舊方式**：
- 認證資訊硬編碼在多處
- 缺乏配置檔案支援
- 難以維護

**新方式**：
- 集中化的配置管理
- 支援配置檔案
- 易於維護和更新

## 遊戲特定遷移

### Sicbo 遊戲遷移

```python
# 舊的 IDPController
class IDPController(Controller):
    def __init__(self, config: GameConfig):
        self.mqtt_client = MQTTLogger(
            client_id=f"idp_controller_{config.room_id}",
            broker="192.168.88.54",
            port=config.broker_port,
        )

# 新的統一實作
class UnifiedIDPController(Controller):
    def __init__(self, config: GameConfig):
        broker_configs = [
            BrokerConfig(broker="192.168.20.9", port=1883, priority=1),
            BrokerConfig(broker="192.168.20.10", port=1883, priority=2)
        ]
        self.mqtt_client = UnifiedMQTTClient(
            client_id=f"idp_controller_{config.room_id}",
            broker_configs=broker_configs
        )
        self.mqtt_client.add_message_handler(
            "ikg/idp/SBO-001/response",
            self._handle_sicbo_response
        )
```

### Baccarat 遊戲遷移

```python
# 舊的 BaccaratIDPController
class BaccaratIDPController(Controller):
    def __init__(self, config: GameConfig):
        self.mqtt_client = MQTTLogger(
            client_id=f"baccarat_idp_controller_{config.room_id}",
            broker="192.168.20.10",
            port=1883,
        )

# 新的統一實作
class UnifiedBaccaratIDPController(Controller):
    def __init__(self, config: GameConfig):
        broker_configs = [
            BrokerConfig(broker="192.168.20.10", port=1883, priority=1),
            BrokerConfig(broker="192.168.20.9", port=1883, priority=2)
        ]
        self.mqtt_client = UnifiedMQTTClient(
            client_id=f"baccarat_idp_controller_{config.room_id}",
            broker_configs=broker_configs
        )
        self.mqtt_client.add_message_handler(
            "ikg/idp/BAC-001/response",
            self._handle_baccarat_response
        )
```

### Roulette 遊戲新增

```python
# 新的 Roulette 控制器（使用統一客戶端）
class RouletteIDPController(Controller):
    def __init__(self, config: GameConfig):
        broker_configs = [
            BrokerConfig(broker="192.168.20.9", port=1883, priority=1),
            BrokerConfig(broker="192.168.20.10", port=1883, priority=2)
        ]
        self.mqtt_client = UnifiedMQTTClient(
            client_id=f"roulette_idp_controller_{config.room_id}",
            broker_configs=broker_configs
        )
        self.mqtt_client.add_message_handler(
            "ikg/idp/ROU-001/response",
            self._handle_roulette_response
        )
```

## 配置檔案支援

### 建立遊戲特定的配置檔案

```json
// conf/roulette-broker.json
{
    "brokers": [
        {
            "broker": "192.168.20.9",
            "port": 1883,
            "username": "PFC",
            "password": "wago",
            "priority": 1
        },
        {
            "broker": "192.168.20.10",
            "port": 1883,
            "username": "PFC",
            "password": "wago",
            "priority": 2
        }
    ],
    "game_config": {
        "game_type": "roulette",
        "game_code": "ROU-001",
        "command_topic": "ikg/idp/ROU-001/command",
        "response_topic": "ikg/idp/ROU-001/response"
    }
}
```

## 測試和驗證

### 1. 執行示範程式

```bash
python mqtt/demo_unified_client.py
```

### 2. 驗證功能

- [ ] 連線建立和 failover 機制
- [ ] 訊息訂閱和發布
- [ ] 訊息處理器註冊和執行
- [ ] 錯誤處理和重連
- [ ] 不同遊戲類型的支援

## 第二階段：統一的 MQTT 配置管理類別

### 新增功能

第二個重構階段建立了統一的 MQTT 配置管理系統：

#### 1. **MQTTConfigManager 類別**
- 集中管理所有 MQTT 配置
- 支援 JSON 配置檔案載入
- 環境切換支援 (development, staging, production)
- 配置驗證和錯誤處理

#### 2. **配置檔案格式**
```json
{
    "brokers": [
        {
            "broker": "192.168.20.9",
            "port": 1883,
            "username": "PFC",
            "password": "wago",
            "priority": 1
        }
    ],
    "game_config": {
        "game_type": "sicbo",
        "game_code": "SBO-001",
        "command_topic": "ikg/idp/SBO-001/command",
        "response_topic": "ikg/idp/SBO-001/response",
        "shaker_topic": "ikg/sicbo/Billy-III/listens",
        "timeout": 10,
        "retry_count": 3
    },
    "environment": "development",
    "log_level": "INFO"
}
```

#### 3. **使用範例**
```python
from mqtt.config_manager import get_config, GameType, Environment

# 載入配置
config = get_config(GameType.SICBO, Environment.DEVELOPMENT)

# 使用配置建立客戶端
client = UnifiedMQTTClient(
    client_id=config.client_id,
    broker_configs=config.brokers,
    default_username=config.default_username,
    default_password=config.default_password
)
```

#### 4. **統一控制器**
- `UnifiedGameController` 基礎類別
- `UnifiedSicboController` Sicbo 控制器
- `UnifiedBaccaratController` Baccarat 控制器
- `UnifiedRouletteController` Roulette 控制器

### 新增檔案
- `mqtt/config_manager.py` - 配置管理類別
- `mqtt/demo_config_manager.py` - 配置管理器示範
- `mqtt/unified_controllers.py` - 統一遊戲控制器
- `conf/roulette-broker.json` - Roulette 配置檔案

## 第三階段：統一的 MQTT 訊息處理器

### 新增功能

第三個重構階段建立了統一的 MQTT 訊息處理框架：

#### 1. **UnifiedMessageProcessor 類別**
- 統一的訊息處理框架
- 優先級佇列管理
- 訊息驗證和轉換
- 錯誤處理和重試機制
- 訊息歷史和統計

#### 2. **訊息處理管道**
- 訊息驗證器 (MessageValidator)
- 訊息轉換器 (MessageTransformer)
- 訊息處理器 (MessageProcessor)
- 訊息路由器 (MessageRouter)

#### 3. **整合系統**
- `IntegratedMQTTSystem` 整合所有組件
- 統一的 API 介面
- 自動訊息處理
- 完整的錯誤處理

#### 4. **使用範例**
```python
from mqtt.integrated_system import create_sicbo_system

# 建立 Sicbo 系統
system = await create_sicbo_system()

# 發送檢測命令
success, result = await system.detect("round_001")

# 清理資源
await system.cleanup()
```

### 新增檔案
- `mqtt/message_processor.py` - 統一的訊息處理器
- `mqtt/demo_message_processor.py` - 訊息處理器示範
- `mqtt/integrated_system.py` - 整合系統
- `mqtt/demo_integrated_system.py` - 整合系統示範

## 第四階段：連線管理器

### 新增功能

第四個重構階段建立了統一的連線管理系統：

#### 1. **UnifiedConnectionManager 類別**
- 連線池管理和負載平衡
- 健康監控和自動故障轉移
- 連線統計和分析
- 資源管理和清理
- 連線生命週期管理

#### 2. **負載平衡策略**
- Round Robin: 輪詢分配
- Least Connections: 最少連線數
- Health Score: 健康分數
- Response Time: 響應時間

#### 3. **健康監控**
- 定期健康檢查
- 連線狀態追蹤
- 自動故障恢復
- 效能指標監控

#### 4. **完整系統整合**
- `CompleteMQTTSystem` 整合所有組件
- 生產就緒的配置
- 完整的錯誤處理
- 效能優化

### 新增檔案
- `mqtt/connection_manager.py` - 統一的連線管理器
- `mqtt/demo_connection_manager.py` - 連線管理器示範
- `mqtt/complete_system.py` - 完整系統整合
- `mqtt/demo_complete_system.py` - 完整系統示範

## 🎉 **重構專案完成！**

### 📋 **重構總結**

所有四個重構階段已完成，建立了完整的統一 MQTT 系統：

#### ✅ **第一階段：統一的 MQTT 基礎客戶端類別**
- `UnifiedMQTTClient` 提供統一的 MQTT 操作介面
- 支援 failover 機制和自動重連
- 統一的訊息處理和錯誤處理

#### ✅ **第二階段：統一的 MQTT 配置管理類別**
- `MQTTConfigManager` 集中管理所有配置
- 支援 JSON 配置檔案和環境切換
- 統一的配置驗證和錯誤處理

#### ✅ **第三階段：統一的 MQTT 訊息處理器**
- `UnifiedMessageProcessor` 提供完整的訊息處理框架
- 模組化處理管道和優先級佇列
- 統一的錯誤處理和重試機制

#### ✅ **第四階段：連線管理器**
- `UnifiedConnectionManager` 提供連線池和負載平衡
- 健康監控和自動故障轉移
- 連線統計和效能監控

### 🚀 **最終整合系統**

`CompleteMQTTSystem` 整合了所有四個階段的組件，提供：

- **統一的 API 介面**：所有遊戲類型使用相同的介面
- **完整的錯誤處理**：統一的錯誤處理和恢復機制
- **效能優化**：連線池、負載平衡、訊息佇列
- **生產就緒**：支援多環境配置和監控
- **易於擴展**：模組化設計，易於新增功能

### 📈 **改進效果**

- ✅ **消除重複**：移除了多個重複的 MQTT 實作
- ✅ **統一介面**：所有遊戲使用相同的 MQTT 系統
- ✅ **支援擴展**：輕鬆新增 Roulette 和其他遊戲類型
- ✅ **改善維護**：集中化的程式碼管理
- ✅ **增強穩定性**：failover 機制和錯誤處理
- ✅ **效能優化**：連線池和負載平衡
- ✅ **生產就緒**：完整的監控和統計功能

## 後續步驟

1. ✅ **第一階段**：統一的 MQTT 基礎客戶端類別 - 已完成
2. ✅ **第二階段**：統一的 MQTT 配置管理類別 - 已完成
3. ✅ **第三階段**：統一的 MQTT 訊息處理器 - 已完成
4. ✅ **第四階段**：連線管理器 - 已完成

## 🎯 **使用建議**

### 新專案
使用 `CompleteMQTTSystem` 作為統一的 MQTT 解決方案：

```python
from mqtt.complete_system import create_complete_sicbo_system

# 建立完整的 Sicbo 系統
system = await create_complete_sicbo_system()

# 發送檢測命令
success, result = await system.detect("round_001")

# 清理資源
await system.cleanup()
```

### 現有專案遷移
1. 逐步替換舊的 MQTT 實作
2. 使用新的配置檔案格式
3. 遷移到統一的 API 介面
4. 啟用連線池和訊息處理功能

### 生產環境
- 使用 `Environment.PRODUCTION` 配置
- 啟用連線池和健康監控
- 配置適當的錯誤處理和重試機制
- 監控系統統計和效能指標

## 注意事項

- 遷移過程中保持向後相容性
- 逐步替換舊的實作
- 充分測試每個遊戲類型的功能
- 更新相關的測試和文檔
