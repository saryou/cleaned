import setuptools
import re

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
with open("cleaned/version.py", "r", encoding="utf-8") as fh:
    version = re.match("VERSION = '(.*)'", fh.read()).groups()[0]

setuptools.setup(
    name="cleand",
    version=version,
    author="Ryosuke Sasaki",
    author_email="saryou.ssk@gmail.com",
    description="a declarative data validator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/saryou/cleaned",
    project_urls={
        "Bug Tracker": "https://github.com/saryou/cleaned/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=["cleaned"],
    package_dir={"cleaned": "cleaned"},
    python_requires=">=3.8",
)
