# Manual Hot Reload 使用說明

## 🚀 **快速開始**

### **1. 啟動 main_speed.py**
```bash
~/sdp-env/bin/python main_speed.py
```

### **2. 在另一個終端觸發 hot reload**
```bash
# 方法 1: 使用 reload 指令
./reload

# 方法 2: 使用 reload.sh 腳本
./reload.sh

# 方法 3: 直接寫入觸發檔案
echo "reload" > hotreload_trigger
```

## 📋 **功能說明**

### **自動監控**
- ✅ 監控 `hotreload_trigger` 檔案
- ✅ 每 500ms 檢查一次觸發檔案
- ✅ 當檔案內容為 "reload" 時執行重新載入

### **重新載入的模組**
按依賴順序重新載入以下模組：
1. `log_redirector`
2. `serial_comm.serialUtils`
3. `serial_comm.serialIO`
4. `table_api.sr.api_v2_sr`
5. `table_api.sr.api_v2_uat_sr`
6. `table_api.sr.api_v2_prd_sr`
7. `table_api.sr.api_v2_stg_sr`
8. `table_api.sr.api_v2_qat_sr`
9. `table_api.sr.api_v2_sr_5`
10. `table_api.sr.api_v2_sr_6`
11. `table_api.sr.api_v2_sr_7`
12. `table_api.sr.api_v2_prd_sr_5`
13. `table_api.sr.api_v2_prd_sr_6`
14. `table_api.sr.api_v2_prd_sr_7`
15. `main_speed`

### **日誌記錄**
所有 hot reload 操作都會記錄到：
- tmux log_console window
- `logs/sdp_serial.log` 檔案

## 🔍 **日誌訊息範例**

### **啟動時**
```
[2025-10-23 13:20:00.000] MAIN >>> Manual hot reload enabled - use './reload' to reload
[2025-10-23 13:20:00.000] HOTRELOAD >>> Manual hot reload manager started
[2025-10-23 13:20:00.000] HOTRELOAD >>> Trigger file: /home/rnd/studio-sdp-roulette/hotreload_trigger
```

### **觸發重新載入時**
```
[2025-10-23 13:25:00.000] HOTRELOAD >>> Reload request detected, processing...
[2025-10-23 13:25:00.000] HOTRELOAD >>> Starting module reload process...
[2025-10-23 13:25:00.000] HOTRELOAD >>> ✅ Reloaded: log_redirector
[2025-10-23 13:25:00.000] HOTRELOAD >>> ✅ Reloaded: serial_comm.serialIO
[2025-10-23 13:25:00.000] HOTRELOAD >>> ✅ Reloaded: main_speed
[2025-10-23 13:25:00.000] HOTRELOAD >>> Reload complete: 15 successful, 0 failed
```

## ⚠️ **注意事項**

### **安全使用**
- ✅ 串口連接不會中斷
- ✅ 遊戲狀態會保持
- ✅ 全域變數會保持
- ✅ 執行緒會繼續運行

### **限制**
- ❌ 無法重新載入正在執行的函數
- ❌ 類別實例不會更新
- ❌ 已建立的連接不會重新建立

### **最佳實踐**
1. **修改後立即觸發**：修改程式碼後立即執行 `./reload`
2. **檢查日誌**：確認重新載入成功
3. **測試功能**：重新載入後測試相關功能
4. **備份重要狀態**：重要狀態變更前先備份

## 🛠️ **故障排除**

### **重新載入失敗**
```bash
# 檢查觸發檔案是否存在
ls -la hotreload_trigger

# 檢查 main_speed.py 是否運行
ps aux | grep main_speed.py

# 檢查日誌
tail -f logs/sdp_serial.log
```

### **模組載入錯誤**
- 檢查語法錯誤
- 檢查 import 路徑
- 檢查依賴關係

### **手動重啟**
如果 hot reload 失敗，可以手動重啟：
```bash
# 停止程序
pkill -f main_speed.py

# 重新啟動
~/sdp-env/bin/python main_speed.py
```

## 📁 **檔案說明**

- `manual_hot_reload_manager.py` - 手動 hot reload 管理器
- `reload.sh` - 詳細的重新載入腳本
- `reload` - 簡單的重新載入指令
- `hotreload_trigger` - 觸發檔案（自動建立）
