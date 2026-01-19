# RPpicow_BME680

Raspberry Pi Pico W と BME680 環境センサーを使用した空気質モニタリングシステム

## 概要

BME680センサーから温度、湿度、気圧、ガス抵抗値を取得し、IAQ（Indoor Air Quality）スコアを算出してAmbientに送信するMicroPythonプログラムです。

## 機能

- 温度、湿度、気圧の計測
- VOC（揮発性有機化合物）によるガス抵抗値の計測
- IAQスコア（室内空気質指数）の算出
- WiFi接続（複数SSID対応）
- Ambientへのデータ送信（10分間隔）

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
# WiFi設定
WIFI_NETWORKS = [
    {"ssid": "your-ssid", "password": "your-password"},
]

# Ambient設定
AMBIENT_CHANNEL_ID = your_channel_id
AMBIENT_WRITE_KEY = "your_write_key"

# キャリブレーション（基準温度計との差分）
TEMP_OFFSET = 28.74  # 温度オフセット（℃）
HUMIDITY_OFFSET = -4.0  # 湿度オフセット（%RH）
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

| チャンネル | 内容 | 単位 |
|------------|------|------|
| d1 | 温度 | °C |
| d2 | 湿度 | %RH |
| d3 | IAQスコア | 0-500 |
| d4 | 気圧 | hPa |
| d5 | ガス抵抗値 | Ω |

## IAQスコアの目安

| スコア | 評価 | 対応 |
|--------|------|------|
| 0-50 | 優良 (Excellent) | 問題なし |
| 51-100 | 良好 (Good) | 問題なし |
| 101-150 | 軽度汚染 (Lightly Polluted) | 換気推奨 |
| 151-200 | 中度汚染 (Moderately Polluted) | 換気が必要 |
| 201-300 | 重度汚染 (Heavily Polluted) | 即座に換気 |
| 301-500 | 危険 (Severely Polluted) | 退避・原因究明 |

## 開発経緯

1. **I2C接続の問題解決**: ソフトウェアI2Cで不安定だったため、ハードウェアI2Cに変更
2. **ピン変更**: GP4/GP5からGP0/GP1に変更して安定化
3. **キャリブレーション**: 基準温度計との比較で温度・湿度オフセットを設定
4. **ガス抵抗計算の修正**: BME680データシートに基づく計算式に修正
5. **Ambientデータ構成**: IAQスコアを重視した構成に変更

## 注意事項

- ガスセンサーは起動後5-10分で安定します
- センサーは経年劣化するため、定期的なキャリブレーションを推奨
- BME680はCO2やCOは検出できません（VOCの総合指標）

## ライセンス

MIT License
