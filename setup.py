from setuptools import setup, find_packages

setup(
    name="py-appsheet",
    version="0.1.0",
    description="A no-frills Python library for interacting with the Google AppSheet API.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Scott Novich",
    author_email="scott.novich@gmail.com",
    url="https://github.com/greatscott/py-appsheet",
    license="MIT",
    packages=find_packages(include=["py_appsheet", "py_appsheet.*"]),
    install_requires=[
        "requests>=2.0.0",
    ],
    python_requires=">=3.7",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
