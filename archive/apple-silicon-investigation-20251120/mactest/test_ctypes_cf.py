#!/usr/bin/env python3.12
"""Test ctypes Core Foundation bindings step by step."""

import sys
import logging

logging.basicConfig(level=logging.DEBUG)

sys.path.insert(0, "src")

from proctap.backends import macos_coreaudio_ctypes as ca_ctypes

print("Testing Core Foundation ctypes bindings...")
print("=" * 70)

# Test 1: CFString creation
print("\nTest 1: Creating CFString...")
try:
    cf_string = ca_ctypes.CFStringCreateWithCString(None, b"test", ca_ctypes.kCFStringEncodingUTF8)
    print(f"✓ CFString created: {cf_string}")
    ca_ctypes.CFRelease(cf_string)
    print("✓ CFString released")
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 2: CFNumber creation
print("\nTest 2: Creating CFNumber...")
try:
    import ctypes
    value = ctypes.c_int32(42)
    cf_number = ca_ctypes.CFNumberCreate(None, ca_ctypes.kCFNumberSInt32Type, ctypes.byref(value))
    print(f"✓ CFNumber created: {cf_number}")
    ca_ctypes.CFRelease(cf_number)
    print("✓ CFNumber released")
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 3: CFArray creation
print("\nTest 3: Creating CFArray...")
try:
    import ctypes

    # Create array of CFStrings
    cf_str1 = ca_ctypes.CFStringCreateWithCString(None, b"item1", ca_ctypes.kCFStringEncodingUTF8)
    cf_str2 = ca_ctypes.CFStringCreateWithCString(None, b"item2", ca_ctypes.kCFStringEncodingUTF8)

    items = (ca_ctypes.CFTypeRef * 2)(cf_str1, cf_str2)
    cf_array = ca_ctypes.CFArrayCreate(None, items, 2, ca_ctypes.get_cf_type_array_callbacks())

    print(f"✓ CFArray created: {cf_array}")

    ca_ctypes.CFRelease(cf_array)
    ca_ctypes.CFRelease(cf_str1)
    ca_ctypes.CFRelease(cf_str2)
    print("✓ CFArray and items released")
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 4: CFDictionary creation (simple)
print("\nTest 4: Creating simple CFDictionary...")
try:
    import ctypes

    key = ca_ctypes.CFStringCreateWithCString(None, b"test_key", ca_ctypes.kCFStringEncodingUTF8)
    value = ca_ctypes.CFStringCreateWithCString(None, b"test_value", ca_ctypes.kCFStringEncodingUTF8)

    keys = (ca_ctypes.CFTypeRef * 1)(key)
    values = (ca_ctypes.CFTypeRef * 1)(value)

    cf_dict = ca_ctypes.CFDictionaryCreate(
        None,
        keys,
        values,
        1,
        ca_ctypes.get_cf_type_dictionary_key_callbacks(),
        ca_ctypes.get_cf_type_dictionary_value_callbacks()
    )

    print(f"✓ CFDictionary created: {cf_dict}")

    ca_ctypes.CFRelease(cf_dict)
    ca_ctypes.CFRelease(key)
    ca_ctypes.CFRelease(value)
    print("✓ CFDictionary and items released")
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 5: create_cf_dictionary helper
print("\nTest 5: Using create_cf_dictionary helper...")
try:
    py_dict = {
        "name": "test",
        "value": 123,
        "enabled": True,
    }

    cf_dict = ca_ctypes.create_cf_dictionary(py_dict)
    print(f"✓ CFDictionary created from Python dict: {cf_dict}")

    ca_ctypes.CFRelease(cf_dict)
    print("✓ CFDictionary released")
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("All tests completed!")
