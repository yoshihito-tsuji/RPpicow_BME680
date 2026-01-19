# 開発ルール (Dev-rules)

## プロジェクト概要

このプロジェクトは、Raspberry Pi Pico WとBME680環境センサーを使用した気象観測システムです。温度・湿度・気圧を計測し、Ambientクラウドサービスに送信します。

## 技術スタック

- **マイクロコントローラ**: Raspberry Pi Pico W
- **言語**: MicroPython
- **センサー**: BME680（I2C接続）
- **通信**: WiFi経由でAmbientにHTTP POST
- **データ送信間隔**: 10分（600秒）

## 開発環境のセットアップ

### 1. 必要なツール

```bash
# macOS/Linux
brew install micropython

# mpremoteのインストール（ファイル転送・実行用）
pip install mpremote

# シリアル通信確認（オプション）
brew install picocom
```

### 2. Pico Wのセットアップ

1. MicroPythonファームウェアをダウンロード
   - https://micropython.org/download/RPI_PICO_W/
   - 最新の`.uf2`ファイルを取得

2. Pico WをBOOTSELモードで接続
   - BOOTSELボタンを押しながらUSBケーブルを接続
   - ドライブとしてマウントされる

3. `.uf2`ファイルをコピー
   - ファイルをドラッグ&ドロップ
   - 自動的に再起動してMicroPythonが起動

### 3. プロジェクトのクローン

```bash
git clone <repository-url>
cd RPpicow_BME680
```

## 開発ワークフロー

### ファイル転送

```bash
# メインプログラムとして転送（自動起動）
mpremote connect /dev/cu.usbmodem* cp bme680_reader.py :main.py

# 通常のファイルとして転送
mpremote connect /dev/cu.usbmodem* cp bme680_reader.py :
```

### デバッグ実行

```bash
# プログラムを実行（REPLで出力確認）
mpremote connect /dev/cu.usbmodem* run bme680_reader.py

# REPLに接続
mpremote connect /dev/cu.usbmodem*
```

### シリアルモニタリング

```bash
# picocomで接続（Ctrl+A → Ctrl+Xで終了）
picocom /dev/cu.usbmodem* -b 115200

# screenで接続（Ctrl+A → Kで終了）
screen /dev/cu.usbmodem* 115200
```

## コーディング規約

### Python スタイル

- PEP 8に準拠（MicroPythonの制約内で）
- 関数・クラスにはdocstringを記載
- 定数は大文字（例: `TEMP_OFFSET`）
- プライベートメソッドには`_`プレフィックス

### コメント

- 複雑なロジックには日本語でコメントを追加
- ハードウェア設定には詳細な説明を記載
- キャリブレーション値の根拠を明記

### エラーハンドリング

- I2C通信エラーは適切にキャッチ
- WiFi接続失敗時はローカル計測継続
- センサー初期化失敗時は明確なメッセージを表示

## ハードウェア構成

### BME680接続

| BME680ピン | Pico W ピン番号 | Pico W GPIO | 説明 |
|------------|-----------------|-------------|------|
| VIN/VCC | 36 | 3V3_OUT | 電源（3.3V） |
| GND | 38 | GND | グランド |
| SDA | 1 | GP0 | I2Cデータ |
| SCL | 2 | GP1 | I2Cクロック |

### I2C設定

- **バス**: ハードウェアI2C (I2C0)
- **周波数**: 100kHz
- **アドレス**: 0x77または0x76（自動検出）

## センサー設定

### キャリブレーション

温度・湿度・気圧のキャリブレーション値は、基準計器との比較により決定します。

```python
TEMP_OFFSET = 28.74      # 温度補正値（℃）
HUMIDITY_OFFSET = -4.0   # 湿度補正値（%RH）
PRESSURE_OFFSET = 36.9   # 気圧補正値（hPa）
```

### センサー動作モード

- **温度・気圧**: オーバーサンプリング x4
- **湿度**: オーバーサンプリング x2
- **ガスセンサー**: 無効（気象観測用途のため）
- **測定モード**: 強制モード（Forced Mode）

## Ambient連携

### データフォーマット

| チャンネル | 内容 | 単位 |
|------------|------|------|
| d1 | 温度 | °C |
| d2 | 湿度 | %RH |
| d3 | 気圧 | hPa |

### 設定方法

`bme680_reader.py`の以下の値を変更：

```python
AMBIENT_CHANNEL_ID = 98573              # あなたのチャンネルID
AMBIENT_WRITE_KEY = "your_write_key"    # あなたのライトキー
SEND_INTERVAL = 600                      # 送信間隔（秒）
```

## WiFi設定

### 複数SSID対応

```python
WIFI_NETWORKS = [
    {"ssid": "primary-wifi", "password": "password1"},
    {"ssid": "backup-wifi", "password": "password2"},
]
```

優先順位順に接続を試行します。

## トラブルシューティング

### I2Cデバイスが検出されない

1. 配線を確認（特にVCCとGND）
2. センサーの電源電圧を確認（3.3V）
3. I2Cアドレスを確認（0x76/0x77を自動検出）

### WiFi接続エラー

1. SSIDとパスワードを確認
2. ネットワークの電波強度を確認
3. ローカル計測は継続実行される

### センサー値の異常

1. キャリブレーション値を再確認
2. センサーの設置環境を確認
3. 電源電圧の安定性を確認

## Git運用

### ブランチ戦略

- `main`: 安定版
- `feature/*`: 新機能開発
- `fix/*`: バグ修正

### コミットメッセージ

```
Add: 新機能追加
Update: 既存機能の更新
Fix: バグ修正
Refactor: リファクタリング
Docs: ドキュメント更新
```

### 注意事項

- WiFi認証情報やAPIキーはコミットしない
- 必要に応じて`.env`ファイルや`secrets.py`を使用
- 機密情報は`.gitignore`に追加

## テスト

### 動作確認項目

- [ ] I2Cデバイス検出
- [ ] センサー初期化
- [ ] 温度・湿度・気圧の読み取り
- [ ] WiFi接続
- [ ] Ambientへのデータ送信
- [ ] エラー時の挙動

### 長時間稼働テスト

- 24時間以上の連続稼働を確認
- メモリリークの確認（`gc.collect()`で対応）
- WiFi再接続の動作確認

## パフォーマンス

### メモリ管理

- 定期的に`gc.collect()`を実行
- HTTP通信後はレスポンスを適切にクローズ
- 不要なオブジェクトは即座に解放

### 電力管理

- 測定間隔: 30秒（ローカル表示）
- 送信間隔: 600秒（Ambient送信）
- スリープモードは未実装（常時稼働想定）

## ライセンス

MIT License

## 参考資料

- [MicroPython公式ドキュメント](https://docs.micropython.org/)
- [Raspberry Pi Pico W](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html)
- [BME680データシート](https://www.bosch-sensortec.com/products/environmental-sensors/gas-sensors/bme680/)
- [Ambient API仕様](https://ambidata.io/refs/api/)
