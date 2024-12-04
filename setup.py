import setuptools

setuptools.setup(
    name="LM scraper",
    version="0.1",
    author="yochi",
    author_email="pedrogush@gmail.com",
    description="scraper for the website ligamagic",
    packages=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: Windows"
    ],
    python_requires=">=3.11",
    install_requires=[
        "requests",
        "opencv-python>=4.0",
        "tqdm",
        "numpy",
        "pillow",
        "bs4",
        "lxml",
        'loguru',
        'pydantic',
        'psutil',
        'fire',
        "pytesseract",
        "curl_cffi",
        "pymongo",
    ]
)