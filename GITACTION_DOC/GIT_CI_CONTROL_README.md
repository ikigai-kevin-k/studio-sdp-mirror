# Git CI/CD 流程控制說明

## 概述

在 `dev/ella/deploy` 分支上，您可以通過在 commit message 中添加特殊標記來選擇性跳過 CI/CD 流程。

## 可用的控制標記

### 跳過整個 CI/CD 流程

使用以下任一標記可以跳過所有 CI/CD 步驟（測試、建置、安全掃描、部署）：

- `[skip-ci]`
- `[no-build]`

### 使用範例

```bash
# 跳過 CI/CD 流程的 commit
git commit -m "Update documentation [skip-ci]"

# 或者使用 no-build 標記
git commit -m "Fix typo in comments [no-build]"

# 正常觸發 CI/CD 流程的 commit
git commit -m "Add new feature for VIP roulette"
```

## 受影響的 Workflow

以下 GitHub Actions workflow 會受到這些標記的影響：

1. **Build and Test SDP Roulette System** (`build.yml`)
   - 測試和品質檢查
   - 建置可執行檔
   - 安全掃描
   - 部署到經銷商 PC

## 注意事項

- 這些標記只對 `dev/ella/deploy` 分支有效
- 標記必須完全匹配（包括方括號）
- 標記可以放在 commit message 的任何位置
- 如果沒有使用這些標記，CI/CD 流程會正常執行

## 其他分支的 CI/CD 控制

- `gitaction` 分支：已禁用自動觸發，只能手動觸發
- `quick-build` workflow：已禁用自動觸發，只能手動觸發

## 緊急情況下的手動觸發

如果需要緊急建置或部署，可以使用以下方式：

1. 前往 GitHub Actions 頁面
2. 選擇對應的 workflow
3. 點擊 "Run workflow" 按鈕
4. 選擇分支並執行

## 最佳實踐

- 對於文檔更新、註釋修改等不需要測試的變更，使用 `[skip-ci]`
- 對於緊急修復或實驗性功能，使用 `[no-build]`
- 對於正式的功能開發和修復，不要使用這些標記
- 在團隊中統一使用這些標記的規範
