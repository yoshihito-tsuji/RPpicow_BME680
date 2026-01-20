"""
現在の測定値を1回だけ取得して表示
"""
from machine import Pin, I2C
import time

# BME680 簡易読み取り
BME680_ADDR = 0x77
BME680_REG_CHIP_ID = 0xD0
BME680_REG_CTRL_HUM = 0x72
BME680_REG_CTRL_MEAS = 0x74
BME680_REG_CONFIG = 0x75
BME680_REG_DATA = 0x1D

# キャリブレーション設定
TEMP_OFFSET = 0.0
HUMIDITY_OFFSET = 9.4
PRESSURE_OFFSET = 27.1

print("\n=== 現在の測定値取得 ===")

# I2C初期化
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=100000)
time.sleep_ms(100)

# デバイススキャン
devices = i2c.scan()
print(f"検出デバイス: {[hex(d) for d in devices]}")

if BME680_ADDR not in devices and 0x76 not in devices:
    print("BME680が見つかりません")
else:
    addr = BME680_ADDR if BME680_ADDR in devices else 0x76
    print(f"BME680アドレス: {hex(addr)}")

    # キャリブレーションデータ読み取り
    coeff1 = i2c.readfrom_mem(addr, 0x89, 25)
    coeff2 = i2c.readfrom_mem(addr, 0xE1, 16)

    # 温度キャリブレーション
    par_t1 = (coeff1[0] | (coeff1[1] << 8))
    par_t2 = coeff1[2] | (coeff1[3] << 8)
    if par_t2 >= 0x8000:
        par_t2 = par_t2 - 0x10000
    par_t3 = coeff1[4]

    # 気圧キャリブレーション
    par_p1 = (coeff1[5] | (coeff1[6] << 8))
    par_p2 = coeff1[7] | (coeff1[8] << 8)
    if par_p2 >= 0x8000:
        par_p2 = par_p2 - 0x10000
    par_p3 = coeff1[9]
    par_p4 = coeff1[11] | (coeff1[12] << 8)
    if par_p4 >= 0x8000:
        par_p4 = par_p4 - 0x10000
    par_p5 = coeff1[13] | (coeff1[14] << 8)
    if par_p5 >= 0x8000:
        par_p5 = par_p5 - 0x10000
    par_p6 = coeff1[15]
    par_p7 = coeff1[16]
    par_p8 = coeff1[17] | (coeff1[18] << 8)
    if par_p8 >= 0x8000:
        par_p8 = par_p8 - 0x10000
    par_p9 = coeff1[19] | (coeff1[20] << 8)
    if par_p9 >= 0x8000:
        par_p9 = par_p9 - 0x10000
    par_p10 = coeff1[21]

    # 湿度キャリブレーション
    par_h1 = (coeff2[2] << 4) | (coeff2[1] & 0x0F)
    par_h2 = (coeff2[0] << 4) | (coeff2[1] >> 4)
    par_h3 = coeff2[3]
    par_h4 = coeff2[4]
    par_h5 = coeff2[5]
    par_h6 = coeff2[6]
    par_h7 = coeff2[7]

    # センサー設定
    i2c.writeto_mem(addr, BME680_REG_CTRL_HUM, bytes([0x02]))
    i2c.writeto_mem(addr, BME680_REG_CONFIG, bytes([0x04]))

    # 測定開始
    i2c.writeto_mem(addr, BME680_REG_CTRL_MEAS, bytes([0x55]))
    time.sleep_ms(200)

    # データ読み取り
    data = i2c.readfrom_mem(addr, BME680_REG_DATA, 15)

    adc_pres = (data[2] << 12) | (data[3] << 4) | (data[4] >> 4)
    adc_temp = (data[5] << 12) | (data[6] << 4) | (data[7] >> 4)
    adc_hum = (data[8] << 8) | data[9]

    # 温度計算
    var1 = (adc_temp / 16384.0 - par_t1 / 1024.0) * par_t2
    var2 = ((adc_temp / 131072.0 - par_t1 / 8192.0) *
            (adc_temp / 131072.0 - par_t1 / 8192.0) * par_t3 * 16.0)
    t_fine = var1 + var2
    temperature = t_fine / 5120.0

    # 気圧計算
    var1 = t_fine / 2.0 - 64000.0
    var2 = var1 * var1 * par_p6 / 131072.0
    var2 = var2 + var1 * par_p5 * 2.0
    var2 = var2 / 4.0 + par_p4 * 65536.0
    var1 = (par_p3 * var1 * var1 / 16384.0 + par_p2 * var1) / 524288.0
    var1 = (1.0 + var1 / 32768.0) * par_p1
    pressure = 1048576.0 - adc_pres
    pressure = (pressure - var2 / 4096.0) * 6250.0 / var1
    var1 = par_p9 * pressure * pressure / 2147483648.0
    var2 = pressure * par_p8 / 32768.0
    var3 = (pressure / 256.0) ** 3 * par_p10 / 131072.0
    pressure = (pressure + (var1 + var2 + var3 + par_p7 * 128.0) / 16.0) / 100.0

    # 湿度計算
    temp_comp = t_fine / 5120.0
    var1 = adc_hum - (par_h1 * 16.0 + (par_h3 / 2.0) * temp_comp)
    var2 = var1 * (par_h2 / 262144.0 * (1.0 + (par_h4 / 16384.0) * temp_comp +
           (par_h5 / 1048576.0) * temp_comp * temp_comp))
    var3 = par_h6 / 16384.0
    var4 = par_h7 / 2097152.0
    humidity = var2 + (var3 + var4 * temp_comp) * var2 * var2

    if humidity > 100.0:
        humidity = 100.0
    elif humidity < 0.0:
        humidity = 0.0

    # キャリブレーション適用
    temp_cal = temperature + TEMP_OFFSET
    hum_cal = humidity + HUMIDITY_OFFSET
    pres_cal = pressure + PRESSURE_OFFSET

    print(f"\n【現在の測定値】")
    print(f"  温度: {temp_cal:.1f} °C (生値: {temperature:.1f}°C)")
    print(f"  湿度: {hum_cal:.1f} %RH (生値: {humidity:.1f}%RH)")
    print(f"  気圧: {pres_cal:.1f} hPa (生値: {pressure:.1f}hPa)")
    print(f"\n【オフセット値】")
    print(f"  温度: {TEMP_OFFSET:+.1f}°C")
    print(f"  湿度: {HUMIDITY_OFFSET:+.1f}%RH")
    print(f"  気圧: {PRESSURE_OFFSET:+.1f}hPa")
    print("=" * 40)

print("\n測定完了")
