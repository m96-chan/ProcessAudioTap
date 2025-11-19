# macOS Process Tap API Investigation Archive (Apple Silicon)

**Date:** 2025-11-20
**Result:** Apple Silicon版では動作不可と判明

## 調査概要

macOS 14.4+で導入されたCore Audio Process Tap APIを使用して、ProcTapのmacOSバックエンドを実装する試み。

### 試みたアプローチ

1. **PyObjC実装** (`macos_pyobjc.py`)
   - Block-based callbacksのサポート不足により失敗

2. **C Extension** (`_macos_native.m`)
   - TCC権限ダイアログが表示されず失敗

3. **Swift CLI Helper** (`swift/proctap-helper/`)
   - TCC権限は取得できたが、`status=2003332927` ('wat?') エラー
   - AMFIによるブロック

### 判明した問題

- **Apple Silicon版では動作不可**
- Intel版でのみ動作する可能性あり（未検証）
- Process Object API (`kAudioHardwarePropertyTranslatePIDToProcessObject`) へのアクセスにAMFI無効化が必要
- AMFIを無効化してもApple Silicon版では権限が得られない

### エラーコード

`status=2003332927` = `0x7761743F` = `'wat?'` = AMFI/TCC permission denied

### 試みた解決策

- ✅ TCC権限（マイク、画面収録）取得
- ✅ SIP無効化 (`csrutil disable`)
- ❌ AMFI無効化 (Apple Siliconでは効果なし)
- ❌ 開発証明書での署名 (秘密鍵の問題で断念)

## アーカイブ内容

### ドキュメント

- `AMFI_DISABLE_INSTRUCTIONS.md` - AMFI無効化手順
- `AMFI_DISABLE_RECOVERY.md` - Recovery Mode手順
- `MACOS_IMPLEMENTATION_FINAL.md` - 最終実装まとめ
- `MACOS_TCC_INVESTIGATION.md` - TCC調査結果
- `SESSION_SUMMARY.md` - セッション記録
- その他調査メモ多数

### 実装コード

- `swift/proctap-helper/` - Swift CLI Helper完全実装
- `macos_pyobjc.py` - PyObjCバックエンド
- `macos_coreaudio_ctypes.py` - ctypesベースバックエンド
- `macos_swift_helper.py` - Pythonラッパー
- `_macos_native.m` - C拡張実装

### テストコード

- `macos_pyobjc_capture_test.py` - PyObjCテスト
- `macos_swift_helper_test.py` - Swift helperテスト
- `test_c_extension.py` - C拡張テスト
- `mactest/` - 各種テストスクリプト
- `*.sh` - シェルスクリプトテスト群

## 技術的知見

### Process Tap API要件

1. macOS 14.4 (Sonoma) 以降
2. TCC権限（マイク、画面収録）
3. 正しいコード署名（Apple Developer ID）
4. **Intel Macまたは特殊な権限設定**

### AudioCapが動作する理由

- 正式なApple Developer ID署名
- Notarization済み
- Intel版でビルド？（未確認）

### 学んだこと

- PyObjCのblock support不完全
- Process Object APIは厳密なセキュリティ制限
- Apple Siliconでは追加の制約がある可能性
- 開発証明書でも不十分（Developer IDが必要）

## 今後の選択肢

1. **AudioCap統合** - 既存の動作するバイナリを使用
2. **Intel Mac対応** - Intel版のみサポート
3. **macOS対応を見送り** - WindowsとLinuxのみサポート

## 参考資料

- AudioCapソース: `/private/tmp/AudioCap/`
- Apple Process Tap API: `kAudioHardwarePropertyTranslatePIDToProcessObject`
- 使用したAPI: `AudioHardwareCreateProcessTap`, `AudioHardwareCreateAggregateDevice`

---

**結論:** macOS Process Tap APIの直接実装は、Apple Siliconでの権限制約により実用的でないと判断。
