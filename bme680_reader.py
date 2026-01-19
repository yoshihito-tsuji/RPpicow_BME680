"""
BME680センサー読み取りプログラム
Raspberry Pi Pico W用

接続ピン:
- 電源: 36ピン (3V3_OUT)
- GND: 38ピン
- SDA: 1ピン (GP0)
- SCL: 2ピン (GP1)

機能:
- BME680センサーからデータ取得
- WiFi接続（2つのSSIDに対応）
- Ambientへデータ送信（10分間隔）
"""

from machine import Pin, I2C
import time
import struct
import network
import urequests
import gc

# ============================================
# WiFi設定（優先順位順）
# ============================================
WIFI_NETWORKS = [
    {"ssid": "wallfacer9", "password": "2choco2dango3jam"},
]

# ============================================
# Ambient設定
# ============================================
AMBIENT_CHANNEL_ID = 98573
AMBIENT_WRITE_KEY = "1259d6fac2a1af55"

# データ送信間隔（秒）
SEND_INTERVAL = 600  # 10分 = 600秒

# ============================================
# BME680 I2Cアドレス
# ============================================
BME680_ADDR = 0x77  # または 0x76（SDOピンの接続による）

# ============================================
# キャリブレーション設定
# 実測値と基準温度計の差分を設定してください
# 例: 基準温度計が25.4°C、センサーが3.2°Cの場合 → 22.2
# ============================================
TEMP_OFFSET = 28.74  # 温度オフセット（℃）
HUMIDITY_OFFSET = -4.0  # 湿度オフセット（%RH）
PRESSURE_OFFSET = 0.0  # 気圧オフセット（hPa）

# BME680レジスタアドレス
BME680_REG_CHIP_ID = 0xD0
BME680_REG_CTRL_HUM = 0x72
BME680_REG_CTRL_MEAS = 0x74
BME680_REG_CONFIG = 0x75
BME680_REG_CTRL_GAS_1 = 0x71
BME680_REG_CTRL_GAS_0 = 0x70
BME680_REG_GAS_WAIT_0 = 0x64
BME680_REG_RES_HEAT_0 = 0x5A
BME680_REG_DATA = 0x1D


class BME680:
    """BME680センサークラス"""

    def __init__(self, i2c, addr=BME680_ADDR):
        self.i2c = i2c
        self.addr = addr

        # チップIDを確認
        chip_id = self._read_byte(BME680_REG_CHIP_ID)
        if chip_id != 0x61:
            # 別アドレスを試す
            self.addr = 0x76
            chip_id = self._read_byte(BME680_REG_CHIP_ID)
            if chip_id != 0x61:
                raise RuntimeError(f"BME680が見つかりません (Chip ID: {hex(chip_id)})")

        print(f"BME680検出 (アドレス: {hex(self.addr)})")

        # キャリブレーションデータ読み取り
        self._read_calibration()

        # センサー設定
        self._setup()

    def _read_byte(self, reg):
        time.sleep_ms(10)
        return self.i2c.readfrom_mem(self.addr, reg, 1)[0]

    def _read_bytes(self, reg, length):
        time.sleep_ms(10)
        return self.i2c.readfrom_mem(self.addr, reg, length)

    def _write_byte(self, reg, value):
        time.sleep_ms(10)
        self.i2c.writeto_mem(self.addr, reg, bytes([value]))

    def _read_calibration(self):
        """キャリブレーションデータを読み取る"""
        # 温度・気圧キャリブレーション (0x89-0xA1)
        coeff1 = self._read_bytes(0x89, 25)
        # 湿度キャリブレーション (0xE1-0xE8)
        coeff2 = self._read_bytes(0xE1, 16)
        # ガスキャリブレーション
        coeff3 = self._read_bytes(0x00, 3)

        # 温度キャリブレーション
        self.par_t1 = (coeff1[0] | (coeff1[1] << 8))
        self.par_t2 = self._signed_short(coeff1[2] | (coeff1[3] << 8))
        self.par_t3 = coeff1[4]

        # 気圧キャリブレーション
        self.par_p1 = (coeff1[5] | (coeff1[6] << 8))
        self.par_p2 = self._signed_short(coeff1[7] | (coeff1[8] << 8))
        self.par_p3 = coeff1[9]
        self.par_p4 = self._signed_short(coeff1[11] | (coeff1[12] << 8))
        self.par_p5 = self._signed_short(coeff1[13] | (coeff1[14] << 8))
        self.par_p6 = coeff1[15]
        self.par_p7 = coeff1[16]
        self.par_p8 = self._signed_short(coeff1[17] | (coeff1[18] << 8))
        self.par_p9 = self._signed_short(coeff1[19] | (coeff1[20] << 8))
        self.par_p10 = coeff1[21]

        # 湿度キャリブレーション
        self.par_h1 = (coeff2[2] << 4) | (coeff2[1] & 0x0F)
        self.par_h2 = (coeff2[0] << 4) | (coeff2[1] >> 4)
        self.par_h3 = coeff2[3]
        self.par_h4 = coeff2[4]
        self.par_h5 = coeff2[5]
        self.par_h6 = coeff2[6]
        self.par_h7 = coeff2[7]

        # ガスキャリブレーション
        self.par_g1 = coeff3[2]
        self.par_g2 = self._signed_short(coeff3[0] | (coeff3[1] << 8))
        self.par_g3 = self._read_byte(0x02)

        # ヒーターレンジ
        self.res_heat_range = (self._read_byte(0x02) >> 4) & 0x03
        self.res_heat_val = self._read_byte(0x00)
        self.range_sw_err = (self._read_byte(0x04) & 0xF0) >> 4

    def _signed_short(self, val):
        if val >= 0x8000:
            return val - 0x10000
        return val

    def _setup(self):
        """センサーを設定"""
        # ソフトリセット
        self._write_byte(0xE0, 0xB6)
        time.sleep_ms(10)

        # 湿度オーバーサンプリング x2
        self._write_byte(BME680_REG_CTRL_HUM, 0x02)

        # ガスセンサー設定
        # ヒーター温度設定（300℃）
        self._set_gas_heater(300, 100)

        # ガス計測有効化
        self._write_byte(BME680_REG_CTRL_GAS_1, 0x10)

        # フィルタ係数 3, 3線SPIオフ
        self._write_byte(BME680_REG_CONFIG, 0x04)

    def _set_gas_heater(self, temp, duration):
        """ガスヒーター設定"""
        # ヒーター抵抗計算
        var1 = ((self.par_g1 / 16.0) + 49.0)
        var2 = (((self.par_g2 / 32768.0) * 0.0005) + 0.00235)
        var3 = (self.par_g3 / 1024.0)
        var4 = var1 * (1.0 + (var2 * temp))
        var5 = var4 + (var3 * 25)  # 環境温度25℃と仮定
        res_heat = int(3.4 * ((var5 * (4.0 / (4.0 + self.res_heat_range)) *
                              (1.0 / (1.0 + (self.res_heat_val * 0.002)))) - 25))

        self._write_byte(BME680_REG_RES_HEAT_0, res_heat)

        # ヒーター時間設定
        gas_wait = self._calc_gas_wait(duration)
        self._write_byte(BME680_REG_GAS_WAIT_0, gas_wait)

    def _calc_gas_wait(self, duration):
        """ガス待機時間を計算"""
        if duration >= 4096:
            return 0xFF

        factor = 0
        while duration > 63:
            duration = duration // 4
            factor += 1

        return int(duration + (factor * 64))

    def read_data(self):
        """全センサーデータを読み取る"""
        # 強制モードで計測開始
        # 温度・気圧オーバーサンプリング x4, 強制モード
        self._write_byte(BME680_REG_CTRL_MEAS, 0x55)

        # 計測完了を待機
        time.sleep_ms(200)

        # データ読み取り
        data = self._read_bytes(BME680_REG_DATA, 15)

        # ADC値を抽出
        adc_pres = (data[2] << 12) | (data[3] << 4) | (data[4] >> 4)
        adc_temp = (data[5] << 12) | (data[6] << 4) | (data[7] >> 4)
        adc_hum = (data[8] << 8) | data[9]
        adc_gas = (data[13] << 2) | (data[14] >> 6)
        gas_range = data[14] & 0x0F

        # ガス計測有効フラグ
        gas_valid = (data[14] >> 5) & 0x01
        heat_stable = (data[14] >> 4) & 0x01

        # 温度計算
        temperature = self._calc_temperature(adc_temp)

        # 気圧計算
        pressure = self._calc_pressure(adc_pres)

        # 湿度計算
        humidity = self._calc_humidity(adc_hum)

        # ガス抵抗計算
        gas_resistance = None
        if gas_valid and heat_stable:
            gas_resistance = self._calc_gas_resistance(adc_gas, gas_range)

        # キャリブレーション適用
        temperature_calibrated = temperature + TEMP_OFFSET
        humidity_calibrated = humidity + HUMIDITY_OFFSET
        pressure_calibrated = pressure + PRESSURE_OFFSET

        return {
            'temperature': temperature_calibrated,
            'temperature_raw': temperature,
            'pressure': pressure_calibrated,
            'humidity': humidity_calibrated,
            'gas_resistance': gas_resistance,
            'gas_valid': gas_valid,
            'heat_stable': heat_stable
        }

    def _calc_temperature(self, adc_temp):
        """温度を計算（℃）"""
        var1 = (adc_temp / 16384.0 - self.par_t1 / 1024.0) * self.par_t2
        var2 = ((adc_temp / 131072.0 - self.par_t1 / 8192.0) *
                (adc_temp / 131072.0 - self.par_t1 / 8192.0) * self.par_t3 * 16.0)
        self.t_fine = var1 + var2
        return self.t_fine / 5120.0

    def _calc_pressure(self, adc_pres):
        """気圧を計算（hPa）"""
        var1 = self.t_fine / 2.0 - 64000.0
        var2 = var1 * var1 * self.par_p6 / 131072.0
        var2 = var2 + var1 * self.par_p5 * 2.0
        var2 = var2 / 4.0 + self.par_p4 * 65536.0
        var1 = (self.par_p3 * var1 * var1 / 16384.0 + self.par_p2 * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * self.par_p1

        if var1 == 0:
            return 0

        pressure = 1048576.0 - adc_pres
        pressure = (pressure - var2 / 4096.0) * 6250.0 / var1
        var1 = self.par_p9 * pressure * pressure / 2147483648.0
        var2 = pressure * self.par_p8 / 32768.0
        var3 = (pressure / 256.0) ** 3 * self.par_p10 / 131072.0

        return (pressure + (var1 + var2 + var3 + self.par_p7 * 128.0) / 16.0) / 100.0

    def _calc_humidity(self, adc_hum):
        """湿度を計算（%RH）"""
        temp_comp = self.t_fine / 5120.0

        var1 = adc_hum - (self.par_h1 * 16.0 + (self.par_h3 / 2.0) * temp_comp)
        var2 = var1 * (self.par_h2 / 262144.0 * (1.0 + (self.par_h4 / 16384.0) * temp_comp +
               (self.par_h5 / 1048576.0) * temp_comp * temp_comp))
        var3 = self.par_h6 / 16384.0
        var4 = self.par_h7 / 2097152.0

        humidity = var2 + (var3 + var4 * temp_comp) * var2 * var2

        # 範囲制限
        if humidity > 100.0:
            humidity = 100.0
        elif humidity < 0.0:
            humidity = 0.0

        return humidity

    def _calc_gas_resistance(self, adc_gas, gas_range):
        """ガス抵抗値を計算（Ω）"""
        # BME680データシートに基づく計算
        lookup_table1 = [1.0, 1.0, 1.0, 1.0, 1.0, 0.99, 1.0, 0.992,
                         1.0, 1.0, 0.998, 0.995, 1.0, 0.99, 1.0, 1.0]
        lookup_table2 = [8000000.0, 4000000.0, 2000000.0, 1000000.0,
                         499500.4995, 248262.1648, 125000.0, 63004.03226,
                         31281.28128, 15625.0, 7812.5, 3906.25,
                         1953.125, 976.5625, 488.28125, 244.140625]

        var1 = (1340.0 + 5.0 * self.range_sw_err) * lookup_table1[gas_range]
        gas_resistance = var1 * lookup_table2[gas_range] / (adc_gas - 512.0 + var1)

        if gas_resistance < 0:
            gas_resistance = 0

        return gas_resistance


def connect_wifi():
    """WiFiに接続（複数SSIDに対応）"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # すでに接続済みの場合
    if wlan.isconnected():
        print(f"WiFi接続済み: {wlan.ifconfig()[0]}")
        return wlan

    print("WiFiネットワークをスキャン中...")
    available_networks = [net[0].decode() for net in wlan.scan()]
    print(f"検出されたネットワーク: {available_networks}")

    # 優先順位順にSSIDを試す
    for wifi in WIFI_NETWORKS:
        ssid = wifi["ssid"]
        password = wifi["password"]

        if ssid in available_networks:
            print(f"'{ssid}' に接続中...")
            wlan.connect(ssid, password)

            # 接続待機（最大20秒）
            for _ in range(20):
                if wlan.isconnected():
                    ip = wlan.ifconfig()[0]
                    print(f"WiFi接続成功: {ip}")
                    return wlan
                time.sleep(1)

            print(f"'{ssid}' への接続タイムアウト")
            wlan.disconnect()

    print("利用可能なWiFiネットワークに接続できませんでした")
    return None


def send_to_ambient(data, iaq):
    """Ambientにデータを送信"""
    url = f"http://ambidata.io/api/v2/channels/{AMBIENT_CHANNEL_ID}/data"

    # Ambient用データフォーマット（案2: IAQ重視）
    # d1: 温度, d2: 湿度, d3: IAQスコア, d4: 気圧, d5: ガス抵抗値
    payload = {
        "writeKey": AMBIENT_WRITE_KEY,
        "d1": round(data['temperature'], 1),
        "d2": round(data['humidity'], 1),
        "d4": round(data['pressure'], 1),
    }

    # IAQスコアがある場合は追加
    if iaq is not None:
        payload["d3"] = round(iaq, 0)

    # ガス抵抗値がある場合は追加
    if data['gas_resistance'] is not None and data['gas_resistance'] > 0:
        payload["d5"] = round(data['gas_resistance'], 0)

    try:
        response = urequests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        status = response.status_code
        response.close()

        if status == 200:
            print("Ambient送信成功")
            return True
        else:
            print(f"Ambient送信エラー: HTTP {status}")
            return False

    except Exception as e:
        print(f"Ambient送信例外: {e}")
        return False
    finally:
        gc.collect()


def estimate_iaq(gas_resistance, humidity):
    """
    簡易的な室内空気質（IAQ）スコアを推定
    ※ 実際のIAQ計算にはBosch独自のアルゴリズムが必要

    Returns: 0-500 (低いほど良い)
    """
    if gas_resistance is None:
        return None

    # 基準値（クリーンな空気での典型的な値）
    gas_baseline = 50000  # Ω
    hum_baseline = 40.0   # %

    # ガス抵抗の寄与（75%）
    gas_score = (gas_resistance / gas_baseline) * 100
    if gas_score > 100:
        gas_score = 100

    # 湿度の寄与（25%）- 40%が理想
    if humidity < hum_baseline:
        hum_score = (humidity / hum_baseline) * 100
    else:
        hum_score = (100 - humidity) / (100 - hum_baseline) * 100
    if hum_score > 100:
        hum_score = 100

    # 合成スコア（逆転: 高いほど良い → 低いほど良い）
    iaq = 500 - (gas_score * 0.75 + hum_score * 0.25) * 5

    return max(0, min(500, iaq))


def get_iaq_category(iaq):
    """IAQスコアからカテゴリを判定"""
    if iaq is None:
        return "計測中..."
    elif iaq <= 50:
        return "優良 (Excellent)"
    elif iaq <= 100:
        return "良好 (Good)"
    elif iaq <= 150:
        return "軽度汚染 (Lightly Polluted)"
    elif iaq <= 200:
        return "中度汚染 (Moderately Polluted)"
    elif iaq <= 300:
        return "重度汚染 (Heavily Polluted)"
    else:
        return "危険 (Severely Polluted)"


def main():
    """メイン関数"""
    print("=" * 50)
    print("BME680 環境センサー + Ambient送信")
    print("=" * 50)
    print()

    # 起動時の安定化待機
    print("システム初期化中...")
    time.sleep(5)

    # I2C初期化（ピン1=GP0=SDA, ピン2=GP1=SCL）
    # ハードウェアI2Cを使用
    i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)
    time.sleep(2)

    # I2Cスキャン
    print("I2Cデバイスをスキャン中...")
    devices = i2c.scan()
    if devices:
        print(f"検出されたデバイス: {[hex(d) for d in devices]}")
    else:
        print("I2Cデバイスが見つかりません")
        print("配線を確認してください")
        return

    print()

    # BME680初期化
    try:
        sensor = BME680(i2c)
    except RuntimeError as e:
        print(f"エラー: {e}")
        return

    print()

    # WiFi接続
    wlan = connect_wifi()
    if wlan is None:
        print("WiFi接続なしでローカル計測のみ実行します")

    print()
    print(f"計測を開始します（送信間隔: {SEND_INTERVAL}秒）")
    print("-" * 50)

    # ガスセンサーの安定化に時間がかかるため通知
    print("※ ガス抵抗値が安定するまで数分かかる場合があります")
    print()

    last_send_time = 0  # 初回は即座に送信

    try:
        while True:
            # データ読み取り
            data = sensor.read_data()

            # IAQ推定
            iaq = estimate_iaq(data['gas_resistance'], data['humidity'])
            iaq_category = get_iaq_category(iaq)

            # 現在時刻
            current_time = time.time()

            # コンソール出力
            print(f"【計測時刻】{current_time}")
            print(f"  温度:       {data['temperature']:.1f} °C")
            print(f"  湿度:       {data['humidity']:.1f} %RH")
            print(f"  気圧:       {data['pressure']:.1f} hPa")

            if data['gas_resistance'] is not None:
                print(f"  ガス抵抗:   {data['gas_resistance']:.0f} Ω")
                print(f"  IAQスコア:  {iaq:.0f}")
                print(f"  空気質:     {iaq_category}")
            else:
                print(f"  ガス抵抗:   計測中...")
                print(f"  ヒーター:   {'安定' if data['heat_stable'] else '加熱中'}")

            # Ambient送信（10分間隔）
            if wlan and wlan.isconnected():
                if current_time - last_send_time >= SEND_INTERVAL:
                    print("  → Ambientに送信中...")
                    if send_to_ambient(data, iaq):
                        last_send_time = current_time
                        next_send = SEND_INTERVAL
                    else:
                        next_send = 60  # エラー時は1分後にリトライ
                    print(f"  → 次回送信まで: {next_send}秒")
                else:
                    remaining = SEND_INTERVAL - (current_time - last_send_time)
                    print(f"  → 次回送信まで: {int(remaining)}秒")
            else:
                # WiFi再接続を試行
                print("  → WiFi未接続（再接続試行中...）")
                wlan = connect_wifi()

            print("-" * 50)

            # 30秒待機（ローカル表示用）
            time.sleep(30)

    except KeyboardInterrupt:
        print()
        print("計測を終了しました")


if __name__ == "__main__":
    main()
