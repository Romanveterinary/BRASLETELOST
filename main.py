import json, os, math, time
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

if platform == "android":
    from jnius import autoclass, PythonJavaClass, java_method
    BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
    MediaPlayer = autoclass('android.media.MediaPlayer')
    AudioManager = autoclass('android.media.AudioManager')
    Context = autoclass('android.content.Context')
    Vibrator = autoclass('android.os.Vibrator')

# --- Логіка конфігу ---
def get_config_path(): return os.path.join(App.get_running_app().user_data_dir, "anti_lost_config.json")

def load_full_config():
    default = {"mac_address": "", "rssi_threshold": -85, "ping_interval": 2, "timeout_limit": 5, "melody_path": ""}
    if os.path.exists(get_config_path()):
        with open(get_config_path(), "r") as f: return {**default, **json.load(f)}
    return default

# --- Основний екран ---
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_monitoring = False
        self.last_seen = time.time()
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        self.status = Label(text="ОЧІКУВАННЯ...", font_size='20sp')
        self.layout.add_widget(self.status)
        
        self.btn_toggle = Button(text="ЗАПУСТИТИ МОНІТОРИНГ", size_hint_y=0.2)
        self.btn_toggle.bind(on_press=self.toggle_monitoring)
        self.layout.add_widget(self.btn_toggle)
        
        btn_settings = Button(text="НАЛАШТУВАННЯ", size_hint_y=0.1)
        btn_settings.bind(on_press=lambda x: setattr(self.manager, 'current', 'settings'))
        self.layout.add_widget(btn_settings)
        self.add_widget(self.layout)
        
        # Аудіо
        self.player = MediaPlayer()
        self.player.setAudioStreamType(AudioManager.STREAM_ALARM)

    def toggle_monitoring(self, instance):
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            self.btn_toggle.text = "ЗУПИНИТИ"
            self.adapter = BluetoothAdapter.getDefaultAdapter()
            self.callback = self.BLECallback(self.on_ble_found)
            self.adapter.startLeScan(self.callback)
            Clock.schedule_interval(self.check_status, 1)
        else:
            self.btn_toggle.text = "ЗАПУСТИТИ МОНІТОРИНГ"
            Clock.unschedule(self.check_status)
            if hasattr(self, 'adapter'): self.adapter.stopLeScan(self.callback)

    class BLECallback(PythonJavaClass):
        __javainterfaces__ = ['android/bluetooth/BluetoothAdapter$LeScanCallback']
        def __init__(self, callback): super().__init__(); self.callback = callback
        @java_method('(Landroid/bluetooth/BluetoothDevice;I[B)V')
        def onLeScan(self, device, rssi, scanRecord): self.callback(device.getAddress(), rssi)

    def on_ble_found(self, address, rssi):
        if address == load_full_config()["mac_address"]: self.last_seen = time.time()

    def check_status(self, dt):
        config = load_full_config()
        if (time.time() - self.last_seen) > config["timeout_limit"]:
            self.status.text = "🚨 ТРИВОГА!"
            if not self.player.isPlaying(): self.player.start()
        else:
            self.status.text = "🟢 СТАБІЛЬНО"
            if self.player.isPlaying(): self.player.pause()

# --- Екран налаштувань (Повертаємо твій інтерфейс) ---
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20)
        self.mac_input = TextInput(text=load_full_config()["mac_address"], hint_text="MAC-адреса")
        layout.add_widget(self.mac_input)
        btn_save = Button(text="ЗБЕРЕГТИ", on_press=self.save)
        layout.add_widget(btn_save)
        self.add_widget(layout)

    def save(self, instance):
        with open(get_config_path(), "w") as f: json.dump({"mac_address": self.mac_input.text}, f)
        self.manager.current = 'main'

class AntiLostApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(SettingsScreen(name='settings'))
        return sm

AntiLostApp().run()
