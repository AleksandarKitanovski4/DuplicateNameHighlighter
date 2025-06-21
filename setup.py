from setuptools import setup, find_packages

setup(
    name='DuplicateNameHighlighter',
    version='1.0.0',
    description='Real-time duplicate name highlighter with OCR and overlay',
    author='Your Name',
    packages=find_packages(include=['core', 'gui', 'utils', 'core.*', 'gui.*', 'utils.*']),
    install_requires=[
        'PyQt5>=5.15.0',
        'pillow>=9.0.0',
        'pytesseract>=0.3.10',
        'opencv-python>=4.5.0.62',
        'imagehash>=4.2.1',
        'pyautogui>=0.9.53',
        'numpy>=1.21.0',
    ],
    entry_points={
        'console_scripts': [
            'duplicate-name-highlighter = main:main',
        ],
    },
    include_package_data=True,
    package_data={
        '': ['*.json', '*.db', '*.png', '*.ico'],
    },
    python_requires='>=3.7',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
) 