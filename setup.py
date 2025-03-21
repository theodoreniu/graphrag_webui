from setuptools import setup, find_packages

setup(
    name='graphrag_webui',
    version='2.1.0',
    description='A web interface for GraphRAG.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Theodoree',
    author_email='theodore.niu@gmail.com',
    url='https://github.com/theodoreniu/graphrag_webui',
    packages=find_packages(),
    install_requires=[
        'click',
    ],
    entry_points={
        'console_scripts': [
            'graphrag_webui = cli.main:main',
            'graphrag-webui = cli.main:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
