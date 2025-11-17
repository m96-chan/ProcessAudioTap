# Experimental macOS Backends

**WARNING**: The implementations in this directory are EXPERIMENTAL and NOT RECOMMENDED for production use.

## Official macOS Backend

The official and recommended macOS backend is **PyObjC** (`macos_pyobjc.py` in `backends/`).

## Experimental Implementations

This directory contains experimental approaches that were explored but are not currently supported:

### 1. Swift CLI Helper (`macos_swift_cli.py`)
- **Status**: Experimental - Has stability issues
- **Approach**: External Swift binary using Core Audio Process Tap
- **Issues**: AudioDeviceStart fails with OSStatus 1852797029 ("nope") error
- **Files**:
  - `macos_swift_cli.py` - Python wrapper
  - `../../swift/proctap-macos/` - Swift CLI helper source

### 2. Native C Extension (`macos_c_extension.py`, `_native_macos.m`)
- **Status**: Work in Progress - Incomplete
- **Approach**: Direct Core Audio C API via Python C extension
- **Issues**: Aggregate device tap reference not working
- **Goal**: Sub-500ms latency (Phase 4 roadmap)
- **Files**:
  - `macos_c_extension.py` - Python wrapper
  - `_native_macos.m` - Objective-C implementation

## Why PyObjC is Recommended

✅ **Verified working** - Successfully captures process audio  
✅ **Direct Python integration** - No subprocess overhead  
✅ **Simple deployment** - Just `pip install pyobjc-*`  
✅ **Better error handling** - Python exceptions vs parsing stderr  
✅ **No binary dependencies** - No Swift toolchain required  

## Future Work (Phase 4)

C extension optimization remains a potential future enhancement for ultra-low latency requirements, but is not a priority for general use.

---

**Last Updated**: 2025-11-18  
**Decision**: Adopt PyObjC as official backend (Phase 3)
