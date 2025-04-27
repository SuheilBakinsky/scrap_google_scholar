#!/usr/bin/env python
"""
Setup script for Scholar Scraper.
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="scholar_scraper",
    version="0.2.0",
    author="ScholarScraper Team",
    description="Search academic databases and summarize papers with Gemini",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/username/scholar_scraper",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "scholar-scraper=scholar_scraper.cli:run_cli",
        ],
    },
)
