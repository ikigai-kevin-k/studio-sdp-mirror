#!/bin/bash

echo "=== 執行完整的本地 CI/CD 測試流程 ==="

# 確保在虛擬環境中
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "❌ 請先啟動虛擬環境: source venv/bin/activate"
    exit 1
fi

echo "✅ 虛擬環境已啟動: $VIRTUAL_ENV"
echo "Python 版本: $(python --version)"

echo ""
echo "=== 1. 程式碼品質檢查 ==="
echo "執行 flake8 檢查..."
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
FLAKE8_EXIT=$?

echo ""
echo "=== 2. 程式碼格式化檢查 ==="
echo "執行 black 檢查..."
black --check --diff .
BLACK_EXIT=$?

echo ""
echo "=== 3. 型別檢查 ==="
echo "執行 mypy 檢查..."
mypy . --ignore-missing-imports
MYPY_EXIT=$?

echo ""
echo "=== 4. 單元測試 ==="
echo "執行 pytest..."
pytest tests/ -v --cov=. --cov-report=term-missing
PYTEST_EXIT=$?

echo ""
echo "=== 5. Shiv 打包測試 ==="
echo "測試 VIP 輪盤打包..."
PYTHONPATH=. shiv --compressed --compile-pyc -o roulette-vip.pyz -e main_vip:main .
SHIV_EXIT=$?

if [ $SHIV_EXIT -eq 0 ]; then
    echo "✅ VIP 輪盤打包成功"
    
    echo "驗證打包檔案..."
    python -c "import zipimport; z = zipimport.zipimporter('roulette-vip.pyz'); print('✅ 打包檔案驗證成功')"
    VALIDATION_EXIT=$?
else
    echo "❌ VIP 輪盤打包失敗"
    VALIDATION_EXIT=1
fi

echo ""
echo "=== 測試結果總結 ==="
echo "flake8: $([ $FLAKE8_EXIT -eq 0 ] && echo '✅ 通過' || echo '❌ 失敗')"
echo "black:  $([ $BLACK_EXIT -eq 0 ] && echo '✅ 通過' || echo '❌ 失敗')"
echo "mypy:   $([ $MYPY_EXIT -eq 0 ] && echo '✅ 通過' || echo '❌ 失敗')"
echo "pytest: $([ $PYTEST_EXIT -eq 0 ] && echo '✅ 通過' || echo '❌ 失敗')"
echo "shiv:   $([ $SHIV_EXIT -eq 0 ] && echo '✅ 通過' || echo '❌ 失敗')"
echo "驗證:   $([ $VALIDATION_EXIT -eq 0 ] && echo '✅ 通過' || echo '❌ 失敗')"

# 計算總體結果
TOTAL_EXIT=$((FLAKE8_EXIT + BLACK_EXIT + MYPY_EXIT + PYTEST_EXIT + SHIV_EXIT + VALIDATION_EXIT))

if [ $TOTAL_EXIT -eq 0 ]; then
    echo ""
    echo "🎉 所有測試都通過了！"
    exit 0
else
    echo ""
    echo "❌ 有 $TOTAL_EXIT 個測試失敗"
    exit 1
fi