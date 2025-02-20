from setuptools import setup, find_packages

setup(
    name="log-reader",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "reader": [
            "data/IP2LOCATION-LITE-DB11.BIN"
        ],  # 包含reader包内的数据文件
    },
    # 添加示例文件
    data_files=[
        ("example", ["example/access.log"]),
    ],
    install_requires=[
        "streamlit>=1.31.0",
        "pandas>=2.0.0",
        "folium>=0.14.0",
        "plotly>=5.18.0",
        "IP2Location>=8.10.0",
        "numpy>=1.24.0",
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "reader=reader.cli:main",
        ],
    },
    author="s045pd",
    author_email="s045pd.x@gmail.com",
    description="A visualization tool for access log analysis",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/s045pd/log-reader",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
