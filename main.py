import traceback

try:
    import json
    import os
    import time
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
    from kivy.core.audio import SoundLoader
    from kivy.utils import platform
    from kivy.clock import Clock, mainthread

    # Фіксуємо розмір тільки для ПК
    if platform not in ('android', 'ios'):
        Window.size = (400, 720)

    # Налаштування нативного Bluetooth для Android через інтерфейс LeScanCallback
    if platform == "android":
        from jnius import autoclass, PythonJavaClass, java_method
        
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        
        # Створюємо Python-клас, який виконує роль Java-інтерфейсу
        class BLEScanCallback(PythonJavaClass):
            __javainterfaces__ = ['android/bluetooth/BluetoothAdapter$LeScanCallback']
            __javacontext__ = 'app'

            def __init__(self, ui_callback):
                super().__init__()
                self.ui_callback = ui_callback

            @java_method('(Landroid/bluetooth/BluetoothDevice;I[B)V')
            def onLeScan(self, device, rssi, scanRecord):
                if device:
                    address = device.getAddress()
                    name = device.getName()
                    # Передаємо дані в інтерфейс
                    self.ui_callback(address, name, rssi)

    def get_config_path():
        return os.path.join(App.get_running_app().user_data_dir, "anti_lost_config.json")

    class MainScreen(Screen):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.monitor_event = None  
            self.disconnect_start_time = None
            self.alarm_start_time = None  
            self.target_mac = ""
            self.last_seen_time = 0
            self.last_seen_rssi = -100
            
            self.alarm_sound = SoundLoader.load('sonar.wav')
            if self.alarm_sound:
                self.alarm_sound.loop = True
                
            # Ініціалізація Bluetooth адаптера
            self.bluetooth_adapter = None
            self.scan_callback = None
            if platform == "android":
                self.bluetooth_adapter = BluetoothAdapter.getDefaultAdapter()
            
            # Пропорційний макет
            layout = BoxLayout(orientation='vertical', padding=30, spacing=15)

            layout.add_widget(Label(text="VET-TRACK: ANTI-LOST", font_size='24sp', bold=True, size_hint_y=0.1))

            self.status_label = Label(text="МОНІТОРИНГ ВИМКНЕНО", font_size='18sp', bold=True, color=(0.5, 0.5, 0.5, 1), size_hint_y=0.1)
            layout.add_widget(self.status_label)

            box_rssi = BoxLayout(orientation='vertical', size_hint_y=0.15)
            box_rssi.add_widget(Label(text="СИЛА СИГНАЛУ (RSSI / ВІДСТАНЬ)", font_size='14sp', bold=True))
            self.rssi_slider = Slider(min=-95, max=-60, value=-85, step=1)
            self.rssi_slider.bind(value=self.on_rssi_change)
            self.rssi_info = Label(text="Поріг спрацювання: -85 dBm (~15м)", font_size='12sp', color=(0.7, 0.7, 0.7, 1))
            box_rssi.add_widget(self.rssi_slider)
            box_rssi.add_widget(self.rssi_info)
            layout.add_widget(box_rssi)

            box_ping = BoxLayout(orientation='vertical', size_hint_y=0.15)
            box_ping.add_widget(Label(text="ІНТЕРВАЛ ОПИТУВАННЯ", font_size='14sp', bold=True))
            self.ping_slider = Slider(min=1, max=10, value=2, step=1)
            self.ping_slider.bind(value=self.on_ping_change)
            self.ping_info = Label(text="Перевірка кожні: 2 сек", font_size='12sp', color=(0.7, 0.7, 0.7, 1))
            box_ping.add_widget(self.ping_slider)
            box_ping.add_widget(self.ping_info)
            layout.add_widget(box_ping)

            box_time = BoxLayout(orientation='vertical', size_hint_y=0.15)
            box_time.add_widget(Label(text="ЗАТРИМКА ТРИВОГИ", font_size='14sp', bold=True))
            self.time_slider = Slider(min=2, max=30, value=5, step=1)
            self.time_slider.bind(value=self.on_time_change)
            self.time_info = Label(text="Час очікування: 5 секунд", font_size='12sp', color=(0.7, 0.7, 0.7, 1))
            box_time.add_widget(self.time_slider)
            box_time.add_widget(self.time_info)
            layout.add_widget(box_time)

            box_dur = BoxLayout(orientation='vertical', size_hint_y=0.15)
            box_dur.add_widget(Label(text="ТРИВАЛІСТЬ ЗВУЧАННЯ СИРЕНИ", font_size='14sp', bold=True))
            self.duration_slider = Slider(min=1, max=5, value=2, step=1)
            self.duration_slider.bind(value=self.on_duration_change)
            self.duration_info = Label(text="Автовимкнення через: 2 хв", font_size='12sp', color=(0.7, 0.7, 0.7, 1))
            box_dur.add_widget(self.duration_slider)
            box_dur.add_widget(self.duration_info)
            layout.add_widget(box_dur)

            self.btn_start = Button(text="УВІМКНУТИ МОНІТОРИНГ", font_size='16sp', bold=True, background_color=(0.2, 0.8, 0.2, 1), size_hint_y=0.1)
            self.btn_start.bind(on_press=self.start_monitoring)
            layout.add_widget(self.btn_start)

            self.btn_stop = Button(text="ВИМКНУТИ МОНІТОРИНГ", font_size='16sp', bold=True, background_color=(0.8, 0.2, 0.2, 1), size_hint_y=0.1, disabled=True)
            self.btn_stop.bind(on_press=self.stop_monitoring)
            layout.add_widget(self.btn_stop)

            btn_settings = Button(text="НАЛАШТУВАННЯ ПРИСТРОЮ", font_size='14sp', background_color=(0.3, 0.3, 0.3, 1), size_hint_y=0.1)
            btn_settings.bind(on_press=self.go_to_settings)
            layout.add_widget(btn_settings)

            self.add_widget(layout)

        def on_rssi_change(self, instance, value): self.rssi_info.text = f"Поріг спрацювання: {int(value)} dBm"
        def on_ping_change(self, instance, value): self.ping_info.text = f"Перевірка кожні: {int(value)} сек"
        def on_time_change(self, instance, value): self.time_info.text = f"Час очікування: {int(value)} секунд"
        def on_duration_change(self, instance, value): self.duration_info.text = f"Автовимкнення через: {int(value)} хв"

        @mainthread
        def on_device_found(self, address, name, rssi):
            if address == self.target_mac:
                self.last_seen_time = time.time()
                self.last_seen_rssi = rssi

        def start_monitoring(self, instance):
            self.target_mac = ""
            config_file = get_config_path()
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r") as f:
                        self.target_mac = json.load(f).get("mac_address", "").strip()
                except Exception:
                    pass

            if not self.target_mac:
                self.status_label.text = "СПОЧАТКУ ВИБЕРІТЬ ПРИСТРІЙ В НАЛАШТУВАННЯХ!"
                self.status_label.font_size = '12sp'
                self.status_label.color = (1, 0.2, 0.2, 1)
                return

            self.btn_start.disabled = True
            self.btn_stop.disabled = False
            self.toggle_sliders(disabled=True)
            
            self.status_label.font_size = '18sp'
            self.status_label.text = "ПОШУК БРАСЛЕТА..."
            self.status_label.color = (0.2, 0.7, 0.8, 1)
            self.disconnect_start_time = None
            self.alarm_start_time = None
            self.last_seen_time = time.time()
            
            # Запускаємо нативний сканер
            if self.bluetooth_adapter:
                self.scan_callback = BLEScanCallback(self.on_device_found)
                self.bluetooth_adapter.startLeScan(self.scan_callback)
            
            self.monitor_event = Clock.schedule_interval(self.check_status, self.ping_slider.value)

        def check_status(self, dt):
            current_time = time.time()
            target_rssi = self.rssi_slider.value
            timeout_limit = self.time_slider.value
            max_alarm_duration = self.duration_slider.value * 60

            if self.alarm_start_time and (current_time - self.alarm_start_time >= max_alarm_duration):
                if self.alarm_sound and self.alarm_sound.state == 'play':
                    self.alarm_sound.stop()
                self.status_label.text = "ТРИВОГА ВИМКНЕНА ЗА ТАЙМАУТОМ"
                self.status_label.color = (0.7, 0.4, 0.7, 1)
                return

            device_missing = (current_time - self.last_seen_time) > 2.0
            
            if device_missing or self.last_seen_rssi < target_rssi:
                if self.disconnect_start_time is None:
                    self.disconnect_start_time = current_time
                
                elapsed = current_time - self.disconnect_start_time
                self.status_label.text = f"ВТРАТА ЗВ'ЯЗКУ! ({int(elapsed)}с)"
                self.status_label.color = (0.9, 0.4, 0.1, 1)

                if elapsed >= timeout_limit:
                    self.status_label.text = "ТРИВОГА! ПРИСТРІЙ ВІДСУТНІЙ!"
                    self.status_label.color = (1, 0, 0, 1)
                    
                    if self.alarm_start_time is None:
                        self.alarm_start_time = current_time 
                    
                    if self.alarm_sound and self.alarm_sound.state == 'stop':
                        self.alarm_sound.play()
            else:
                if self.alarm_sound and self.alarm_sound.state == 'play':
                    self.alarm_sound.stop()
                self.disconnect_start_time = None
                self.alarm_start_time = None
                self.status_label.text = f"ПРИСТРІЙ ПОРУЧ | Сигнал: {self.last_seen_rssi} dBm"
                self.status_label.color = (0.2, 0.8, 0.2, 1)

        def stop_monitoring(self, instance):
            if self.monitor_event:
                self.monitor_event.cancel()
                self.monitor_event = None
                
            if self.bluetooth_adapter and self.scan_callback:
                self.bluetooth_adapter.stopLeScan(self.scan_callback)
                self.scan_callback = None
                
            if self.alarm_sound and self.alarm_sound.state == 'play':
                self.alarm_sound.stop()
                
            self.status_label.text = "МОНІТОРИНГ ВИМКНЕНО"
            self.status_label.font_size = '18sp'
            self.status_label.color = (0.5, 0.5, 0.5, 1)
            self.btn_start.disabled = False
            self.btn_stop.disabled = True
            self.toggle_sliders(disabled=False)

        def toggle_sliders(self, disabled):
            self.rssi_slider.disabled = disabled
            self.ping_slider.disabled = disabled
            self.time_slider.disabled = disabled
            self.duration_slider.disabled = disabled

        def go_to_settings(self, instance):
            self.manager.current = 'settings'

    class SettingsScreen(Screen):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.found_devices = {}
            
            # Ініціалізація Bluetooth адаптера
            self.bluetooth_adapter = None
            self.scan_callback = None
            if platform == "android":
                self.bluetooth_adapter = BluetoothAdapter.getDefaultAdapter()
            
            layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

            layout.add_widget(Label(text="НАЛАШТУВАННЯ", font_size='20sp', bold=True, size_hint_y=0.1))

            layout.add_widget(Label(text="Bluetooth MAC-адреса:", font_size='14sp', size_hint_y=0.05, halign='left'))
            self.mac_input = TextInput(text="", multiline=False, font_size='14sp', size_hint_y=0.1)
            layout.add_widget(self.mac_input)

            layout.add_widget(Label(text="Ключ авторизації (Auth Key):", font_size='14sp', size_hint_y=0.05))
            self.key_input = TextInput(text="", multiline=False, font_size='14sp', size_hint_y=0.1)
            layout.add_widget(self.key_input)

            layout.add_widget(Label(text="БЛЮТУЗ РАДАР (Клікни на пристрій):", font_size='12sp', color=(0.2, 0.7, 0.8, 1), size_hint_y=0.05))
            
            self.scroll_view = ScrollView(size_hint=(1, 0.35))
            self.devices_container = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
            self.devices_container.bind(minimum_height=self.devices_container.setter('height'))
            
            self.scroll_view.add_widget(self.devices_container)
            layout.add_widget(self.scroll_view)

            self.btn_scan = Button(text="ЗАПУСТИТИ РАДАР ЕФІРУ", font_size='14sp', background_color=(0.2, 0.6, 0.8, 1), size_hint_y=0.1)
            self.btn_scan.bind(on_press=self.start_ble_scan)
            layout.add_widget(self.btn_scan)

            btn_save = Button(text="ЗБЕРЕГТИ КОНФІГ", font_size='16sp', bold=True, background_color=(0.2, 0.8, 0.2, 1), size_hint_y=0.1)
            btn_save.bind(on_press=self.save_config)
            layout.add_widget(btn_save)

            self.add_widget(layout)
            
        def on_enter(self):
            self.load_config()
            
        @mainthread
        def on_device_found(self, address, name, rssi):
            if address not in self.found_devices:
                self.found_devices[address] = True
                dev_name = name if name else "Невідомий пристрій"
                btn_text = f"{dev_name} \n[{address}] | {rssi} dBm"
                
                dev_btn = ToggleButton(text=btn_text, group='ble_dev', size_hint=(1, None), height=100, font_size='14sp')
                dev_btn.bind(on_press=lambda inst, addr=address: self.select_device(addr))
                
                self.devices_container.add_widget(dev_btn)
                self.devices_container.height += 105

        def start_ble_scan(self, instance):
            if not self.bluetooth_adapter:
                lbl = Label(text="Помилка: Немає доступу до Bluetooth", font_size='12sp', size_hint_y=None, height=40)
                self.devices_container.add_widget(lbl)
                self.devices_container.height += 40
                return

            self.btn_scan.disabled = True
            self.btn_scan.text = "ШУКАЮ ПРИСТРОЇ (4 СЕК)..."
            self.devices_container.clear_widgets()
            self.devices_container.height = 0
            self.found_devices.clear()
            
            # Запускаємо стабільне нативне сканування
            self.scan_callback = BLEScanCallback(self.on_device_found)
            self.bluetooth_adapter.startLeScan(self.scan_callback)
            
            Clock.schedule_once(self.stop_ble_scan, 4.0)

        def stop_ble_scan(self, dt):
            if self.bluetooth_adapter and self.scan_callback:
                self.bluetooth_adapter.stopLeScan(self.scan_callback)
                self.scan_callback = None
            
            self.btn_scan.disabled = False
            self.btn_scan.text = "ЗАПУСТИТИ РАДАР ЕФІРУ"
            
            if not self.found_devices:
                lbl = Label(text="Нічого не знайдено. Увімкніть GPS та Bluetooth.", font_size='12sp', size_hint_y=None, height=40)
                self.devices_container.add_widget(lbl)
                self.devices_container.height += 40

        def select_device(self, address):
            self.mac_input.text = address

        def save_config(self, instance):
            config_data = {"mac_address": self.mac_input.text.strip(), "auth_key": self.key_input.text.strip()}
            config_file = get_config_path()
            with open(config_file, "w") as f:
                json.dump(config_data, f)
            self.manager.current = 'main'

        def load_config(self):
            config_file = get_config_path()
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r") as f:
                        data = json.load(f)
                        self.mac_input.text = data.get("mac_address", "")
                        self.key_input.text = data.get("auth_key", "")
                except Exception:
                    pass

    class AntiLostApp(App):
        def build(self):
            if platform == "android":
                from android.permissions import request_permissions, Permission
                request_permissions([
                    Permission.BLUETOOTH,
                    Permission.BLUETOOTH_ADMIN,
                    Permission.BLUETOOTH_SCAN,
                    Permission.BLUETOOTH_CONNECT,
                    Permission.ACCESS_FINE_LOCATION,
                    Permission.ACCESS_COARSE_LOCATION
                ])

            self.title = "VetTrack Anti-Lost Radar"
            sm = ScreenManager()
            sm.add_widget(MainScreen(name='main'))
            sm.add_widget(SettingsScreen(name='settings'))
            return sm

    if __name__ == "__main__":
        AntiLostApp().run()

except Exception as e:
    from kivy.app import App
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView
    from kivy.core.window import Window

    class ErrorApp(App):
        def build(self):
            sv = ScrollView()
            error_text = traceback.format_exc()
            lbl = Label(
                text=f"FATAL ERROR:\n\n{error_text}", 
                text_size=(Window.width * 0.9, None), 
                size_hint_y=None, 
                color=(1, 0.2, 0.2, 1),
                valign='top'
            )
            lbl.bind(texture_size=lbl.setter('size'))
            sv.add_widget(lbl)
            return sv

    ErrorApp().run()
