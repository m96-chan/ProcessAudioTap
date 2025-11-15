from setuptools import setup, Extension
from setuptools import find_packages
import sys
import platform

# Platform-specific extension modules
ext_modules = []

# Build native extension only on Windows
if platform.system() == "Windows":
    ext_modules = [
        Extension(
            "proctap._native",
            sources=["src/proctap/_native.cpp"],
            language="c++",
            extra_compile_args=["/std:c++20", "/EHsc", '/utf-8'] if sys.platform == 'win32' else [],
            libraries=[
                'ole32', 'uuid', 'propsys'
                # CoInitializeEx, CoCreateInstance, CoTaskMemAlloc/Free など
                # "Avrt",   # 将来、AVRT 系の API (AvSetMmThreadCharacteristicsW 等) を使うなら追加
                # "Mmdevapi", # 今は LoadLibrary で動的ロードなので必須ではない
            ],
        )
    ]
    print("Building with Windows WASAPI backend (C++ extension)")

elif platform.system() == "Linux":
    # Linux: No native extension yet, pure Python backend (under development)
    print("Building for Linux (backend under development - limited functionality)")
    print("NOTE: Process-specific audio capture is not yet implemented on Linux")

elif platform.system() == "Darwin":  # macOS
    # macOS: No native extension yet, pure Python backend (planned)
    print("Building for macOS (backend not implemented)")
    print("WARNING: macOS support is planned but not yet available")

else:
    print(f"WARNING: Platform '{platform.system()}' is not officially supported")
    print("The package will install but audio capture will not work")

setup(
    name="proc-tap",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    ext_modules=ext_modules,
)