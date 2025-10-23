# Git Hooks for Studio SDP Roulette

這個專案包含了自動化的 Git hooks 來確保程式碼品質和一致性。

## 🚀 快速安裝

### 自動安裝（推薦）

```bash
# 在專案根目錄執行
./install-git-hooks.sh
```

這個腳本會：
- 創建虛擬環境（如果不存在）
- 安裝所有必要的依賴
- 設置 Git hooks
- 測試 hooks 是否正常工作

### 手動安裝

如果你偏好手動設置：

```bash
# 1. 創建虛擬環境
python3 -m venv venv
source venv/bin/activate

# 2. 安裝依賴
pip install -e ".[dev]"

# 3. 設置 hooks 權限
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push
```

## 📋 可用的 Hooks

### Pre-commit Hook

**觸發時機**: 每次執行 `git commit` 時

**功能**:
- 檢查 Black 程式碼格式
- 執行 Flake8 關鍵錯誤檢查
- 阻止包含格式問題的 commit

**配置**: `.git/hooks/pre-commit`

### Pre-push Hook

**觸發時機**: 每次執行 `git push` 時

**功能**:
- 自動修復 Black 格式問題
- 執行完整的 Flake8 檢查
- 運行模組導入測試
- 自動提交格式修復（如果需要）

**配置**: `.git/hooks/pre-push`

## 🔧 工具說明

### Black

Python 程式碼格式化工具，確保所有程式碼都符合一致的格式標準。

```bash
# 檢查格式
black --check --diff .

# 自動修復格式
black .
```

### Flake8

Python 程式碼品質檢查工具，檢查語法錯誤、風格問題和複雜度。

```bash
# 檢查關鍵錯誤
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# 檢查風格問題
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
```

## 📝 工作流程

### 正常開發流程

1. **編輯程式碼**
   ```bash
   # 編輯你的檔案
   vim main_sicbo.py
   ```

2. **提交變更**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   # Pre-commit hook 會自動運行
   ```

3. **推送到遠端**
   ```bash
   git push origin dev/ella/deploy
   # Pre-push hook 會自動運行
   ```

### 如果格式檢查失敗

1. **Pre-commit 失敗**
   ```bash
   # 手動修復格式
   black .
   
   # 重新提交
   git add .
   git commit -m "feat: add new feature"
   ```

2. **Pre-push 失敗**
   - Hook 會自動修復格式問題
   - 創建一個新的 commit
   - 提示你重新 push

## ⚙️ 配置選項

### 跳過 Hooks（不推薦）

```bash
# 跳過 pre-commit hook
git commit --no-verify -m "message"

# 跳過 pre-push hook
git push --no-verify
```

### 自定義配置

你可以修改以下檔案來自定義 hooks 行為：

- `.git/hooks/pre-commit` - Pre-commit hook 邏輯
- `.git/hooks/pre-push` - Pre-push hook 邏輯
- `pyproject.toml` - Black 和 Flake8 配置

## 🐛 故障排除

### 常見問題

1. **Hook 權限錯誤**
   ```bash
   chmod +x .git/hooks/pre-commit
   chmod +x .git/hooks/pre-push
   ```

2. **虛擬環境問題**
   ```bash
   # 重新創建虛擬環境
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **依賴缺失**
   ```bash
   pip install black flake8
   ```

### 檢查 Hook 狀態

```bash
# 檢查 hooks 是否存在
ls -la .git/hooks/

# 測試 pre-commit hook
.git/hooks/pre-commit

# 測試 pre-push hook
.git/hooks/pre-push
```

## 📚 相關資源

- [Git Hooks 官方文檔](https://git-scm.com/docs/githooks)
- [Black 格式化工具](https://black.readthedocs.io/)
- [Flake8 程式碼檢查](https://flake8.pycqa.org/)
- [Python 編碼標準 (PEP 8)](https://www.python.org/dev/peps/pep-0008/)

## 🤝 團隊協作

### 新成員設置

新加入的團隊成員只需要執行：

```bash
git clone <repository-url>
cd studio-sdp-roulette
./install-git-hooks.sh
```

### 持續整合

這些 hooks 與 GitHub Actions 工作流程配合使用，確保：

- 本地開發時的程式碼品質
- CI/CD 流程中的一致性檢查
- 團隊程式碼風格的統一

## 📞 支援

如果你遇到問題或有改進建議，請：

1. 檢查這個文檔的故障排除部分
2. 查看專案的 Issues 頁面
3. 聯繫團隊成員尋求協助

---

**記住**: 這些 hooks 是為了幫助你寫出更好的程式碼，不是阻礙你的開發流程。如果遇到問題，隨時可以尋求幫助！ 🚀
