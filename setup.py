#!/usr/bin/env python3
"""
Setup script for Studio SDP Roulette System
This script helps shiv properly package all modules and dependencies
"""

from setuptools import setup, find_packages


# Read requirements from requirements.txt
def read_requirements():
    """Read requirements from requirements.txt file."""
    with open("requirements.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


# Read README for long description
def read_readme():
    """Read README.md file for long description."""
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()


setup(
    name="studio_sdp_roulette",
    version="1.0.0",
    description="SDP Game System with Roulette, SicBo, and Baccarat Controllers",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Studio SDP Team",
    author_email="team@studio-sdp.com",
    url="https://github.com/studio-sdp/studio-sdp-roulette",
    packages=find_packages(
        include=["*"], exclude=["tests*", "setup*", "proto*", "self_test*"]
    ),
    include_package_data=True,
    python_requires=">=3.12",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "sdp-vip=main_vip:main",
            "sdp-speed=main_speed:main",
            "sdp-sicbo=main_sicbo:main",
            "sdp-baccarat=main_baccarat:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Topic :: Games/Entertainment",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    zip_safe=False,
)
