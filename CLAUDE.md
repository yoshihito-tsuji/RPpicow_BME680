# CLAUDE.md — RPpicow_BME680（Pico W 気象観測システム）

> このファイルはClaude Code起動時の自動オリエンテーション用です。
> 詳細な正本はREADME.mdを参照してください。

---

## プロジェクト要約

Raspberry Pi Pico W + BME680センサーで温度・湿度・気圧を計測し、
Ambientクラウドへ10分間隔でデータ送信する屋外気象観測システム。
ガスセンサーは無効化済み。

---

## 現在フェーズ

安定稼働中。設定値のキャリブレーション調整が主な作業。

## 直近の優先事項

1. センサーキャリブレーションの維持・調整
2. 安定稼働の監視（WiFi自動再接続の動作確認）

---

## 技術スタック

- **言語**: MicroPython
- **ハードウェア**: Raspberry Pi Pico W、BME680センサー（I2C: SDA=GP0、SCL=GP1）
- **外部サービス**: Ambient（データ可視化クラウド）
- **通信**: WiFi（複数SSID対応、自動再接続）
- **データ送信間隔**: 10分（600秒）

## 主要ファイル

```
RPpicow_BME680/
├── bme680_reader.py     # メインプログラム（設定値もここに記載）
└── README.md            # 正本
```

## 実行・テストコマンド

```bash
# Pico Wへの転送
mpremote connect /dev/cu.usbmodem* cp bme680_reader.py :main.py

# 実行確認
mpremote connect /dev/cu.usbmodem* run bme680_reader.py
```

---

## プロジェクト固有ルール

- **WiFi認証情報（SSID/パスワード）はコードに直書き**されているため、
  公開リポジトリへのpush前に必ず確認・マスク処理を行うこと
- Ambient チャンネルID・ライトキーも同様に要確認
- 三者協働開発（Dev-Rules）は**未適用**。LOG・DECISIONS.mdは存在しない
- 単一ファイル構成（`bme680_reader.py`）を維持する

---

## 参照先

- プロジェクト詳細: `README.md`
- 三者協働ルール（参考）: `../Dev-Rules/README.md`
