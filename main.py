import json
import os
import math
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton
from kivy.core.window import Window
from kivy.utils import platform
from kivy.clock import Clock, mainthread
import time

if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method
    BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
    MediaPlayer = autoclass('android.media.MediaPlayer')
    AudioManager = autoclass('android.media.AudioManager')
    Context = autoclass('android.content.Context')
    Vibrator = autoclass('android.os.Vibrator')

def get_config_path():
    return os.path.join(App.get_running_app().user_data_dir, "anti_lost_config.json")

def load_config():
    default = {"mac_address": "", "rssi_threshold": -85}
    if os.path.exists(get_config_path()):
        with open(get_config_path(), "r") as f: return {**default, **json.load(f)}
    return default

class BLEScanCallback(PythonJavaClass):
    __javainterfaces__ = ['android/bluetooth/BluetoothAdapter$LeScanCallback']
    __javacontext__ = 'app'

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    @java_method('(Landroid/bluetooth/BluetoothDevice;I[B)V')
    def onLeScan(self, device, rssi, scanRecord):
        if device: self.callback(device.getAddress(), rssi)

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_seen = time.time()
        self.is_monitoring = False
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        self.status = Label(text="ОЧІКУВАННЯ...", font_size='20sp')
        layout.add_widget(self.status)
        
        self.btn_toggle = Button(text="ЗАПУСТИТИ МОНІТОРИНГ", size_hint_y=0.2)
        self.btn_toggle.bind(on_press=self.toggle_monitoring)
        layout.add_widget(self.btn_toggle)
        
        self.add_widget(layout)
        
        # Ініціалізація аудіо
        self.player = MediaPlayer()
        self.player.setAudioStreamType(AudioManager.STREAM_ALARM)

    def toggle_monitoring(self, instance):
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            self.btn_toggle.text = "ЗУПИНИТИ"
            self.adapter = BluetoothAdapter.getDefaultAdapter()
            self.callback = BLEScanCallback(self.on_ble_found)
            self.adapter.startLeScan(self.callback)
            Clock.schedule_interval(self.check_status, 1)
        else:
            self.btn_toggle.text = "ЗАПУСТИТИ"
            Clock.unschedule(self.check_status)
            self.adapter.stopLeScan(self.callback)

    def on_ble_found(self, address, rssi):
        config = load_config()
        if address == config.get("mac_address"):
            self.last_seen = time.time()

    def check_status(self, dt):
        config = load_config()
        if (time.time() - self.last_seen) > 5.0:
            self.status.text = "🚨 ТРИВОГА! ЗВ'ЯЗОК ВТРАЧЕНО"
            self.status.color = (1, 0, 0, 1)
            if not self.player.isPlaying(): self.player.start()
        else:
            self.status.text = "🟢 СТАБІЛЬНО"
            self.status.color = (0, 1, 0, 1)
            if self.player.isPlaying(): self.player.pause()

class AntiLostApp(App):
    def build(self):
        return MainScreen()

if __name__ == "__main__":
    AntiLostApp().run()
