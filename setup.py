from setuptools import setup, find_packages

setup(
    name="ai-job-pipeline",
    version="1.0.0",
    description="AI-powered job search pipeline — scrape, score, tailor resumes, export to Excel",
    author="Parth Parmar",
    author_email="m2parthparmar@gmail.com",
    url="https://github.com/parth-r-parmar/ai-job-pipeline",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "anthropic>=0.40.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "openpyxl>=3.1.0",
        "lxml>=5.0.0",
        "fake-useragent>=1.5.0",
        "fpdf2>=2.8.0",
        "python-dotenv>=1.0.0",
    ],
)
