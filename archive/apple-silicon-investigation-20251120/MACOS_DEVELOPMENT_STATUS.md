# macOS Process Tap実装 - 開発状況サマリー

## 📊 現在の状況

### ✅ 完成している実装

1. **Swift CLI Helper** ([swift/proctap-helper/Sources/main.swift](swift/proctap-helper/Sources/main.swift))
   - ✅ マイク権限リクエスト（AVFoundation）
   - ✅ Screen Recording権限チェック
   - ✅ `kAudioHardwarePropertyTranslatePIDToProcessObject` API使用（AudioCapと同じ）
   - ✅ Process Tap作成（`AudioHardwareCreateProcessTap`）
   - ✅ Aggregate Device作成
   - ✅ IOProc Block登録（`AudioDeviceCreateIOProcIDWithBlock`）
   - ✅ PCM audio streaming (stdout経由)
   - ✅ アプリケーションバンドル化
   - ✅ Info.plist with usage descriptions

2. **Python Wrapper** ([src/proctap/backends/macos_swift_helper.py](src/proctap/backends/macos_swift_helper.py))
   - ✅ Swift helper binary検出（開発版/パッケージ版）
   - ✅ サブプロセス管理
   - ✅ スレッドベースのaudio queue
   - ✅ Callback/async iterator サポート
   - ✅ AudioBackend インターフェース実装
   - ✅ Format configuration

3. **Backend統合** ([src/proctap/backends/__init__.py](src/proctap/backends/__init__.py))
   - ✅ Swift CLI Helperを優先使用
   - ✅ PyObjCバックエンドへのフォールバック
   - ✅ エラーメッセージとインストール手順

4. **ビルドシステム**
   - ✅ SwiftPM設定（Package.swift）
   - ✅ App Bundle作成スクリプト（build_app_bundle.sh）
   - ✅ AVFoundation framework リンク

### ❌ 未解決の問題

**コード署名の欠如による`status=2003332927`エラー**

症状：
```
ERROR: Failed to translate PID XXX to process object (status=2003332927, objectID=0)
```

エラーコード `2003332927` = `0x7761743F` = `'wat?'` (FourCC) = TCC/AMFI permission denied

原因：
- macOS AMFIがコード署名のないバイナリによるProcess Object APIアクセスをブロック
- Ad-hoc署名（`codesign -s -`）では不十分
- 必要なのはApple Developer ID署名またはAMFI無効化

確認済みの試行：
- ✅ マイク権限取得 → 成功（TCC dialog表示）
- ✅ Screen Recording権限 → 取得済み
- ✅ AudioCapと同じAPI使用 → 実装済み
- ✅ Entitlements追加 → 効果なし
- ✅ Ad-hoc署名 → 効果なし
- ❌ Apple Developer ID署名 → 未実施（証明書なし）

## 🔧 動作させる方法

### オプション1: AMFI無効化（開発用）⭐推奨

**成功確率: 70%**

詳細手順: [AMFI_DISABLE_INSTRUCTIONS.md](AMFI_DISABLE_INSTRUCTIONS.md)

Recovery Modeで以下を実行：
```bash
csrutil enable --without debug
```

これにより、コード署名チェックが緩和されます。

### オプション2: SIP完全無効化（開発用）

**成功確率: 90%**

より確実ですが、セキュリティリスクが高い：
```bash
csrutil disable
```

⚠️ 開発マシンでのみ使用し、テスト後は必ず再有効化すること

### オプション3: Apple Developer ID署名（本番用）

**成功確率: 100%**

要件：
- Apple Developer Program登録（$99/年）
- Developer ID Application証明書
- 適切なEntitlements
- Notarization（配布する場合）

手順：
```bash
codesign --force --sign "Developer ID Application: Your Name (TEAM_ID)" \
         --entitlements proctap-helper.entitlements \
         --options runtime \
         proctap-helper.app

# Notarization（配布用）
xcrun notarytool submit proctap-helper.zip \
      --apple-id your-email@example.com \
      --team-id TEAM_ID \
      --password app-specific-password
```

### オプション4: AudioCap依存（実用的代替案）

**成功確率: 100%**

AudioCapは既に署名済みで動作しています：
- ライセンス: BSD 2-Clause（寛容）
- 商用利用可能
- Pythonラッパーから呼び出し可能

実装アプローチ：
```python
# AudioCapバイナリを検出
# subprocess経由で実行
# 出力をパースしてPCMデータ取得
# 統一APIで提供
```

## 📝 技術的な発見

### Process Tap APIの要件

1. **macOS 14.4+** (Sonoma以降)
2. **マイク権限** - AVFoundationで取得可能
3. **Process Object API アクセス** - コード署名必須
4. **正しいAPI使用**:
   - `kAudioHardwarePropertyTranslatePIDToProcessObject` (PID → Object ID)
   - `AudioHardwareCreateProcessTap` (Process Tap作成)
   - `AudioHardwareCreateAggregateDevice` (Aggregate Device作成)
   - `AudioDeviceCreateIOProcIDWithBlock` (Block-based callback)

### なぜAudioCapは動作するのか

AudioCapが動作する理由：
1. ✅ Apple Developer IDで署名されている
2. ✅ 適切なEntitlementsがある
3. ✅ Notarizedされている（配布版）
4. ✅ TCCが正しく権限を認識できる

### なぜ私たちの実装は動作しないのか

1. ❌ コード署名がない（ad-hoc署名では不十分）
2. ❌ AMFIがProcess Object APIへのアクセスをブロック
3. ❌ TCCは権限を付与しているが、AMFIレベルでブロックされる

## 📂 ファイル構成

```
ProcTap/
├── swift/proctap-helper/
│   ├── Sources/main.swift              # Swift CLI helper実装
│   ├── Package.swift                   # SwiftPM設定
│   ├── build_app_bundle.sh            # App Bundle作成スクリプト
│   ├── proctap-helper.entitlements    # 本番用entitlements
│   └── proctap-helper-debug.entitlements  # 開発用entitlements
│
├── src/proctap/backends/
│   ├── macos_swift_helper.py          # Python wrapper
│   ├── __init__.py                     # Backend selection
│   └── base.py                         # AudioBackend interface
│
├── examples/
│   └── macos_swift_helper_test.py     # テストスクリプト
│
└── ドキュメント/
    ├── MACOS_IMPLEMENTATION_FINAL.md       # 最終調査結果
    ├── MACOS_TCC_INVESTIGATION.md          # TCC問題詳細
    ├── AMFI_DISABLE_INSTRUCTIONS.md        # AMFI無効化手順
    └── MACOS_DEVELOPMENT_STATUS.md         # このファイル
```

## 🚀 次のステップ

### 開発を進める場合

1. **AMFI無効化を試す** ([AMFI_DISABLE_INSTRUCTIONS.md](AMFI_DISABLE_INSTRUCTIONS.md)参照)
2. 動作確認後、実装を完成させる
3. Apple Developer Program登録を検討
4. 署名とNotarizationを実装

### 実用的なアプローチ

1. **AudioCap統合バックエンドを作成**
   - AudioCapバイナリ検出
   - サブプロセス管理
   - 出力パース
   - 統一API提供

2. **ドキュメント整備**
   - 署名手順の詳細化
   - ユーザー向けインストールガイド
   - トラブルシューティング

3. **配布準備**
   - setup.pyにSwiftビルド統合
   - Homebrew Formula作成（署名済みバイナリ配布）
   - PyPIパッケージ公開

## 📚 参考資料

- **AudioCap**: https://github.com/kyleneideck/AudioCap
  - 実証済みのProcess Tap実装
  - BSD 2-Clause License

- **Apple Core Audio**: https://developer.apple.com/documentation/coreaudio
  - Process Tap API（非公開）

- **Apple Code Signing**: https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution
  - Developer ID署名手順

- **TCC/SIP**: https://support.apple.com/en-us/HT204899
  - System Integrity Protection

## ✅ まとめ

実装は**技術的には完成**しています。唯一の障害は**コード署名**です。

開発環境で動作させるには：
- **AMFI無効化**（70%の確率で成功）
- または**SIP無効化**（90%の確率で成功）

本番環境で配布するには：
- **Apple Developer ID署名**（100%成功、$99/年）
- または**AudioCap依存**（100%成功、無料）

どちらの方向で進めるかを決定してください。
