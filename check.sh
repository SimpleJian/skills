#!/bin/bash
# 快速检查脚本
# 用法: ./check.sh

echo "=========================================="
echo "Skills 代码检查"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查点计数
PASSED=0
FAILED=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo "[1/4] 检查 Python 语法..."
SYNTAX_OK=true
for file in tushare_utils/*.py a_share_trend/*.py a_share_value/*.py futures_trend/*.py futures_value/*.py; do
    if ! python -m py_compile "$file" 2>/dev/null; then
        check_fail "语法错误: $file"
        SYNTAX_OK=false
    fi
done

if $SYNTAX_OK; then
    check_pass "所有文件语法正确"
fi

echo ""
echo "[2/4] 运行单元测试..."
if python tests/run_tests.py -q 2>&1 | grep -q "^OK"; then
    check_pass "所有测试通过"
else
    check_fail "部分测试失败，运行 'python tests/run_tests.py -v' 查看详情"
fi

echo ""
echo "[3/4] 检查关键导入..."
IMPORT_OK=true
python -c "from tushare_utils.data_quality import DataPreprocessor" 2>/dev/null || { check_fail "无法导入 data_quality"; IMPORT_OK=false; }
python -c "from tushare_utils.risk_tags import RiskTagGenerator" 2>/dev/null || { check_fail "无法导入 risk_tags"; IMPORT_OK=false; }
python -c "from tushare_utils.api_utils import FinancialDataCache" 2>/dev/null || { check_fail "无法导入 FinancialDataCache"; IMPORT_OK=false; }

if $IMPORT_OK; then
    check_pass "关键模块导入正常"
fi

echo ""
echo "[4/4] 检查缓存目录..."
CACHE_DIR="$HOME/.cache/tushare/financial"
if [ -d "$CACHE_DIR" ]; then
    CACHE_SIZE=$(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1)
    FILE_COUNT=$(ls -1 "$CACHE_DIR"/*.csv 2>/dev/null | wc -l)
    check_pass "缓存目录存在 ($FILE_COUNT 个文件, $CACHE_SIZE)"
else
    check_warn "缓存目录不存在，将在首次运行时创建"
fi

echo ""
echo "=========================================="
echo "检查结果: $PASSED 通过, $FAILED 失败"
echo "=========================================="

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ 所有检查通过${NC}"
    exit 0
else
    echo -e "${RED}✗ 部分检查失败，请修复后重试${NC}"
    exit 1
fi
