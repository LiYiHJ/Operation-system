#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V5.1 跨境电商智能运营系统 - 安装配置
"""

from setuptools import setup, find_packages

setup(
    name="ecom-v51",
    version="5.1.0",
    description="V5.1 跨境电商智能运营系统 - SKU 运营分析和策略推荐",
    author="Your Team",
    author_email="team@example.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pandas>=1.5.0",
        "pytest>=7.0.0",
    ],
    entry_points={
        "console_scripts": [
            "v51-ops=ecom_v51.cli:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
