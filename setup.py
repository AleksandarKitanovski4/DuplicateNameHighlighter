from setuptools import setup, find_packages

setup(
    name='DuplicateNameHighlighter',
    version='0.2.0',
    description='Real-time duplicate name highlighter with OCR and overlay',
    author='Your Name',
    packages=find_packages(include=['core', 'gui', 'utils', 'core.*', 'gui.*', 'utils.*']),
    install_requires=[
        'PyQt5>=5.15.0',
        'numpy',
        'opencv-python',
        'pillow',
        'pyautogui',
        'imagehash',
        'pytesseract',
        'pytesseract>=0.3.10',
        'opencv-python>=4.5.0.62',
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