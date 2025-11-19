# AMFI無効化手順（Recovery Mode）

## 現在の状態
- ✅ SIP無効化済み (`csrutil status` = disabled)
- ❌ AMFI有効（`status=2003332927` エラーが継続）

## 必要な作業

Recovery Modeで以下のコマンドを実行してAMFIを無効化:

```bash
nvram boot-args="amfi_get_out_of_my_way=1"
```

## 手順

### 1. Recovery Modeで起動

**Intel Mac:**
1. Macを再起動
2. 起動音が聞こえたら、すぐに `Cmd + R` を押し続ける
3. Appleロゴが表示されるまで押し続ける

**Apple Silicon Mac (M1/M2/M3):**
1. Macをシャットダウン
2. 電源ボタンを長押し（10秒以上）
3. 「起動オプションを読み込み中...」が表示されたら、「オプション」をクリック
4. 「続ける」をクリック

### 2. ターミナルを開く

- メニューバーから **ユーティリティ → ターミナル** を選択

### 3. AMFIを無効化

```bash
# AMFI無効化
nvram boot-args="amfi_get_out_of_my_way=1"

# 確認
nvram boot-args
```

**期待される出力:**
```
boot-args	amfi_get_out_of_my_way=1
```

### 4. 再起動

```bash
reboot
```

## テスト

通常モードで起動後、以下でテスト:

```bash
# boot-args確認
nvram boot-args

# Swift helperテスト
cd /Users/djsaxia/projects/m96-chan/ProcTap/swift/proctap-helper
say "Testing AMFI disabled" &
sleep 0.5
SAY_PID=$(ps aux | grep " say " | grep -v grep | awk '{print $2}' | head -1)
echo "Testing with PID: $SAY_PID"
.build/arm64-apple-macosx/release/proctap-helper.app/Contents/MacOS/proctap-helper $SAY_PID
```

**期待される結果:**
```
Found process object ID XXX for PID YYY
Created process tap: ZZZZZ
...
[PCM audio data streaming]
```

## 注意事項

⚠️ **セキュリティへの影響:**
- AMFIはコード署名検証を無効化します
- 署名されていないコードが実行可能になります
- **開発マシンでのみ使用**してください
- 本番環境では絶対に使用しないでください

## 元に戻す方法

AMFIを再度有効化する場合は、Recovery Modeで:

```bash
# boot-argsを削除
nvram -d boot-args

# またはSIPも再度有効化
csrutil enable
nvram -d boot-args
reboot
```
