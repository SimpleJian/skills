#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径独立性测试

检测所有 skill 模块是否包含硬编码的绝对路径依赖。
"""

import unittest
import os
import re
import sys

_current_dir = os.path.dirname(os.path.abspath(__file__))
_skills_dir = os.path.dirname(_current_dir)
sys.path.insert(0, _skills_dir)


class TestPathIndependence(unittest.TestCase):
    """测试路径独立性"""
    
    def setUp(self):
        """设置测试环境"""
        self.skills_dir = _skills_dir
        # 需要检查的 skill 目录
        self.skill_dirs = [
            'a_share_trend', 'a_share_value',
            'futures_trend', 'futures_value',
            'macro_analysis', 'portfolio_manager', 'risk_manager',
            'financial_analyzer', 'industry_research', 'fund_analyzer',
            'tushare_utils'
        ]
        # 硬编码用户名（核心检测目标）
        self.forbidden_username = 'lijian'
        # 允许的路径占位符
        self.allowed_placeholders = [
            '/path/to', '/your/path', '<your_path>', 
            '/home/username', '/Users/username'
        ]
    
    def _check_file_for_hardcoded_paths(self, filepath):
        """
        检查文件是否包含硬编码路径（检测特定用户名'lijian'）
        
        Returns:
            (bool, list) - (是否干净, 发现的问题列表)
        """
        issues = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except:
            return True, []
        
        for line_num, line in enumerate(lines, 1):
            # 检查是否包含硬编码用户名'lijian'
            if self.forbidden_username in line:
                # 检查是否是动态路径获取（使用__file__）
                if '__file__' in line or 'os.path' in line:
                    continue
                # 检查是否是允许的占位符
                if any(placeholder in line for placeholder in self.allowed_placeholders):
                    continue
                # 检查是否是文档中的说明（包含"检测"、"如"等关键词）
                if any(kw in line for kw in ['检测', '如', '说明', '例如']):
                    continue
                issues.append({
                    'line': line_num,
                    'content': line.strip(),
                    'pattern': self.forbidden_username
                })
        
        return len(issues) == 0, issues
    
    def test_a_share_trend_no_hardcoded_paths(self):
        """测试 a_share_trend 无硬编码路径"""
        skill_dir = os.path.join(self.skills_dir, 'a_share_trend')
        issues_found = []
        
        for filename in os.listdir(skill_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(skill_dir, filename)
                is_clean, issues = self._check_file_for_hardcoded_paths(filepath)
                if not is_clean:
                    issues_found.extend(issues)
        
        if issues_found:
            error_msg = f"发现 {len(issues_found)} 个硬编码路径:\n"
            for issue in issues_found[:5]:  # 最多显示5个
                error_msg += f"  第{issue['line']}行: {issue['content'][:60]}...\n"
            self.fail(error_msg)
    
    def test_a_share_value_no_hardcoded_paths(self):
        """测试 a_share_value 无硬编码路径"""
        skill_dir = os.path.join(self.skills_dir, 'a_share_value')
        issues_found = []
        
        for filename in os.listdir(skill_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(skill_dir, filename)
                is_clean, issues = self._check_file_for_hardcoded_paths(filepath)
                if not is_clean:
                    issues_found.extend(issues)
        
        self.assertEqual(len(issues_found), 0, 
                        f"发现 {len(issues_found)} 个硬编码路径")
    
    def test_futures_trend_no_hardcoded_paths(self):
        """测试 futures_trend 无硬编码路径"""
        skill_dir = os.path.join(self.skills_dir, 'futures_trend')
        issues_found = []
        
        for filename in os.listdir(skill_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(skill_dir, filename)
                is_clean, issues = self._check_file_for_hardcoded_paths(filepath)
                if not is_clean:
                    issues_found.extend(issues)
        
        self.assertEqual(len(issues_found), 0, 
                        f"发现 {len(issues_found)} 个硬编码路径")
    
    def test_futures_value_no_hardcoded_paths(self):
        """测试 futures_value 无硬编码路径"""
        skill_dir = os.path.join(self.skills_dir, 'futures_value')
        issues_found = []
        
        for filename in os.listdir(skill_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(skill_dir, filename)
                is_clean, issues = self._check_file_for_hardcoded_paths(filepath)
                if not is_clean:
                    issues_found.extend(issues)
        
        self.assertEqual(len(issues_found), 0, 
                        f"发现 {len(issues_found)} 个硬编码路径")
    
    def test_macro_analysis_no_hardcoded_paths(self):
        """测试 macro_analysis 无硬编码路径"""
        skill_dir = os.path.join(self.skills_dir, 'macro_analysis')
        issues_found = []
        
        for filename in os.listdir(skill_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(skill_dir, filename)
                is_clean, issues = self._check_file_for_hardcoded_paths(filepath)
                if not is_clean:
                    issues_found.extend(issues)
        
        self.assertEqual(len(issues_found), 0, 
                        f"发现 {len(issues_found)} 个硬编码路径")
    
    def test_portfolio_manager_no_hardcoded_paths(self):
        """测试 portfolio_manager 无硬编码路径"""
        skill_dir = os.path.join(self.skills_dir, 'portfolio_manager')
        issues_found = []
        
        for filename in os.listdir(skill_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(skill_dir, filename)
                is_clean, issues = self._check_file_for_hardcoded_paths(filepath)
                if not is_clean:
                    issues_found.extend(issues)
        
        self.assertEqual(len(issues_found), 0, 
                        f"发现 {len(issues_found)} 个硬编码路径")
    
    def test_risk_manager_no_hardcoded_paths(self):
        """测试 risk_manager 无硬编码路径"""
        skill_dir = os.path.join(self.skills_dir, 'risk_manager')
        issues_found = []
        
        for filename in os.listdir(skill_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(skill_dir, filename)
                is_clean, issues = self._check_file_for_hardcoded_paths(filepath)
                if not is_clean:
                    issues_found.extend(issues)
        
        self.assertEqual(len(issues_found), 0, 
                        f"发现 {len(issues_found)} 个硬编码路径")
    
    def test_financial_analyzer_no_hardcoded_paths(self):
        """测试 financial_analyzer 无硬编码路径"""
        skill_dir = os.path.join(self.skills_dir, 'financial_analyzer')
        issues_found = []
        
        for filename in os.listdir(skill_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(skill_dir, filename)
                is_clean, issues = self._check_file_for_hardcoded_paths(filepath)
                if not is_clean:
                    issues_found.extend(issues)
        
        self.assertEqual(len(issues_found), 0, 
                        f"发现 {len(issues_found)} 个硬编码路径")
    
    def test_industry_research_no_hardcoded_paths(self):
        """测试 industry_research 无硬编码路径"""
        skill_dir = os.path.join(self.skills_dir, 'industry_research')
        issues_found = []
        
        for filename in os.listdir(skill_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(skill_dir, filename)
                is_clean, issues = self._check_file_for_hardcoded_paths(filepath)
                if not is_clean:
                    issues_found.extend(issues)
        
        self.assertEqual(len(issues_found), 0, 
                        f"发现 {len(issues_found)} 个硬编码路径")
    
    def test_fund_analyzer_no_hardcoded_paths(self):
        """测试 fund_analyzer 无硬编码路径"""
        skill_dir = os.path.join(self.skills_dir, 'fund_analyzer')
        issues_found = []
        
        for filename in os.listdir(skill_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(skill_dir, filename)
                is_clean, issues = self._check_file_for_hardcoded_paths(filepath)
                if not is_clean:
                    issues_found.extend(issues)
        
        self.assertEqual(len(issues_found), 0, 
                        f"发现 {len(issues_found)} 个硬编码路径")
    
    def test_tushare_utils_no_hardcoded_paths(self):
        """测试 tushare_utils 无硬编码路径"""
        skill_dir = os.path.join(self.skills_dir, 'tushare_utils')
        issues_found = []
        
        for filename in os.listdir(skill_dir):
            if filename.endswith('.py'):
                filepath = os.path.join(skill_dir, filename)
                is_clean, issues = self._check_file_for_hardcoded_paths(filepath)
                if not is_clean:
                    issues_found.extend(issues)
        
        self.assertEqual(len(issues_found), 0, 
                        f"发现 {len(issues_found)} 个硬编码路径")
    
    def test_all_skills_have_md_file(self):
        """测试所有技能都有对应的 SKILL.md 文件"""
        missing_md = []
        
        for skill_dir_name in self.skill_dirs:
            skill_dir = os.path.join(self.skills_dir, skill_dir_name)
            md_filepath = os.path.join(skill_dir, 'SKILL.md')
            
            if not os.path.exists(md_filepath):
                missing_md.append(skill_dir_name)
        
        if missing_md:
            error_msg = f"以下 {len(missing_md)} 个技能缺少 SKILL.md 文件:\n"
            for skill in missing_md:
                error_msg += f"  - {skill}/SKILL.md\n"
            error_msg += "\n请为每个技能创建对应的 SKILL.md 文档"
            self.fail(error_msg)
    
    def test_all_skill_md_files_no_hardcoded_paths(self):
        """测试所有 SKILL.md 文件无硬编码路径"""
        issues_found = []
        
        for skill_dir_name in self.skill_dirs:
            skill_dir = os.path.join(self.skills_dir, skill_dir_name)
            md_filepath = os.path.join(skill_dir, 'SKILL.md')
            
            if os.path.exists(md_filepath):
                is_clean, issues = self._check_file_for_hardcoded_paths(md_filepath)
                if not is_clean:
                    issues_found.append({
                        'skill': skill_dir_name,
                        'issues': issues
                    })
        
        if issues_found:
            error_msg = f"发现 {len(issues_found)} 个 SKILL.md 文件包含硬编码路径:\n"
            for item in issues_found:
                error_msg += f"\n【{item['skill']}/SKILL.md】\n"
                for issue in item['issues'][:3]:  # 每个文件最多显示3个
                    error_msg += f"  第{issue['line']}行: {issue['content'][:60]}...\n"
            self.fail(error_msg)
    
    def test_tests_readme_no_hardcoded_paths(self):
        """测试 tests/README.md 无硬编码路径"""
        readme_path = os.path.join(self.skills_dir, 'tests', 'README.md')
        
        if os.path.exists(readme_path):
            is_clean, issues = self._check_file_for_hardcoded_paths(readme_path)
            
            if not is_clean:
                error_msg = "tests/README.md 包含硬编码路径:\n"
                for issue in issues[:5]:
                    error_msg += f"  第{issue['line']}行: {issue['content'][:60]}...\n"
                self.fail(error_msg)
    
    def test_root_readme_no_hardcoded_paths(self):
        """测试根目录 README.md 无硬编码路径"""
        readme_path = os.path.join(self.skills_dir, 'README.md')
        
        if os.path.exists(readme_path):
            is_clean, issues = self._check_file_for_hardcoded_paths(readme_path)
            
            if not is_clean:
                error_msg = "README.md 包含硬编码路径:\n"
                for issue in issues[:5]:
                    error_msg += f"  第{issue['line']}行: {issue['content'][:60]}...\n"
                self.fail(error_msg)
    
    def test_changelog_no_hardcoded_paths(self):
        """测试 CHANGELOG.md 无硬编码路径"""
        changelog_path = os.path.join(self.skills_dir, 'CHANGELOG.md')
        
        if os.path.exists(changelog_path):
            is_clean, issues = self._check_file_for_hardcoded_paths(changelog_path)
            
            if not is_clean:
                error_msg = "CHANGELOG.md 包含硬编码路径:\n"
                for issue in issues[:5]:
                    error_msg += f"  第{issue['line']}行: {issue['content'][:60]}...\n"
                self.fail(error_msg)
    
    def test_investment_guide_no_hardcoded_paths(self):
        """测试 INVESTMENT_SKILLS_GUIDE.md 无硬编码路径"""
        guide_path = os.path.join(self.skills_dir, 'INVESTMENT_SKILLS_GUIDE.md')
        
        if os.path.exists(guide_path):
            is_clean, issues = self._check_file_for_hardcoded_paths(guide_path)
            
            if not is_clean:
                error_msg = "INVESTMENT_SKILLS_GUIDE.md 包含硬编码路径:\n"
                for issue in issues[:5]:
                    error_msg += f"  第{issue['line']}行: {issue['content'][:60]}...\n"
                self.fail(error_msg)
    
    def test_tests_init_no_hardcoded_paths(self):
        """测试 tests/__init__.py 无硬编码路径"""
        init_path = os.path.join(self.skills_dir, 'tests', '__init__.py')
        
        if os.path.exists(init_path):
            is_clean, issues = self._check_file_for_hardcoded_paths(init_path)
            
            if not is_clean:
                error_msg = "tests/__init__.py 包含硬编码路径:\n"
                for issue in issues[:5]:
                    error_msg += f"  第{issue['line']}行: {issue['content'][:60]}...\n"
                self.fail(error_msg)


if __name__ == '__main__':
    unittest.main()
