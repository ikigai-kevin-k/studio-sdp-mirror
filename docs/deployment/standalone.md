# SDP Game 執行檔部署指南

## 概述

本指南說明如何在生產環境中使用 shiv 打包的 SDP Game 執行檔（.pyz）。執行檔可以在生產環境中獨立運行，無需安裝完整的開發環境。

## 環境需求

### 生產環境需求

- Python 3.12.x
- 虛擬環境：`~/sdp-env`
- 運行時依賴套件（已安裝在 sdp-env 中）：
  - pyserial==3.5
  - websockets==15.0.1
  - paho-mqtt==2.1.0
  - asyncio-mqtt==0.16.2
  - 其他依賴見 `requirements.txt`

## 打包執行檔

### 1. 準備開發環境

```bash
cd /home/rnd/studio-sdp-roulette

# 激活生產環境
source ~/sdp-env/bin/activate

# 確保依賴已安裝
pip install -r requirements.txt
```

### 2. 使用 Shiv 打包

#### 打包 SicBo Game

```bash
shiv --compressed --compile-pyc \
     --python "/home/rnd/sdp-env/bin/python" \
     --output-file sdp-sicbo.pyz \
     --entry-point main_sicbo:main \
     .
```

#### 打包其他遊戲

```bash
# VIP Roulette
shiv --compressed --compile-pyc \
     --python "/home/rnd/sdp-env/bin/python" \
     --output-file sdp-vip.pyz \
     --entry-point main_vip:main \
     .

# Speed Roulette
shiv --compressed --compile-pyc \
     --python "/home/rnd/sdp-env/bin/python" \
     --output-file sdp-speed.pyz \
     --entry-point main_speed:main \
     .

# Baccarat
shiv --compressed --compile-pyc \
     --python "/home/rnd/sdp-env/bin/python" \
     --output-file sdp-baccarat.pyz \
     --entry-point main_baccarat:main \
     .
```

### 3. 驗證打包結果

```bash
# 運行測試腳本
./test_pyz_standalone.sh

# 或手動測試
./sdp-sicbo.pyz --help
```

## 部署到生產環境

### 1. 準備生產環境

```bash
# 在生產機器上創建虛擬環境（如果尚未創建）
python3 -m venv ~/sdp-env

# 激活虛擬環境
source ~/sdp-env/bin/activate

# 安裝運行時依賴
pip install -r requirements.txt
```

### 2. 部署執行檔

```bash
# 複製執行檔到生產環境
scp sdp-sicbo.pyz user@production-server:~/

# 或使用 GitHub Actions 自動部署（參見 .github/workflows/build.yml）
```

### 3. 設置執行權限

```bash
chmod +x ~/sdp-sicbo.pyz
```

## 運行執行檔

### 基本用法

```bash
# 激活生產環境
source ~/sdp-env/bin/activate

# 運行 SicBo Game（使用預設參數）
./sdp-sicbo.pyz

# 查看所有可用參數
./sdp-sicbo.pyz --help
```

### 常用參數

```bash
# 指定 MQTT broker
./sdp-sicbo.pyz --broker 192.168.88.54 --port 1883

# 指定遊戲類型
./sdp-sicbo.pyz --game-type sicbo

# 啟用日誌記錄
./sdp-sicbo.pyz --enable-logging --log-dir ./logs

# 指定配置 URL 和 Token
./sdp-sicbo.pyz --get-url https://live-backend-service-api-uat.sdp.com.tw/api/v2/sdp/config --token YOUR_TOKEN

# 重新啟動前執行初始化
./sdp-sicbo.pyz -r
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
  --get-url https://live-backend-service-api-prd.sdp.com.tw/api/v2/sdp/config \
  --token YOUR_PRODUCTION_TOKEN \
  -r
```

## Systemd 服務配置（推薦）

### 創建服務檔案

```bash
sudo nano /etc/systemd/system/sdp-sicbo.service
```

### 服務配置內容

```ini
[Unit]
Description=SDP SicBo Game Service
After=network.target

[Service]
Type=simple
User=rnd
WorkingDirectory=/home/rnd
ExecStart=/home/rnd/sdp-env/bin/python /home/rnd/sdp-sicbo.pyz --broker 192.168.88.54 --enable-logging --log-dir /var/log/sdp
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 管理服務

```bash
# 重新載入 systemd 配置
sudo systemctl daemon-reload

# 啟動服務
sudo systemctl start sdp-sicbo

# 設置開機自動啟動
sudo systemctl enable sdp-sicbo

# 查看服務狀態
sudo systemctl status sdp-sicbo

# 查看服務日誌
sudo journalctl -u sdp-sicbo -f

# 停止服務
sudo systemctl stop sdp-sicbo

# 重啟服務
sudo systemctl restart sdp-sicbo
```

## 故障排除

### 問題 1: 找不到模組

**症狀**：`ModuleNotFoundError: No module named 'main_sicbo'`

**解決方法**：
1. 確認 `setup.py` 中包含 `py_modules` 配置
2. 重新打包執行檔
3. 驗證模組已打包：
   ```bash
   python -c "import zipfile; z = zipfile.ZipFile('sdp-sicbo.pyz'); print([f for f in z.namelist() if 'main_' in f])"
   ```

### 問題 2: 找不到配置檔

**症狀**：`FileNotFoundError: conf/xxx.json`

**解決方法**：
1. 確認 `MANIFEST.in` 存在並包含 `recursive-include conf *.json`
2. 重新打包執行檔
3. 驗證配置檔已打包：
   ```bash
   python -c "import zipfile; z = zipfile.ZipFile('sdp-sicbo.pyz'); print([f for f in z.namelist() if 'conf/' in f])"
   ```

### 問題 3: Python 版本不匹配

**症狀**：執行檔無法運行或出現兼容性錯誤

**解決方法**：
1. 確認生產環境使用 Python 3.12.x
2. 確認打包時使用正確的 Python 路徑：`--python "/home/rnd/sdp-env/bin/python"`
3. 檢查 shebang：`head -1 sdp-sicbo.pyz`

### 問題 4: 缺少依賴套件

**症狀**：`ImportError` 或 `ModuleNotFoundError`

**解決方法**：
```bash
source ~/sdp-env/bin/activate
pip install -r requirements.txt
```

## 打包配置檔案說明

### setup.py 關鍵配置

```python
py_modules=[
    "main_sicbo",
    "main_vip",
    "main_speed",
    "main_baccarat",
    # ... 其他根目錄模組
],
include_package_data=True,  # 重要：啟用包含數據檔案
```

### MANIFEST.in 內容

```
recursive-include conf *.json
recursive-include conf *.yaml
recursive-include conf *.yml
```

### pyproject.toml 配置

```toml
[project]
name = "studio_sdp_roulette"
version = "1.0.0"
requires-python = ">=3.12"

[tool.setuptools.packages.find]
include = ["*"]
exclude = ["tests*", "setup*", "proto*", "self_test*"]
```

## 測試清單

在部署前，請確認：

- [ ] ✅ 執行檔可以在生產環境中運行（不需安裝 studio_sdp_roulette）
- [ ] ✅ Shebang 指向正確的 Python 解釋器
- [ ] ✅ 配置檔已打包進執行檔
- [ ] ✅ 所有主要模組已打包
- [ ] ✅ `--help` 命令正常工作
- [ ] ✅ 運行時依賴已安裝在生產環境
- [ ] ✅ 執行檔具有執行權限

## GitHub Actions 自動部署

參見 `.github/workflows/build.yml` 了解自動化打包和部署流程。

關鍵步驟：
1. 測試和品質檢查
2. 使用 Shiv 打包所有遊戲執行檔
3. 打包成 `sdp.zip`
4. 上傳到 self-hosted runner
5. 自動部署到經銷商 PC

## 注意事項

1. **不要在生產環境安裝開發套件**：執行檔應該獨立運行，只需要運行時依賴。

2. **配置檔路徑**：如果程式需要讀取外部配置檔，請確保配置檔與執行檔在同一目錄或指定正確路徑。

3. **日誌目錄**：確保日誌目錄存在且有寫入權限：
   ```bash
   mkdir -p /var/log/sdp
   sudo chown rnd:rnd /var/log/sdp
   ```

4. **環境變數**：如需設置環境變數，可在 systemd 服務檔案中添加：
   ```ini
   [Service]
   Environment="MQTT_BROKER=192.168.88.54"
   Environment="LOG_LEVEL=INFO"
   ```

## 相關文件

- [CICD.md](GITACTION_DOC/CICD.md) - CI/CD 流程文檔
- [GIT_CI_CONTROL_README.md](GITACTION_DOC/GIT_CI_CONTROL_README.md) - Git CI 控制說明
- [build.yml](.github/workflows/build.yml) - GitHub Actions 建置配置

## 支援

如有問題，請聯繫：
- 開發團隊：Studio SDP Team
- Email: kevin.k@ikigai.team

---

最後更新：2025-10-13
版本：1.0.0

