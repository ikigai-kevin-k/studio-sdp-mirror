# Studio SDP Roulette Build Fixes

## 問題描述

在 GitHub Actions 中透過 shiv 打包的 `sdp-sicbo.pyz` 執行檔在目標機器上執行時出現以下錯誤：

```
ModuleNotFoundError: No module named 'main_sicbo'
```

## 根本原因

1. **模組路徑問題**：shiv 在打包時無法正確找到 `main_sicbo` 模組
2. **缺少適當的包裝結構**：沒有正確的 `__init__.py` 和 `setup.py` 檔案
3. **shiv 打包參數不當**：使用了不正確的參數組合

## 解決方案

### 1. 更新 `__init__.py`

創建了完整的包裝初始化檔案，確保所有模組都能被正確識別：

```python
# Import main modules to make them available
from . import main_sicbo
from . import main_vip
from . import main_speed
from . import main_baccarat
```

### 2. 創建 `setup.py`

添加了 `setup.py` 檔案來改善 shiv 打包過程：

```python
entry_points={
    'console_scripts': [
        'sdp-vip=main_vip:main',
        'sdp-speed=main_speed:main',
        'sdp-sicbo=main_sicbo:main',
        'sdp-baccarat=main_baccarat:main',
    ],
}
```

### 3. 優化 GitHub Actions 工作流程

#### 修改前的 shiv 命令：
```bash
PYTHONPATH=. shiv --compressed --compile-pyc -o sdp-sicbo.pyz -e main_sicbo:main .
```

#### 修改後的 shiv 命令：
```bash
shiv --compressed --compile-pyc --site-packages . --python "/usr/bin/python3" --output-file sdp-sicbo.pyz --entry-point main_sicbo:main .
```

### 4. 添加模組驗證

在 build.yml 中添加了模組驗證步驟，確保打包前所有模組都能正確導入。

### 5. 創建測試腳本

創建了 `test_build.py` 腳本來驗證打包過程和模組導入。

## 主要修改檔案

1. **`.github/workflows/build.yml`** - 更新 shiv 打包命令和添加驗證步驟
2. **`__init__.py`** - 添加模組導入和包裝元數據
3. **`setup.py`** - 創建新的安裝腳本
4. **`test_build.py`** - 創建測試腳本

## 關鍵改進

1. **使用 `--site-packages`**：確保所有依賴都被正確打包
2. **指定 Python 解釋器路徑**：使用 `--python "/usr/bin/python3"`
3. **使用長格式參數**：`--output-file` 和 `--entry-point` 替代短格式
4. **添加模組驗證**：在打包前驗證所有模組都能正確導入

## 測試建議

在部署前，建議執行以下測試：

```bash
# 測試模組導入
python test_build.py

# 測試打包過程（本地）
shiv --compressed --compile-pyc --site-packages . --python "/usr/bin/python3" --output-file test-sicbo.pyz --entry-point main_sicbo:main .

# 測試執行檔
python test-sicbo.pyz
```

## 注意事項

1. 確保目標機器上的 Python 版本與打包時使用的版本相容
2. 檢查目標機器上的 Python 路徑是否與 `--python` 參數指定的路徑一致
3. 如果仍有問題，可以嘗試使用 `--python "$(which python3)"` 來動態指定路徑

## 相關資源

- [shiv 官方文檔](https://shiv.readthedocs.io/)
- [Python 包裝最佳實踐](https://packaging.python.org/guides/)
- [GitHub Actions 工作流程語法](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
