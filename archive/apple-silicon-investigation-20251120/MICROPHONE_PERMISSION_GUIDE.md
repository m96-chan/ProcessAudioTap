# マイク権限の設定ガイド

## 📋 概要

ProcTapのmacOSバックエンドは、プロセスからオーディオをキャプチャするためにマイク権限が必要です。これはmacOSのTCC (Transparency, Consent, and Control) システムによって管理されています。

## 🚨 問題: システム設定にアプリが表示されない

システム設定の「プライバシーとセキュリティ」→「マイク」にPythonやTerminalが**表示されない**場合、まだそのアプリがマイクアクセスをリクエストしていません。

## ✅ 解決方法

### 方法1: マイク権限をリセットしてダイアログを再表示 (推奨)

すべてのマイク権限をリセットすると、次回マイクアクセス時にダイアログが表示されます：

```bash
# すべてのマイク権限をリセット
tccutil reset Microphone
```

実行後、以下のコマンドでテストを実行すると、**システムダイアログが表示されます**：

```bash
# テスト実行（ダイアログが表示されるはず）
./quick_test.sh
```

ダイアログが表示されたら、**「OK」または「許可」をクリック**してください。

### 方法2: PyObjC AVFoundationをインストールして強制トリガー

PyObjC AVFoundationモジュールをインストールすることで、より確実にダイアログをトリガーできます：

```bash
# PyObjC AVFoundationをインストール
pip install pyobjc-framework-AVFoundation

# ダイアログをトリガー
python3.12 -c "from AVFoundation import AVCaptureDevice, AVMediaTypeAudio; print(AVCaptureDevice.defaultDeviceWithMediaType_(AVMediaTypeAudio))"
```

このコマンドを実行すると、システムダイアログが表示されます。

### 方法3: システム設定で手動追加

システム設定にアプリが表示されている場合：

1. **システム設定**を開く（Appleメニュー  → システム設定）
2. **「プライバシーとセキュリティ」**をクリック
3. **「マイク」**をクリック
4. 以下のいずれかを探す：
   - ☑️ Terminal（Terminalから実行している場合）
   - ☑️ iTerm2（iTerm2から実行している場合）
   - ☑️ python3.12
   - ☑️ Python
   - ☑️ 使用しているIDEの名前（VS Code、PyCharmなど）

5. チェックボックスを**有効化** ✓

## 🎬 ダイアログの表示例

マイクアクセスをリクエストすると、以下のようなシステムダイアログが表示されます：

```
┌────────────────────────────────────────────┐
│  "python3.12"がマイクにアクセスしようと     │
│  しています。                              │
│                                            │
│           [許可しない]    [OK]              │
└────────────────────────────────────────────┘
```

**「OK」をクリックしてください**。

## 🔍 現在の実行環境を確認

あなたの環境では：

- **Python実行可能ファイル**: `/Users/djsaxia/.anyenv/envs/pyenv/versions/3.12.11/bin/python3.12`
- **システム設定で探すべき名前**:
  - `python3.12`
  - `Python`
  - または使用中のターミナル/IDEの名前

## 📝 手順まとめ

### 最も簡単な方法（推奨）：

```bash
# 1. マイク権限をリセット
tccutil reset Microphone

# 2. テストを実行（ダイアログが表示される）
./quick_test.sh

# 3. ダイアログで「OK」をクリック

# 4. テストが成功することを確認
```

### 既にダイアログで「許可しない」をクリックしてしまった場合：

```bash
# リセットして再度試す
tccutil reset Microphone

# または、システム設定で手動で有効化
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
```

## ⚠️ 重要な注意点

1. **権限はアプリごと**に管理されます：
   - Terminalから実行 → Terminalに権限が必要
   - VS Codeから実行 → VS Codeに権限が必要
   - スクリプトで直接実行 → Python実行ファイルに権限が必要

2. **ダイアログは1回だけ**表示されます：
   - 一度「許可しない」をクリックすると、再表示されません
   - 再表示するには `tccutil reset Microphone` を使用

3. **権限付与後は再起動不要**：
   - 権限を付与したら、すぐにテストを実行できます

## 🧪 テスト手順

権限を付与した後：

```bash
# 音声プロセスを起動
say "テスト音声です。1, 2, 3, 4, 5" &
SAY_PID=$!

# オーディオキャプチャテスト
python3.12 examples/macos_pyobjc_capture_test.py --pid $SAY_PID --duration 5 --output test.wav

# 再生して確認
afplay test.wav
```

## 📊 期待される成功時の出力

```
macOS Version: 15.6.0
PyObjC Status: Available ✓
Process Tap API: Supported ✓

Creating MacOSNativeBackend...
✅ Microphone permission already granted

Starting audio capture...
Creating process tap for PID 12345...
✓ Process tap created: device ID 117

Reading tap stream format (CRITICAL)...
✅ [CRITICAL] Tap stream format read successfully: 48000 Hz, 2 channels, 32 bits/sample

Getting default output device UID...
✓ Default output device UID: [デバイスUID]

Creating aggregate device...
✓ Aggregate device created: ID 118

Starting aggregate device...
✓ Device started successfully

Capturing audio for 5.0 seconds...
  [5.0s] Captured 500 chunks, 960,000 bytes

Phase 2 Test: PASSED ✓
```

## 🔧 トラブルシューティング

### 問題: ダイアログが表示されない

**解決策**:
```bash
# 1. まず権限をリセット
tccutil reset Microphone

# 2. PyObjC AVFoundationをインストール（より確実）
pip install pyobjc-framework-AVFoundation

# 3. 直接ダイアログをトリガー
python3.12 -c "from AVFoundation import AVCaptureDevice, AVMediaTypeAudio; AVCaptureDevice.defaultDeviceWithMediaType_(AVMediaTypeAudio)"

# 4. ダイアログで「OK」をクリック

# 5. テスト実行
./quick_test.sh
```

### 問題: 「Audio capture permission denied (status=2003332927)」エラー

**意味**: Status `2003332927` = `'wat?'` = TCC権限拒否

**解決策**:
- 上記の方法でマイク権限を付与してください

### 問題: システム設定にアプリが表示されているが、チェックボックスがない

**解決策**:
- アプリ名を一度リストから削除（`-`ボタン）
- `tccutil reset Microphone` を実行
- テストを再実行してダイアログを再表示

## 📚 参考情報

- **TCC データベース**: `~/Library/Application Support/com.apple.TCC/TCC.db`
- **エラーコード**:
  - `0` = 成功
  - `2003332927` = `'wat?'` = 権限拒否
  - `560947818` = `'!no!'` = プロパティが見つからない

## 🎉 成功したら

権限が正しく設定され、テストが成功したら：

1. ✅ マイク権限が付与されました
2. ✅ Priority 1 & 2の修正（Tap format読み取り、Output device UID取得）が動作しています
3. ✅ オーディオキャプチャが正常に動作しています

これで、ProcTapのmacOSバックエンドが完全に機能します！
