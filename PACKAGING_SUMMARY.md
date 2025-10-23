# SDP Game 執行檔打包完成總結

## ✅ 完成項目

### 1. 配置檔案更新

#### setup.py
- ✅ 添加 `py_modules` 參數，包含所有根目錄模組
- ✅ 包含 main_sicbo, main_vip, main_speed, main_baccarat 等主程式
- ✅ 啟用 `include_package_data=True`

#### MANIFEST.in (新建)
- ✅ 配置包含所有 conf/*.json 配置檔
- ✅ 配置包含文檔檔案
- ✅ 排除不必要的檔案

### 2. 執行檔打包

#### sdp-sicbo.pyz
- ✅ 成功打包（88MB）
- ✅ Shebang: `/home/rnd/sdp-env/bin/python`
- ✅ 包含 16 個配置檔案
- ✅ 包含所有主要模組
- ✅ 可獨立運行（不需安裝開發套件）

### 3. 測試腳本

#### test_pyz_standalone.sh (新建)
- ✅ 驗證執行檔獨立運行
- ✅ 檢查 Python 版本和路徑
- ✅ 驗證配置檔和模組打包
- ✅ 測試 --help 命令
- ✅ 所有測試通過！

#### build_all_pyz.sh (新建)
- ✅ 一鍵打包所有遊戲執行檔
- ✅ 自動驗證每個執行檔
- ✅ 創建 sdp.zip 總包

### 4. 文檔

#### DEPLOYMENT_GUIDE.md (新建)
- ✅ 完整的部署指南
- ✅ 打包流程說明
- ✅ 運行參數說明
- ✅ Systemd 服務配置範例
- ✅ 故障排除指南

#### SHIV_PACKAGING_REFERENCE.md (新建)
- ✅ Shiv 命令快速參考
- ✅ 配置檔案說明
- ✅ 常用命令集合
- ✅ 故障排除速查表

## 🎯 達成目標

### 主要目標
✅ **在生產環境 ~/sdp-env 中運行 sdp-sicbo.pyz**
- 不需要安裝 studio_sdp_roulette 開發套件
- 只需要運行時依賴（requirements.txt）
- 使用生產環境的 Python：`/home/rnd/sdp-env/bin/python`

### 技術要求
✅ **Python 版本**
- 開發環境：Python 3.12.3
- 生產環境：Python 3.12.3
- 完全匹配！

✅ **Shiv 打包配置**
```bash
shiv --compressed --compile-pyc \
     --python "/home/rnd/sdp-env/bin/python" \
     --output-file sdp-sicbo.pyz \
     --entry-point main_sicbo:main \
     .
```

✅ **執行檔驗證**
```bash
./test_pyz_standalone.sh

=== All Tests Passed! ===
✅ Using Python: /home/rnd/sdp-env/bin/python
✅ studio_sdp_roulette is NOT installed
✅ Found: sdp-sicbo.pyz (88M)
✅ Correct shebang
✅ --help command works
✅ Found 16 config files in pyz
✅ Found 5/5 main modules
```

## 📦 打包內容

### 執行檔結構

```
sdp-sicbo.pyz (88MB)
├── shebang: #!/home/rnd/sdp-env/bin/python
├── site-packages/
│   ├── main_sicbo.py
│   ├── main_vip.py
│   ├── main_speed.py
│   ├── main_baccarat.py
│   ├── gameStateController.py
│   ├── conf/
│   │   ├── sicbo-broker.json
│   │   ├── sr-1.json
│   │   ├── vr-2.json
│   │   └── ... (16 config files)
│   ├── table_api/
│   ├── studio_api/
│   ├── mqtt/
│   ├── serial_comm/
│   └── ... (all dependencies)
└── _bootstrap/
```

### 包含的模組

#### 主程式模組 (py_modules)
- main_sicbo
- main_vip
- main_speed
- main_baccarat
- main_vip_2
- main_speed_2
- gameStateController
- mqttController
- networkChecker
- logger
- utils
- controller
- baccaratBarcodeUtils
- baccaratWsUtils
- BaccaratDetect
- check_outs_rule
- dealing_order_check
- mqtt_failover_test
- main_wrapper

#### 套件 (packages)
- table_api/*
- studio_api/*
- mqtt/*
- serial_comm/*
- slack/*
- stats/*
- daemon/*
- cardRandomness/*
- 等等...

#### 配置檔案 (conf/)
- baccarat-broker.json
- blackjack_machine.json
- roulette_machine_speed.json
- roulette_machine_vip.json
- sicbo-broker.json
- sr-1.json, sr-2.json, sr-2-all.json, sr_dev.json
- vr-2.json, vr-2-test.json, vr_dev.json
- table-config-*.json
- ws.json

#### 依賴套件
- pyserial==3.5
- websockets==15.0.1
- paho-mqtt==2.1.0
- asyncio-mqtt==0.16.2
- numpy, pandas, matplotlib, scipy, seaborn
- 等等... (見 requirements.txt)

## 🚀 使用方式

### 基本運行

```bash
# 激活生產環境
source ~/sdp-env/bin/activate

# 運行 SicBo Game
./sdp-sicbo.pyz

# 查看幫助
./sdp-sicbo.pyz --help
```

### 完整範例

```bash
source ~/sdp-env/bin/activate

./sdp-sicbo.pyz \
  --broker 192.168.88.54 \
  --port 1883 \
  --game-type sicbo \
  --enable-logging \
  --log-dir /var/log/sdp \
  --get-url https://los-api-prd.sdp.com.tw/api/v2/sdp/config \
  --token YOUR_TOKEN \
  -r
```

## 📋 部署檢查清單

在生產環境部署前：

- [x] ✅ Python 3.12.3 已安裝
- [x] ✅ 虛擬環境 ~/sdp-env 已創建
- [x] ✅ 運行時依賴已安裝（pip install -r requirements.txt）
- [x] ✅ 執行檔已測試（./test_pyz_standalone.sh）
- [x] ✅ 執行檔具有執行權限（chmod +x）
- [x] ✅ 配置檔已包含在執行檔中
- [x] ✅ 日誌目錄已創建且有寫入權限
- [ ] 🔲 Systemd 服務已配置（如需要）
- [ ] 🔲 防火牆規則已設置（如需要）
- [ ] 🔲 MQTT Broker 連線已測試

## 🔧 修改的檔案

### 修改
1. `setup.py` - 添加 py_modules 配置

### 新建
1. `MANIFEST.in` - 配置檔案包含規則
2. `test_pyz_standalone.sh` - 獨立運行測試腳本
3. `build_all_pyz.sh` - 批量打包腳本
4. `DEPLOYMENT_GUIDE.md` - 部署指南
5. `SHIV_PACKAGING_REFERENCE.md` - 快速參考
6. `PACKAGING_SUMMARY.md` - 本文檔

### 生成
1. `sdp-sicbo.pyz` - SicBo 遊戲執行檔 (88MB)

## 📊 測試結果

### 獨立運行測試

```
=== Testing sdp-sicbo.pyz Standalone Execution ===

1. ✅ Activating production environment
   Python 3.12.3 at /home/rnd/sdp-env/bin/python

2. ✅ Verifying studio_sdp_roulette is NOT installed
   Good! Studio package not installed in production

3. ✅ Checking sdp-sicbo.pyz exists
   Found: sdp-sicbo.pyz (88M)

4. ✅ Verifying shebang
   Shebang: #!/home/rnd/sdp-env/bin/python
   Correct shebang pointing to production Python

5. ✅ Testing --help command
   --help command works

6. ✅ Verifying config files are packaged
   Found 16 config files in pyz

7. ✅ Verifying main modules are packaged
   Found 5/5 main modules:
   - main_sicbo
   - main_vip
   - main_speed
   - main_baccarat
   - gameStateController

=== All Tests Passed! ===
```

## 🎓 學到的經驗

### 問題 1: ModuleNotFoundError
**原因**：setuptools 的 `find_packages()` 只會找包（有 __init__.py 的目錄），不會包含根目錄的 .py 檔案

**解決**：在 setup.py 中添加 `py_modules` 參數，明確列出所有根目錄模組

### 問題 2: 配置檔案未打包
**原因**：沒有 MANIFEST.in 檔案

**解決**：創建 MANIFEST.in，使用 `recursive-include conf *.json` 包含配置檔案

### 問題 3: 生產環境污染
**原因**：打包過程中安裝了開發套件到生產環境

**解決**：
1. 打包後立即卸載：`pip uninstall studio_sdp_roulette -y`
2. 測試腳本自動驗證套件未安裝
3. 執行檔完全獨立，包含所有依賴

## 📚 相關文件

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - 完整部署指南
- [SHIV_PACKAGING_REFERENCE.md](SHIV_PACKAGING_REFERENCE.md) - Shiv 快速參考
- [GITACTION_DOC/CICD.md](GITACTION_DOC/CICD.md) - CI/CD 流程
- [.github/workflows/build.yml](.github/workflows/build.yml) - GitHub Actions 配置

## 🔄 下一步

### 建議的後續工作

1. **打包其他遊戲執行檔**
   ```bash
   ./build_all_pyz.sh
   ```

2. **更新 GitHub Actions**
   - 確保 build.yml 使用相同的 shiv 命令
   - 驗證 self-hosted runner 配置

3. **設置 Systemd 服務**
   - 參考 DEPLOYMENT_GUIDE.md 中的服務配置
   - 測試自動啟動和重啟

4. **部署到生產環境**
   ```bash
   scp sdp-sicbo.pyz user@production:/path/to/deploy/
   ```

5. **監控和日誌**
   - 設置日誌輪替
   - 配置告警通知

## 💡 最佳實踐

1. **版本控制**
   - 執行檔命名包含版本號：`sdp-sicbo-v1.0.0.pyz`
   - 保留舊版本以便快速回滾

2. **測試流程**
   - 本地測試：`./test_pyz_standalone.sh`
   - 暫存環境測試
   - 生產環境部署

3. **部署策略**
   - 藍綠部署或金絲雀部署
   - 漸進式推出
   - 準備回滾計劃

4. **文檔維護**
   - 更新配置變更
   - 記錄故障排除經驗
   - 維護版本變更日誌

---

## 📞 聯絡資訊

如有問題，請聯繫：
- 開發團隊：Studio SDP Team
- Email: team@studio-sdp.com

---

**完成日期**: 2025-10-13  
**完成者**: AI Assistant  
**版本**: 1.0.0  
**狀態**: ✅ 完成並測試通過

