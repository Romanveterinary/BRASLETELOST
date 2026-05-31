import os
import time
import json
import traceback
from jnius import autoclass, PythonJavaClass, java_method

PythonService = autoclass('org.kivy.android.PythonService')
service_context = PythonService.mService
context = service_context.getApplicationContext()

# --- ПОВІДОМЛЕННЯ В ШТОРЦІ (FOREGROUND) ---
NotificationBuilder = autoclass('android.app.Notification$Builder')
NotificationChannel = autoclass('android.app.NotificationChannel')
channel_id = "vettrack_channel"
channel = NotificationChannel(channel_id, "VetTrack Service", 2)
manager = context.getSystemService("notification")
manager.createNotificationChannel(channel)

builder = NotificationBuilder(context, channel_id)
builder.setContentTitle("VetTrack Anti-Lost")
builder.setContentText("Моніторинг BLE пристрою...")
builder.setSmallIcon(0x01080038)
service_context.startForeground(1, builder.build())

# --- WAKE LOCK (БЛОКУВАННЯ СНУ) ---
try:
    PowerManager = autoclass('android.os.PowerManager')
    power_manager = context.getSystemService("power")
    wake_lock = power_manager.newWakeLock(1, "VetTrack::BleScanLock")
    wake_lock.acquire()
except Exception as e:
    pass

BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
Intent = autoclass('android.content.Intent')
MediaPlayer = autoclass('android.media.MediaPlayer')

files_dir = service_context.getFilesDir().getAbsolutePath()
CONFIG_FILE = os.path.join(files_dir, "anti_lost_config.json")
STATE_FILE = os.path.join(files_dir, "live_state.json")

# Глобальні змінні
last_seen_time = time.time()
last_seen_rssi = -100
smoothed_rssi = None # Програмний амортизатор

# --- СТАРИЙ СКАРНЕР (Для дуже старих телефонів) ---
class BLEScanCallback(PythonJavaClass):
    __javainterfaces__ = ['android/bluetooth/BluetoothAdapter$LeScanCallback']
    __javacontext__ = 'app'

    def __init__(self, target_mac):
        super().__init__()
        self.target_mac = target_mac

    @java_method('(Landroid/bluetooth/BluetoothDevice;I[B)V')
    def onLeScan(self, device, rssi, scanRecord):
        global last_seen_time, last_seen_rssi, smoothed_rssi
        if device:
            address = device.getAddress()
            if address == self.target_mac:
                last_seen_time = time.time()
                if smoothed_rssi is None:
                    smoothed_rssi = rssi
                else:
                    smoothed_rssi = (0.2 * rssi) + (0.8 * smoothed_rssi)
                last_seen_rssi = int(smoothed_rssi)

def load_config():
    default_config = {
        "mac_address": "",
        "rssi_threshold": -85,
        "ping_interval": 2,
        "timeout_limit": 5,
        "alarm_duration": 2,
        "melody_path": ""
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                default_config.update(data)
        except Exception:
            pass
    return default_config

def write_state(status_text, rssi_val):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"status": status_text, "rssi": rssi_val}, f)
    except:
        pass

def main():
    global last_seen_time, last_seen_rssi, smoothed_rssi
    write_state("РАДАР ЗАПУЩЕНО, ШУКАЮ...", -100)
    
    config = load_config()
    target_mac = config.get("mac_address", "").strip()
    
    if not target_mac:
        write_state("ПОМИЛКА: НЕМАЄ MAC-АДРЕСИ", -100)
        return

    adapter = BluetoothAdapter.getDefaultAdapter()
    if not adapter:
        write_state("ПОМИЛКА: BLUETOOTH ВИМКНЕНО", -100)
        return

    # --- ЗАПУСК СУЧАСНОГО АПАРАТНОГО СКАНЕРА (ФОНОВИЙ РЕЖИМ) ---
    try:
        Build = autoclass('android.os.Build$VERSION')
        modern_scanner_started = False
        
        if Build.SDK_INT >= 26: # API 26 (Android 8.0) і вище
            try:
                from android.broadcast import BroadcastReceiver
                
                # Ця функція ловитиме сигнали, навіть якщо екран чорний
                def on_ble_found(context, intent):
                    global last_seen_time, last_seen_rssi, smoothed_rssi
                    action = intent.getAction()
                    if action == "com.romanveterinary.BLE_SCAN_RESULT":
                        results = intent.getParcelableArrayListExtra("android.bluetooth.le.extra.LIST_SCAN_RESULT")
                        if results and results.size() > 0:
                            for i in range(results.size()):
                                scan_result = results.get(i)
                                rssi = scan_result.getRssi()
                                last_seen_time = time.time()
                                if smoothed_rssi is None:
                                    smoothed_rssi = rssi
                                else:
                                    smoothed_rssi = (0.2 * rssi) + (0.8 * smoothed_rssi)
                                last_seen_rssi = int(smoothed_rssi)
                                
                br = BroadcastReceiver(on_ble_found, actions=['com.romanveterinary.BLE_SCAN_RESULT'])
                
                IntentFilter = autoclass('android.content.IntentFilter')
                filter_intent = IntentFilter()
                filter_intent.addAction('com.romanveterinary.BLE_SCAN_RESULT')
                
                # Реєструємо слухача напряму в сервісі (захищає від зупинок)
                if Build.SDK_INT >= 33:
                    service_context.registerReceiver(br.receiver, filter_intent, 4) # 4 = RECEIVER_NOT_EXPORTED
                else:
                    service_context.registerReceiver(br.receiver, filter_intent)
                    
                PendingIntent = autoclass('android.app.PendingIntent')
                ArrayList = autoclass('java.util.ArrayList')
                ScanFilterBuilder = autoclass('android.bluetooth.le.ScanFilter$Builder')
                ScanSettingsBuilder = autoclass('android.bluetooth.le.ScanSettings$Builder')
                ScanSettings = autoclass('android.bluetooth.le.ScanSettings')
                
                intent = Intent("com.romanveterinary.BLE_SCAN_RESULT")
                intent.setPackage(service_context.getPackageName())
                
                flag = 134217728 # FLAG_UPDATE_CURRENT
                if Build.SDK_INT >= 31:
                    flag |= 33554432 # FLAG_MUTABLE
                    
                pending_intent = PendingIntent.getBroadcast(service_context, 0, intent, flag)
                
                # ОСЬ ВІН - АПАРАТНИЙ ФІЛЬТР (Дозволяє сканування при вимкненому екрані)
                fb = ScanFilterBuilder()
                fb.setDeviceAddress(target_mac)
                filters = ArrayList()
                filters.add(fb.build())
                
                sb = ScanSettingsBuilder()
                sb.setScanMode(1) # 1 = SCAN_MODE_BALANCED (Оптимально для фону)
                settings = sb.build()
                
                scanner = adapter.getBluetoothLeScanner()
                if scanner:
                    scanner.startScan(filters, settings, pending_intent)
                    modern_scanner_started = True
                    
            except Exception as e:
                modern_scanner_started = False
                
        if not modern_scanner_started:
            scan_callback = BLEScanCallback(target_mac)
            adapter.startLeScan(scan_callback)
            
    except Exception as e:
        write_state(f"SCAN ERROR: {e}", -100)

    # --- НАЛАШТУВАННЯ МЕЛОДІЇ ---
    player = MediaPlayer()
    alarm_playing = False
    disconnect_start_time = None
    
    try:
        melody = config.get("melody_path", "").strip()
        if melody and os.path.exists(melody):
            player.setDataSource(melody)
        else:
            app_dir = os.path.dirname(__file__)
            player.setDataSource(os.path.join(app_dir, "sonar.wav"))
        player.prepare()
        player.setLooping(True)
    except Exception:
        pass

    # --- ГОЛОВНИЙ ЦИКЛ ПЕРЕВІРКИ ---
    while True:
        current_time = time.time()
        config = load_config() 
        
        target_rssi = config["rssi_threshold"]
        timeout_limit = config["timeout_limit"]
        max_alarm_duration = config["alarm_duration"] * 60
        ping_interval = config["ping_interval"]
        
        # Динамічна толерантність
        silence_tolerance = max(15.0, ping_interval * 3.0)
        device_missing = (current_time - last_seen_time) > silence_tolerance
        
        current_status = "НЕВІДОМО"
        
        if device_missing or last_seen_rssi < target_rssi:
            if disconnect_start_time is None:
                disconnect_start_time = current_time
                
            elapsed = current_time - disconnect_start_time
            
            if elapsed >= timeout_limit:
                current_status = "🚨 ТРИВОГА! ЗВ'ЯЗОК ВТРАЧЕНО 🚨"
                if not alarm_playing:
                    try:
                        intent = Intent()
                        intent.setAction("com.romanveterinary.LOST_ALARM")
                        service_context.sendBroadcast(intent)
                    except Exception:
                        pass
                        
                    try:
                        player.start()
                        alarm_playing = True
                    except:
                        pass
                        
                if alarm_playing and elapsed >= (timeout_limit + max_alarm_duration):
                    try:
                        player.pause()
                        alarm_playing = False
                    except:
                        pass
            else:
                time_left = int(timeout_limit - elapsed)
                current_status = f"ВТРАЧАЮ ЗВ'ЯЗОК! Сирена через {time_left} сек"
        else:
            current_status = "🟢 ЗВ'ЯЗОК СТАБІЛЬНИЙ"
            if alarm_playing:
                try:
                    player.pause()
                    player.seekTo(0)
                    alarm_playing = False
                except:
                    pass
            disconnect_start_time = None

        write_state(current_status, last_seen_rssi)
        time.sleep(ping_interval)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        write_state(f"FATAL ERROR: {e}", -100)
