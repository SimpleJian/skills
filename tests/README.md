# 技能模块单元测试

## 测试覆盖范围

| 测试文件 | 测试内容 | 关键测试点 |
|---------|---------|-----------|
| `test_data_quality.py` | 数据质量模块 | 除权检测、停牌标记、波动率计算、期货到期检查 |
| `test_risk_tags.py` | 风险标签模块 | 标签分类、风险等级、标签字符串生成 |
| `test_financial_cache.py` | 财务缓存模块 | 缓存存取、过期检查、增量更新、缓存清理 |

## 运行测试

### 方法1：使用测试运行脚本（推荐）

```bash
cd /Users/lijian/.agents/skills

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
cd /Users/lijian/.agents/skills

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
cd /Users/lijian/.agents/skills

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
├── __init__.py              # 测试包初始化
├── README.md                # 本文件
├── run_tests.py             # 测试运行脚本
├── test_data_quality.py     # 数据质量模块测试
├── test_risk_tags.py        # 风险标签模块测试
└── test_financial_cache.py  # 财务缓存模块测试
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

## 持续集成建议

在每次修改代码后，建议运行：

```bash
# 1. 运行单元测试
python tests/run_tests.py

# 2. 运行语法检查
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
export PYTHONPATH=/Users/lijian/.agents/skills:$PYTHONPATH
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
