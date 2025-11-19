# AMFI無効化手順（開発用）

## ⚠️ 警告

この手順は開発環境専用です。本番環境では絶対に実施しないでください。
セキュリティリスクがあるため、テスト完了後は必ず再有効化してください。

## 目的

macOS Process Tap APIのコード署名チェックを回避して、開発中のSwift Helperを動作させる。

## 手順

### 1. Recovery Modeで起動

1. **Macを再起動**
2. 起動音が鳴ったら、または画面が表示されたら、すぐに **Command (⌘) + R** を押し続ける
3. Appleロゴとプログレスバーが表示されたら、キーを離す
4. Recovery Modeが起動するまで待つ

### 2. ターミナルを開く

1. 上部メニューバーから **ユーティリティ** → **ターミナル** を選択

### 3. SIPの状態を確認

```bash
csrutil status
```

現在の状態が表示されます。

### 4. AMFIを無効化（オプションA: 推奨）

コード署名検証だけを無効にする（他のSIP保護は維持）：

```bash
csrutil enable --without debug
```

**または**

### 4. SIPを完全に無効化（オプションB: より確実だが危険）

```bash
csrutil disable
```

### 5. 再起動

```bash
reboot
```

### 6. 通常モードで起動後、確認

ターミナルで以下を実行：

```bash
csrutil status
```

以下のような表示になれば成功：

**オプションAの場合:**
```
System Integrity Protection status: enabled (Custom Configuration).

Configuration:
    Apple Internal: disabled
    Kext Signing: enabled
    Filesystem Protections: enabled
    Debugging Restrictions: disabled  ← これが重要
    DTrace Restrictions: enabled
    NVRAM Protections: enabled
    BaseSystem Verification: enabled
```

**オプションBの場合:**
```
System Integrity Protection status: disabled.
```

### 7. Swift Helperをテスト

```bash
cd /Users/djsaxia/projects/m96-chan/ProcTap/swift/proctap-helper

# 再ビルド
bash build_app_bundle.sh

# テスト
say "Testing AMFI disabled configuration" &
sleep 0.5
PID=$(ps aux | grep " say " | grep -v grep | awk '{print $2}' | head -1)
.build/arm64-apple-macosx/release/proctap-helper.app/Contents/MacOS/proctap-helper $PID
```

### 8. 動作確認

以下のいずれかが表示されれば成功：

✅ `Found process object ID XXX for PID YYY`
✅ `Process Tap created: device ID XXX`

以下が表示されなくなれば成功：

❌ `ERROR: Failed to translate PID ... (status=2003332927, ...)`

## テスト完了後の再有効化（重要！）

開発が完了したら、必ずSIPを再有効化してください：

### 1. 再度Recovery Modeで起動（Command + R）

### 2. ターミナルで以下を実行

```bash
csrutil enable
```

### 3. 再起動

```bash
reboot
```

### 4. 確認

```bash
csrutil status
# "System Integrity Protection status: enabled." と表示されればOK
```

## トラブルシューティング

### Q1: Recovery Modeに入れない

**M1/M2 Mac の場合:**
1. Macをシャットダウン
2. 電源ボタンを長押し（10秒以上）
3. 「起動オプションを読み込み中...」と表示されたら離す
4. 「オプション」を選択
5. 管理者パスワードを入力

**Intel Mac の場合:**
- Command + R を確実に起動音の直後から押し続ける
- それでもダメなら Command + Option + R（インターネットリカバリ）

### Q2: パスワードを求められる

Recovery Modeでは、Mac管理者のパスワードが必要です。

### Q3: csrutilコマンドが見つからない

Recovery Modeのターミナルで実行していることを確認してください。
通常モードでは実行できません。

## 補足：代替案

もしAMFI無効化でも動作しない場合：

1. **Apple Developer Programに登録**（$99/年）
   - Developer ID証明書を取得
   - 正式に署名してNotarization

2. **AudioCapを依存として使用**
   - 既に署名済みのAudioCapバイナリを利用
   - BSD 2-Clauseライセンスで商用利用可能

## 参考

- Apple SIP公式ドキュメント: https://support.apple.com/en-us/HT204899
- csrutil manpage: `man csrutil` (Recovery Modeで実行)
