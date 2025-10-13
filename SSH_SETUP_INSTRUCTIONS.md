# SSH 公鑰設置說明

## 問題診斷
GitHub Actions SSH 連線失敗的原因：
- ✅ SSH 私鑰格式正確
- ✅ SSH 連線建立成功  
- ❌ **公鑰認證失敗** - ASB-001-1 伺服器拒絕了我們的公鑰

## 解決方案

### 步驟 1: 取得公鑰內容
從 strong-pc 上取得對應的公鑰：
```bash
ella@strong-pc ~/.ssh> cat id_studio_runner.pub
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIB9t344CiHCwIwm+QRL5MRcVhLoJdGWQNAEezBme471K tony.p@tony.p-MacBook
```

### 步驟 2: 在 ASB-001-1 上設置公鑰
需要將上述公鑰添加到 ASB-001-1 的 `~/.ssh/authorized_keys` 檔案中：

```bash
# 方法 1: 直接編輯 authorized_keys 檔案
ssh rnd@192.168.88.54
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIB9t344CiHCwIwm+QRL5MRcVhLoJdGWQNAEezBme471K tony.p@tony.p-MacBook" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 步驟 3: 驗證設置
設置完成後，測試連線：
```bash
ssh ASB-001-1 "echo 'SSH connection successful'"
```

## 其他 Dealer PCs
同樣需要對以下伺服器執行相同操作：
- ARO-001-1 (192.168.88.50)
- ARO-001-2 (192.168.88.51)  
- ARO-002-1 (192.168.88.52)

## 注意事項
- 確保 `~/.ssh` 目錄權限為 700
- 確保 `authorized_keys` 檔案權限為 600
- 公鑰必須完整複製，包括註解部分

## 自動化方案 (未來)
可以考慮使用 `ssh-copy-id` 命令來自動化公鑰設置：
```bash
ssh-copy-id -i ~/.ssh/id_studio_runner.pub rnd@192.168.88.54
```
# SSH Connection Test - Mon Oct 13 12:43:07 PM +04 2025
