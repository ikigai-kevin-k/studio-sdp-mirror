# Shiv 打包執行檔快速參考

## 快速開始

### 打包單一遊戲（SicBo）

```bash
source ~/sdp-env/bin/activate
cd /home/rnd/studio-sdp-roulette

shiv --compressed --compile-pyc \
     --python "/home/rnd/sdp-env/bin/python" \
     --output-file sdp-sicbo.pyz \
     --entry-point main_sicbo:main \
     .
```

### 打包所有遊戲

```bash
source ~/sdp-env/bin/activate
cd /home/rnd/studio-sdp-roulette
./build_all_pyz.sh
```

### 測試執行檔

```bash
source ~/sdp-env/bin/activate
./test_pyz_standalone.sh
```

## 配置檔案說明

### 1. setup.py

關鍵配置：需要包含根目錄的 Python 模組

```python
setup(
    name="studio_sdp_roulette",
    version="1.0.0",
    packages=find_packages(...),
    py_modules=[
        "main_sicbo",
        "main_vip",
        "main_speed",
        "main_baccarat",
        "gameStateController",
        # ... 其他根目錄模組
    ],
    include_package_data=True,  # 必須啟用
    # ...
)
```

### 2. MANIFEST.in

確保配置檔案被包含：

```
recursive-include conf *.json
recursive-include conf *.yaml
recursive-include conf *.yml
```

### 3. pyproject.toml

專案基本配置：

```toml
[project]
name = "studio_sdp_roulette"
version = "1.0.0"
requires-python = ">=3.12"

[tool.setuptools.packages.find]
include = ["*"]
exclude = ["tests*", "setup*", "proto*", "self_test*"]
```

## Shiv 命令參數說明

### 基本參數

| 參數 | 說明 | 範例 |
|------|------|------|
| `--compressed` | 壓縮 .pyz 檔案 | 減少檔案大小 |
| `--compile-pyc` | 預編譯 bytecode | 加快啟動速度 |
| `--python` | 指定 Python 解釋器 | `/home/rnd/sdp-env/bin/python` |
| `--output-file` / `-o` | 輸出檔案名稱 | `sdp-sicbo.pyz` |
| `--entry-point` / `-e` | 程式進入點 | `main_sicbo:main` |
| `.` | 來源目錄 | 當前目錄 |

### 進階參數

```bash
# 指定環境變數
--env NAME=value

# 排除套件
--exclude-deps package-name

# 指定 site-packages
--site-packages PATH

# 詳細輸出
--verbose
```

## 環境要求

### 開發環境（打包用）

```bash
# Python 3.12+
python3 --version

# 激活虛擬環境
source ~/sdp-env/bin/activate

# 安裝依賴
pip install -r requirements.txt
pip install shiv
```

### 生產環境（運行用）

```bash
# Python 3.12+
python3 --version

# 激活虛擬環境
source ~/sdp-env/bin/activate

# 只需安裝運行時依賴（不需要 shiv）
pip install -r requirements.txt

# 不需要安裝 studio_sdp_roulette 套件！
```

## 常用命令

### 檢查執行檔內容

```bash
# 查看所有檔案
python -c "import zipfile; z = zipfile.ZipFile('sdp-sicbo.pyz'); print('\n'.join(z.namelist()))"

# 查看配置檔
python -c "import zipfile; z = zipfile.ZipFile('sdp-sicbo.pyz'); print('\n'.join([f for f in z.namelist() if 'conf/' in f]))"

# 查看主模組
python -c "import zipfile; z = zipfile.ZipFile('sdp-sicbo.pyz'); print('\n'.join([f for f in z.namelist() if 'main_' in f]))"

# 檢查檔案大小
du -h sdp-sicbo.pyz

# 檢查 shebang
head -1 sdp-sicbo.pyz
```

### 驗證執行檔

```bash
# 測試 help
./sdp-sicbo.pyz --help

# 測試執行（乾跑）
./sdp-sicbo.pyz --version 2>&1 | head

# 檢查依賴
ldd sdp-sicbo.pyz  # 應該沒有輸出（純 Python）
```

## 打包流程

### 標準流程

1. **準備環境**
   ```bash
   source ~/sdp-env/bin/activate
   cd /home/rnd/studio-sdp-roulette
   ```

2. **清理舊檔案**
   ```bash
   rm -f sdp-*.pyz sdp.zip
   pip uninstall studio_sdp_roulette -y
   ```

3. **更新依賴**
   ```bash
   pip install -r requirements.txt
   ```

4. **打包執行檔**
   ```bash
   shiv --compressed --compile-pyc \
        --python "/home/rnd/sdp-env/bin/python" \
        --output-file sdp-sicbo.pyz \
        --entry-point main_sicbo:main \
        .
   ```

5. **驗證**
   ```bash
   ./test_pyz_standalone.sh
   ```

6. **部署**
   ```bash
   scp sdp-sicbo.pyz user@server:/path/to/deploy/
   ```

## 故障排除速查

### 問題：ModuleNotFoundError

```bash
# 原因：模組未包含在 setup.py 的 py_modules 中
# 解決：更新 setup.py，添加缺失的模組名稱
```

### 問題：找不到配置檔

```bash
# 原因：MANIFEST.in 缺失或配置錯誤
# 解決：創建/更新 MANIFEST.in，添加 recursive-include conf *.json
```

### 問題：Python 版本不匹配

```bash
# 原因：打包和運行使用不同的 Python 版本
# 解決：確保使用相同的 Python 路徑
shiv --python "/home/rnd/sdp-env/bin/python" ...
```

### 問題：執行檔過大

```bash
# 原因：包含了不必要的依賴或檔案
# 解決方案：
# 1. 使用 --compressed 參數
# 2. 排除不需要的依賴：--exclude-deps package-name
# 3. 在 setup.py 中排除測試檔案
```

## 檔案大小參考

| 執行檔 | 預期大小 | 包含內容 |
|--------|----------|----------|
| sdp-sicbo.pyz | ~88MB | SicBo + 依賴 + 配置 |
| sdp-vip.pyz | ~88MB | VIP Roulette + 依賴 + 配置 |
| sdp-speed.pyz | ~88MB | Speed Roulette + 依賴 + 配置 |
| sdp-baccarat.pyz | ~88MB | Baccarat + 依賴 + 配置 |
| sdp.zip | ~300MB | 所有執行檔壓縮 |

## GitHub Actions 整合

參見 `.github/workflows/build.yml` 第 106-120 行：

```yaml
- name: Build SicBo executable
  run: |
    shiv --compressed --compile-pyc \
         --python "/usr/bin/python3" \
         --output-file sdp-sicbo.pyz \
         --entry-point main_sicbo:main .
```

## 相關腳本

| 腳本 | 用途 |
|------|------|
| `build_all_pyz.sh` | 打包所有遊戲執行檔 |
| `test_pyz_standalone.sh` | 測試執行檔獨立運行 |
| `test-ci.sh` | 完整 CI/CD 測試 |

## 參考資源

- [Shiv 官方文檔](https://shiv.readthedocs.io/)
- [Python Packaging 指南](https://packaging.python.org/)
- [部署指南](DEPLOYMENT_GUIDE.md)
- [CI/CD 文檔](GITACTION_DOC/CICD.md)

---

最後更新：2025-10-13
版本：1.0.0

