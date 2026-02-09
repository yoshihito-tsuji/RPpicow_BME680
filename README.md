# RPpicow_BME680

Raspberry Pi Pico W と BME680 環境センサーを使用した気象観測システム

## 概要

BME680センサーから温度、湿度、気圧を取得し、Ambientクラウドサービスに送信するMicroPythonプログラムです。屋外気象観測を想定して、ガスセンサー機能は無効化しています。

## 機能

- 温度、湿度、気圧の計測（30秒間隔でローカル表示）
- WiFi接続（複数SSID対応、自動再接続）
- Ambientへのデータ送信（10分間隔）
- キャリブレーション機能（温度・湿度・気圧の補正）
- メモリ管理（ガベージコレクション自動実行）

## ハードウェア

### 必要なもの

- Raspberry Pi Pico W
- BME680センサーモジュール（例：秋月電子 AE-BME680）
- ジャンパーワイヤー
- ブレッドボード（推奨）

### 配線

| BME680ピン | Pico W ピン番号 | Pico W GPIO |
|------------|-----------------|-------------|
| VIN/VCC | 36番ピン | 3V3_OUT |
| GND | 38番ピン | GND |
| SDA | 1番ピン | GP0 |
| SCL | 2番ピン | GP1 |

## セットアップ

### 1. MicroPythonのインストール

Raspberry Pi Pico WにMicroPythonファームウェアをインストールしてください。

### 2. 設定の変更

`bme680_reader.py` の以下の設定を環境に合わせて変更してください：

```python
# WiFi設定（複数SSID対応）
WIFI_NETWORKS = [
    {"ssid": "your-ssid-1", "password": "your-password-1"},
    {"ssid": "your-ssid-2", "password": "your-password-2"},
]

# Ambient設定
AMBIENT_CHANNEL_ID = your_channel_id
AMBIENT_WRITE_KEY = "your_write_key"

# データ送信間隔
SEND_INTERVAL = 600  # 10分 = 600秒

# キャリブレーション（基準計器との差分を設定）
TEMP_OFFSET = 28.74      # 温度オフセット（℃）
HUMIDITY_OFFSET = -4.0   # 湿度オフセット（%RH）
PRESSURE_OFFSET = 36.9   # 気圧オフセット（hPa）
```

### 3. プログラムの転送

```bash
mpremote connect /dev/cu.usbmodem* cp bme680_reader.py :main.py
```

### 4. 実行

Pico Wを再起動するか、以下のコマンドで実行：

```bash
mpremote connect /dev/cu.usbmodem* run bme680_reader.py
```

## Ambientデータフォーマット

気象観測用のデータ構成です。

| チャンネル | 内容 | 単位 |
| ---------- | ---- | ---- |
| d1 | 温度 | °C |
| d2 | 湿度 | %RH |
| d3 | 気圧 | hPa |

## 技術的な特徴

### ハードウェアI2C使用

- GP0（SDA）とGP1（SCL）でハードウェアI2C（I2C0）を使用
- ソフトウェアI2Cよりも安定した通信を実現

### キャリブレーション機能

- 基準計器との比較により温度・湿度・気圧を補正
- オフセット値はコード内で簡単に調整可能

### ガスセンサー無効化

- 屋外気象観測用途のため、ガスセンサー機能は無効化
- ヒーター非動作により消費電力を削減

### 自動WiFi再接続

- 接続断時は自動的に再接続を試行
- 複数SSIDに対応（優先順位順）

## 開発経緯

1. **I2C接続の問題解決**: ソフトウェアI2Cで不安定だったため、ハードウェアI2Cに変更
2. **ピン変更**: GP4/GP5からGP0/GP1に変更して安定化
3. **キャリブレーション**: 基準計器との比較で温度・湿度・気圧オフセットを設定
4. **用途変更**: 室内空気質監視から屋外気象観測へ用途を変更
5. **ガスセンサー無効化**: 気象観測にガスセンサーは不要なため無効化
6. **Ambientデータ構成変更**: 温度・湿度・気圧の3要素に最適化

## 注意事項

- センサーは経年劣化するため、定期的なキャリブレーションを推奨
- 屋外設置の場合は防水・防塵対策が必要
- 直射日光が当たらない場所への設置を推奨
- WiFi電波が届く範囲での使用を前提

## 参考資料

- [MicroPython公式ドキュメント](https://docs.micropython.org/)
- [Raspberry Pi Pico W](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html)
- [BME680データシート](https://www.bosch-sensortec.com/products/environmental-sensors/gas-sensors/bme680/)
- [Ambient API仕様](https://ambidata.io/refs/api/)
- [mpremote公式ドキュメント](https://docs.micropython.org/en/latest/reference/mpremote.html)

## 開発環境

### 📚 開発方法論の詳細

- **GitHub版**: [Dev-Rules](https://github.com/yoshihito-tsuji/Dev-Rules)
- **ローカル版**: [../Dev-Rules/README.md](../Dev-Rules/README.md)
- **Codex向けガイド**: [../Dev-Rules/CODEX_ONBOARDING.md](../Dev-Rules/CODEX_ONBOARDING.md)
- **Claude Code Best Practice**: [../Dev-Rules/claude-code/README.md](../Dev-Rules/claude-code/README.md)

## ライセンス

MIT License
