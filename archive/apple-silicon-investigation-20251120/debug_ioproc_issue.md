# IOProc コールバックが呼ばれない問題の詳細分析

## 現状

### 成功している部分 ✅
1. Process Tap作成 (ID=117)
2. Tap stream format読み取り試行
3. Aggregate Device作成 (ID=118)
4. IOProc登録 (PyObjCPointer: 0xa)
5. AudioDeviceStart成功 (status=0)

### 失敗している部分 ❌
- **IOProcコールバックが一度も呼ばれない**
- キャプチャされたバイト数: 0
- 音声チャンク数: 0

## 考えられる原因

### 1. ❌ TCC（プライバシー）権限の問題
**状態**: ユーザー確認済み - ターミナルに音声入力権限を付与済み
**確認方法**: システム環境設定 > プライバシーとセキュリティ > マイク
**結論**: この問題ではない

### 2. ⚠️ Tap Stream Formatの読み取り失敗

```
WARNING - Failed to read tap format: converting to a C array
```

**問題点**:
- AudioCapでは line 133 で `tap.streamFormat` を**必ず**読み取る
- この読み取りはAggregateデバイス作成**前に**実行される
- 現在の実装ではPyObjCの「converting to a C array」エラーで失敗

**AudioCap (Swift)での実装**:
```swift
// Line 133 - CRITICAL!
let tapStreamFormat = tap.streamFormat
```

**影響**:
- Tap streamFormatの読み取りは、Tapデバイスを「アクティブ化」する可能性がある
- この読み取りなしでは、Tapが適切に初期化されない可能性

**解決策**:
- ctypesで `kAudioTapPropertyFormat` を直接読み取る
- または、この読み取りをスキップできるか確認

### 3. ⚠️ Default Output Device UIDの取得失敗

```
WARNING - Failed to query default output device, using fallback: converting to a C array
Using fallback output device UID: BuiltInSpeakerDevice
```

**問題点**:
- PyObjCの `AudioObjectGetPropertyData` が「converting to a C array」エラー
- フォールバック値 `"BuiltInSpeakerDevice"` が正しいか不明
- AudioCapでは実際のデバイスUIDを取得している

**影響**:
- Aggregateデバイスのmain sub-deviceが間違っている可能性
- Sub-device listに存在しないUIDを指定している可能性

**解決策**:
- ctypesで `kAudioHardwarePropertyDefaultSystemOutputDevice` を取得
- `kAudioDevicePropertyDeviceUID` もctypesで取得

### 4. ⚠️ Aggregate Device設定の不備

**AudioCap構成**:
```swift
// Line 140-165
let description: [String: Any] = [
    kAudioAggregateDeviceUIDKey as String: aggregateDeviceUID,
    kAudioAggregateDeviceNameKey as String: "AudioCap Aggregate",
    kAudioAggregateDeviceSubDeviceListKey as String: [
        [kAudioSubDeviceUIDKey as String: outputDeviceUID]
    ],
    kAudioAggregateDeviceMainSubDeviceKey as String: outputDeviceUID,
    kAudioAggregateDeviceTapListKey as String: [
        [
            kAudioSubTapUIDKey as String: tapUUID,
            kAudioSubTapDriftCompensationKey as String: true
        ]
    ],
    kAudioAggregateDeviceTapAutoStartKey as String: true,
    kAudioAggregateDeviceIsPrivateKey as String: true,
    kAudioAggregateDeviceIsStackedKey as String: false
]
```

**現在の実装との差異**:
- キー名は一致 ✅
- 値の型（Bool vs NSNumber）が異なる可能性 ⚠️

### 5. ⚠️ IOProc コールバックのシグネチャ

**PyObjC IOProc シグネチャ**:
```python
@objc.callbackFor(AudioDeviceCreateIOProcID)
def io_proc_callback(device_id, now, input_data, input_time, output_data, output_time, client_data):
```

**Core Audio IOProc型定義**:
```c
typedef OSStatus (*AudioDeviceIOProc)(
    AudioObjectID           inDevice,
    const AudioTimeStamp*   inNow,
    const AudioBufferList*  inInputData,
    const AudioTimeStamp*   inInputTime,
    AudioBufferList*        outOutputData,
    const AudioTimeStamp*   inOutputTime,
    void*                   inClientData
);
```

**問題の可能性**:
- PyObjCの `@objc.callbackFor` が正しくシグネチャを設定していない
- `AudioDeviceCreateIOProcID` に渡すコールバックポインタが無効

### 6. ⚠️ プロセスの音声再生状態

**確認事項**:
- `say` コマンドのプロセスが実行中であること ✅
- AudioObjectID 115が取得できている ✅
- しかし、Process Tapが実際に音声をキャプチャしているか不明 ⚠️

**テスト方法**:
- Tapデバイスに直接IOProcを登録してテスト
- Aggregateを経由せずにTapから読み取れるか確認

### 7. ⚠️ Aggregate DeviceとTapの関連付け

**AudioCapの動作**:
1. Process Tap作成
2. **Tap stream format読み取り** ← CRITICAL
3. Aggregate Device作成（TapをTapListに含める）
4. **Aggregate DeviceにIOProc登録**
5. Aggregate Device起動

**現在の実装の問題**:
- Step 2 が失敗している
- これにより、TapがAggregateに正しく関連付けられていない可能性

## 優先度付き解決策

### Priority 1: Tap Stream Format読み取りをctypesで実装 🔥

この読み取りは**CRITICAL**とAudioCapでもマークされており、最も重要。

```python
# ctypesでの実装例
def read_tap_stream_format_ctypes(tap_device_id: int):
    """Read tap stream format using ctypes."""
    # kAudioTapPropertyFormat = 'ftap'
    address = AudioObjectPropertyAddress(
        mSelector=0x66746170,  # 'ftap'
        mScope=kAudioObjectPropertyScopeGlobal,
        mElement=kAudioObjectPropertyElementMain
    )

    # AudioStreamBasicDescription is 40 bytes
    asbd_size = 40
    asbd_buffer = (ctypes.c_byte * asbd_size)()

    status = AudioObjectGetPropertyData_ctypes(
        tap_device_id,
        address,
        0,
        None,
        ctypes.byref(ctypes.c_uint32(asbd_size)),
        asbd_buffer
    )

    if status == 0:
        # Parse ASBD
        return parse_asbd(asbd_buffer)
```

### Priority 2: Default Output Device UIDをctypesで取得 🔥

フォールバック値が間違っている可能性が高い。

```python
def get_default_output_device_uid_ctypes():
    """Get default output device UID using ctypes."""
    # 1. Get device ID
    # 2. Get device UID property
    # 3. Convert CFString to Python string
```

### Priority 3: IOProcを直接Tapデバイスに登録してテスト 🔧

Aggregateを経由せず、Tapデバイスから直接読み取れるかテスト。

```python
# Test: Tap device直接読み取り
backend._io_proc_id = None
status, io_proc_id = AudioDeviceCreateIOProcID(
    backend._tap_device_id,  # Aggregate IDではなくTap ID
    backend._io_callback,
    None,
    None
)
```

### Priority 4: Aggregateデバイス設定のデバッグ出力 🔍

作成したAggregateデバイスの設定を読み返して確認。

```python
# Aggregateデバイスのプロパティを読み取り
# - SubDeviceList
# - TapList
# - TapAutoStart
# などが正しく設定されているか確認
```

## 次のステップ

1. **Priority 1を実装**: Tap stream formatをctypesで読み取る
2. **Priority 2を実装**: Default output device UIDをctypesで取得
3. **テスト実行**: 音声データがキャプチャされるか確認
4. **Priority 3でデバッグ**: まだ動かない場合、Tap直接読み取りをテスト

## AudioCap との主な違い

| 項目 | AudioCap (Swift) | 現在の実装 (Python/PyObjC) | 状態 |
|------|------------------|---------------------------|------|
| Tap Stream Format読み取り | ✅ 成功 | ❌ PyObjCエラー | 🔴 修正必要 |
| Default Output UID | ✅ 実デバイスUID | ⚠️ フォールバック値 | 🟡 要確認 |
| Aggregate作成 | ✅ Swift API | ✅ ctypes API | 🟢 成功 |
| IOProc登録 | ✅ Swift callback | ✅ PyObjC callback | 🟢 成功 |
| Device起動 | ✅ 成功 | ✅ 成功 | 🟢 成功 |
| **音声データ取得** | ✅ 成功 | ❌ 0バイト | 🔴 失敗 |

**結論**: Tap stream format読み取りとDefault output device UID取得をctypesで実装することで、AudioCapと同等の動作が期待できる。
