#!/usr/bin/env python3
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="wfbinstaller",
    version="1.0.0",
    author="wfbInstaller Contributors",
    description="Garmin Watchface Installer for Garmin devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/joshuahxh/wfbInstaller",
    packages=find_packages(),
    py_modules=[
        "main",
        "models",
        "logger",
        "device_service",
        "file_handler",
        "download_service",
        "app_installer"
    ],
    entry_points={
        "console_scripts": [
            "wfbinstaller=main:main",
        ],
    },
    install_requires=[
        "python-libmtp>=1.1.19",
        "requests>=2.31.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Utilities",
    ],
    python_requires=">=3.7",
)
