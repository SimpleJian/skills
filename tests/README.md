# 技能模块单元测试

## 测试覆盖范围

### 基础设施测试

| 测试文件 | 测试内容 | 关键测试点 |
|---------|---------|-----------|
| `test_data_quality.py` | 数据质量模块 | 除权检测、停牌标记、波动率计算、期货到期检查 |
| `test_risk_tags.py` | 风险标签模块 | 标签分类、风险等级、标签字符串生成 |
| `test_financial_cache.py` | 财务缓存模块 | 缓存存取、过期检查、增量更新、缓存清理 |
| `test_path_independence.py` | 路径独立性检查 | 检测硬编码绝对路径 |

### 技能模块测试

| 测试文件 | 测试内容 | 关键测试点 |
|---------|---------|-----------|
| `test_macro_analysis.py` | 宏观分析技能 | 经济周期判断、宏观指标获取、资产配置 |
| `test_portfolio_manager.py` | 组合管理技能 | 组合分析、相关性监控、再平衡建议 |
| `test_risk_manager.py` | 风险管理技能 | 止损扫描、VaR计算、凯利公式 |
| `test_financial_analyzer.py` | 财务分析技能 | 杜邦分析、财务质量评分 |
| `test_industry_research.py` | 行业研究技能 | 行业表现、行业轮动、波特五力 |
| `test_fund_analyzer.py` | 基金分析技能 | 基金筛选、业绩分析、持仓穿透 |

## 运行测试

### 方法1：使用测试运行脚本（推荐）

```bash
cd /path/to/skills

# 运行所有测试
python tests/run_tests.py

# 详细输出
python tests/run_tests.py -v

# 只运行特定测试
python tests/run_tests.py -k test_check_price_data

# 简洁输出
python tests/run_tests.py -q
```

### 方法2：使用 pytest

```bash
cd /path/to/skills

# 运行所有测试
python -m pytest tests/ -v

# 运行单个测试文件
python -m pytest tests/test_data_quality.py -v

# 运行单个测试类
python -m pytest tests/test_risk_tags.py::TestRiskTagGenerator -v

# 运行单个测试方法
python -m pytest tests/test_data_quality.py::TestDataQualityChecker::test_check_price_data_normal -v
```

### 方法3：使用 unittest

```bash
cd /path/to/skills

# 运行所有测试
python -m unittest discover tests/ -v

# 运行单个测试文件
python -m unittest tests.test_data_quality -v

# 运行单个测试类
python -m unittest tests.test_risk_tags.TestRiskTagGenerator -v
```

## 测试结构

```
tests/
├── __init__.py                 # 测试包初始化
├── README.md                   # 本文件
├── run_tests.py                # 测试运行脚本
├── test_data_quality.py        # 数据质量模块测试 (14个)
├── test_risk_tags.py           # 风险标签模块测试 (14个)
├── test_financial_cache.py     # 财务缓存模块测试 (11个)
├── test_path_independence.py   # 路径独立性检查 + SKILL.md 存在性检查 (18个)
├── test_macro_analysis.py      # 宏观分析技能测试 (12个)
├── test_portfolio_manager.py   # 组合管理技能测试 (4个)
├── test_risk_manager.py        # 风险管理技能测试 (6个)
├── test_financial_analyzer.py  # 财务分析技能测试 (3个)
├── test_industry_research.py   # 行业研究技能测试 (3个)
└── test_fund_analyzer.py       # 基金分析技能测试 (3个)

总计: 10个测试文件，88个测试用例
```

## 添加新测试

1. 创建测试文件，命名格式：`test_<module_name>.py`
2. 继承 `unittest.TestCase`
3. 测试方法命名：`test_<功能>_<场景>`
4. 使用 `setUp` 和 `tearDown` 进行初始化和清理

### 示例

```python
import unittest
import sys
import os

# 添加 skills 目录到路径
_current_dir = os.path.dirname(os.path.abspath(__file__))
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

from your_module import YourClass

class TestYourClass(unittest.TestCase):
    def setUp(self):
        """测试前初始化"""
        self.obj = YourClass()
    
    def test_feature_normal(self):
        """测试正常场景"""
        result = self.obj.do_something()
        self.assertEqual(result, expected_value)
    
    def test_feature_edge_case(self):
        """测试边界条件"""
        result = self.obj.do_something(edge_input)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
```

## 路径独立性与文档完整性检查

所有 skill 模块必须避免硬编码的绝对路径，且必须有对应的文档。

```bash
# 检查所有技能模块
python -m unittest tests.test_path_independence -v
```

### 检测内容

#### 1. SKILL.md 存在性检查

每个技能目录必须包含 `SKILL.md` 文件：

```bash
# 检查所有技能是否有文档
python -m unittest tests.test_path_independence.TestPathIndependence.test_all_skills_have_md_file
```

#### 2. 硬编码路径检查

测试会检查是否包含特定用户名（如 `lijian`）的硬编码路径。

### 正确的动态路径获取方式

```python
# ✅ 正确：使用动态路径
_current_file = os.path.abspath(__file__)
_current_dir = os.path.dirname(_current_file)
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)

# ❌ 错误：硬编码路径
sys.path.insert(0, '/path/to/skills')
```

## 持续集成建议

在每次修改代码后，建议运行：

```bash
# 1. 运行单元测试
python tests/run_tests.py

# 2. 运行路径独立性检查
python -m unittest tests.test_path_independence

# 3. 运行语法检查
python -m py_compile tushare_utils/*.py
python -m py_compile a_share_trend/*.py
python -m py_compile a_share_value/*.py
python -m py_compile futures_trend/*.py
python -m py_compile futures_value/*.py

# 3. 检查导入
python -c "from tushare_utils.data_quality import DataPreprocessor; print('✓ 导入成功')"
```

## 常见问题

### 1. ImportError: No module named 'tushare_utils'

确保在 skills 目录下运行测试，或者设置 PYTHONPATH：

```bash
export PYTHONPATH=/path/to/skills:$PYTHONPATH
python tests/run_tests.py
```

### 2. 测试失败但代码没问题

可能是测试数据需要更新。检查：
- 测试数据是否模拟了真实情况
- 日期相关测试是否需要调整

### 3. 缓存测试失败

缓存测试使用临时目录，如果测试中断可能导致临时文件残留。手动清理：

```bash
rm -rf /tmp/test_cache_*
```

## 测试覆盖率

要生成测试覆盖率报告：

```bash
# 安装 coverage
pip install pytest-cov

# 生成报告
python -m pytest tests/ --cov=tushare_utils --cov-report=html

# 查看报告
open htmlcov/index.html
```

## 维护建议

1. **每次修改后运行测试**：确保没有破坏现有功能
2. **添加新功能时添加测试**：保持测试覆盖率
3. **定期更新测试数据**：特别是日期相关的测试
4. **保持测试独立**：每个测试应该能独立运行
