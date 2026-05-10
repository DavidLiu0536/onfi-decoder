from setuptools import setup, find_packages

setup(
    name='onfi-decoder',
    version='0.1.0',
    description='Open NAND Flash Interface (ONFI) protocol decoder for logic analyzer captures',
    long_description=open('README.md').read() if __import__('os').path.exists('README.md') else '',
    long_description_content_type='text/markdown',
    author='DavidLiu0536',
    url='https://github.com/DavidLiu0536/onfi-decoder',
    license='MIT',
    packages=find_packages(),
    install_requires=[
        'matplotlib>=3.5',
    ],
    entry_points={
        'console_scripts': [
            'onfi-decode = onfi_decoder.cli:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)',
    ],
    python_requires='>=3.8',
)
