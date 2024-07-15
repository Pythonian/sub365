"""Project setup configuration."""

from setuptools import find_packages, setup

setup(
    name="sub365",
    version="1.0",
    packages=find_packages(include=["accounts", "config"]),
)
