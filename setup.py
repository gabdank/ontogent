from setuptools import setup, find_packages

setup(
    name="ontogent",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "anthropic>=0.6.0",
        "langchain>=0.0.267",
        "pydantic>=2.0.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "ontogent=src.main:main",
        ],
    },
) 