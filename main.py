import traceback

try:
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

    if platform not in ('android', 'ios'):
        Window.size = (400, 720)

    if platform == "android":
        from jnius import autoclass, PythonJavaClass, java_method
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        
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
                    self.ui_callback(address, name, rssi)

    def get_config_path():
        return os.path.join(App.get_running_app().user_data_dir, "anti_lost_config.json")

    def get_state_path():
        return os.path.join(App.get_running_app().user_data_dir, "live_state.json")

    def load_full_config():
        default_config = {
            "mac_address": "",
            "rssi_threshold": -85,
            "ping_interval": 2,
            "timeout_limit": 5,
            "alarm_duration": 2,
            "melody_path": ""
        }
        config_file = get_config_path()
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    data = json.load(f)
                    default_config.update(data)
            except Exception:
                pass
        return default_config

    def save_full_config(data):
        config = load_full_config()
        config.update(data)
        with open(get_config_path(), "w") as f:
            json.dump(config, f)

    def calc_distance(rssi):
        tx_power = -59
        n = 2.5
        if rssi == 0:
            return 0.0
        distance = math.pow(10, (tx_power - rssi) / (10 * n))
        return round(distance, 1)

    class MainScreen(Screen):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            layout = BoxLayout(orientation='vertical', padding=30, spacing=15)

            layout.add_widget(Label(text="VET-TRACK: ANTI-LOST", font_size='24sp', bold=True, size_hint_y=0.1))

            self.status_label = Label(text="ГОТОВИЙ ДО ЗАПУСКУ ФОНУ", font_size='14sp', bold=True, color=(0.5, 0.5, 0.5, 1), size_hint_y=0.1)
            layout.add_widget(self.status_label)

            self.target_label = Label(text="ПРИСТРІЙ НЕ ВИБРАНО", font_size='22sp', bold=True, color=(0.2, 0.8, 0.2, 0.2), size_hint_y=0.1)
            layout.add_widget(self.target_label)

            config = load_full_config()

            box_rssi = BoxLayout(orientation='vertical', size_hint_y=0.15)
            box_rssi.add_widget(Label(text="СИЛА СИГНАЛУ (RSSI / ВІДСТАНЬ)", font_size='14sp', bold=True))
            self.rssi_slider = Slider(min=-95, max=-60, value=config["rssi_threshold"], step=1)
            self.rssi_slider.bind(value=self.on_rssi_change)
            
            init_dist = calc_distance(self.rssi_slider.value)
            self.rssi_info = Label(text=f"Поріг: {int(self.rssi_slider.value)} dBm (~{init_dist} м)", font_size='12sp', color=(0.7, 0.7, 0.7, 1))
            box_rssi.add_widget(self.rssi_slider)
            box_rssi.add_widget(self.rssi_info)
            layout.add_widget(box_rssi)

            box_ping = BoxLayout(orientation='vertical', size_hint_y=0.15)
            box_ping.add_widget(Label(text="ІНТЕРВАЛ ОПИТУВАННЯ", font_size='14sp', bold=True))
            self.ping_slider = Slider(min=1, max=10, value=config["ping_interval"], step=1)
            self.ping_slider.bind(value=self.on_ping_change)
            self.ping_info = Label(text=f"Кожні: {int(self.ping_slider.value)} сек", font_size='12sp', color=(0.7, 0.7, 0.7, 1))
            box_ping.add_widget(self.ping_slider)
            box_ping.add_widget(self.ping_info)
            layout.add_widget(box_ping)

            box_time = BoxLayout(orientation='vertical', size_hint_y=0.15)
            box_time.add_widget(Label(text="ЗАТРИМКА ТРИВОГИ", font_size='14sp', bold=True))
            self.time_slider = Slider(min=2, max=30, value=config["timeout_limit"], step=1)
            self.time_slider.bind(value=self.on_time_change)
            self.time_info = Label(text=f"Очікування: {int(self.time_slider.value)} сек", font_size='12sp', color=(0.7, 0.7, 0.7, 1))
            box_time.add_widget(self.time_slider)
            box_time.add_widget(self.time_info)
            layout.add_widget(box_time)

            box_dur = BoxLayout(orientation='vertical', size_hint_y=0.15)
            box_dur.add_widget(Label(text="ТРИВАЛІСТЬ СИРЕНИ", font_size='14sp', bold=True))
            self.duration_slider = Slider(min=1, max=5, value=config["alarm_duration"], step=1)
            self.duration_slider.bind(value=self.on_duration_change)
            self.duration_info = Label(text=f"Вимкнення через: {int(self.duration_slider.value)} хв", font_size='12sp', color=(0.7, 0.7, 0.7, 1))
            box_dur.add_widget(self.duration_slider)
            box_dur.add_widget(self.duration_info)
            layout.add_widget(box_dur)

            self.btn_start = Button(text="ЗАПУСТИТИ СЛУЖБУ", font_size='16sp', bold=True, background_color=(0.2, 0.8, 0.2, 1), size_hint_y=0.1)
            self.btn_start.bind(on_press=self.start_service)
            layout.add_widget(self.btn_start)

            self.btn_stop = Button(text="ЗУПИНИТИ СЛУЖБУ", font_size='16sp', bold=True, background_color=(0.8, 0.2, 0.2, 1), size_hint_y=0.1)
            self.btn_stop.bind(on_press=self.stop_service)
            layout.add_widget(self.btn_stop)

            self.btn_settings = Button(text="НАЛАШТУВАННЯ ПРИСТРОЮ", font_size='14sp', background_color=(0.3, 0.3, 0.3, 1), size_hint_y=0.1)
            self.btn_settings.bind(on_press=self.go_to_settings)
            layout.add_widget(self.btn_settings)

            self.add_widget(layout)
            
            Clock.schedule_interval(self.update_live_ui, 0.5)
            self.service_running = False

        def update_live_ui(self, dt):
            if not self.service_running:
                return

            state_file = get_state_path()
            if os.path.exists(state_file):
                try:
                    with open(state_file, "r") as f:
                        state_data = json.load(f)
                        
                        status_text = state_data.get("status", "ОЧІКУВАННЯ...")
                        rssi_val = state_data.get("rssi", -100)
                        
                        self.status_label.text = status_text
                        
                        if "ТРИВОГА" in status_text or "ВТРАЧАЮ" in status_text:
                            self.status_label.color = (1, 0.2, 0.2, 1)
                        elif "СТАБІЛЬНИЙ" in status_text:
                            self.status_label.color = (0.2, 0.8, 0.2, 1)
                        else:
                            self.status_label.color = (0.8, 0.8, 0.2, 1)

                        alpha = max(0.1, min(1.0, (rssi_val + 100) / 50.0))
                        
                        config = load_full_config()
                        mac = config.get("mac_address", "НЕВІДОМО")
                        dist = calc_distance(rssi_val)
                        
                        self.target_label.text = f"МЕТА: {mac}\nСигнал: {rssi_val} dBm (~{dist} м)"
                        self.target_label.color = (0.2, 0.8, 0.2, alpha)
                except Exception:
                    pass

        def on_rssi_change(self, instance, value):
            dist = calc_distance(value)
            self.rssi_info.text = f"Поріг: {int(value)} dBm (~{dist} м)"
            
        def on_ping_change(self, instance, value): self.ping_info.text = f"Кожні: {int(value)} сек"
        def on_time_change(self, instance, value): self.time_info.text = f"Очікування: {int(value)} сек"
        def on_duration_change(self, instance, value): self.duration_info.text = f"Вимкнення через: {int(value)} хв"

        def start_service(self, instance):
            save_full_config({
                "rssi_threshold": self.rssi_slider.value,
                "ping_interval": self.ping_slider.value,
                "timeout_limit": self.time_slider.value,
                "alarm_duration": self.duration_slider.value
            })

            config = load_full_config()
            if not config.get("mac_address"):
                self.status_label.text = "СПОЧАТКУ ВИБЕРІТЬ ПРИСТРІЙ!"
                self.status_label.color = (1, 0.2, 0.2, 1)
                return

            self.rssi_slider.disabled = True
            self.ping_slider.disabled = True
            self.time_slider.disabled = True
            self.duration_slider.disabled = True
            self.btn_settings.disabled = True

            if platform == 'android':
                try:
                    from jnius import autoclass
                    # ОСЬ ТУТ ВИПРАВЛЕНО: Ми звертаємося до згенерованого класу ServiceScanner
                    service = autoclass("com.romanveterinary.vettrack_antilost.ServiceScanner")
                    mActivity = autoclass("org.kivy.android.PythonActivity").mActivity
                    service.start(mActivity, "")
                    self.service_running = True
                    self.status_label.text = "СЛУЖБА ПРАЦЮЄ У ФОНІ"
                    self.status_label.color = (0.2, 0.8, 0.2, 1)
                except Exception as e:
                    self.status_label.text = f"Помилка: {str(e)}"
                    self.status_label.color = (1, 0.2, 0.2, 1)

        def stop_service(self, instance):
            self.status_label.text = "ФОНОВУ СЛУЖБУ ЗУПИНЕНО"
            self.status_label.color = (0.5, 0.5, 0.5, 1)
            self.service_running = False
            self.target_label.text = "СЛУЖБА ЗУПИНЕНА"
            self.target_label.color = (0.5, 0.5, 0.5, 0.3)
            
            self.rssi_slider.disabled = False
            self.ping_slider.disabled = False
            self.time_slider.disabled = False
            self.duration_slider.disabled = False
            self.btn_settings.disabled = False

            try:
                state_file = get_state_path()
                if os.path.exists(state_file):
                    os.remove(state_file)
            except:
                pass

            if platform == 'android':
                try:
                    from jnius import autoclass
                    # ОСЬ ТУТ ВИПРАВЛЕНО ТАКОЖ
                    service = autoclass("com.romanveterinary.vettrack_antilost.ServiceScanner")
                    mActivity = autoclass("org.kivy.android.PythonActivity").mActivity
                    service.stop(mActivity)
                except Exception:
                    pass

        def go_to_settings(self, instance):
            self.manager.current = 'settings'

    class SettingsScreen(Screen):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.found_devices = {}
            
            self.bluetooth_adapter = None
            self.scan_callback = None
            if platform == "android":
                self.bluetooth_adapter = BluetoothAdapter.getDefaultAdapter()
            
            layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

            layout.add_widget(Label(text="НАЛАШТУВАННЯ", font_size='20sp', bold=True, size_hint_y=0.1))

            layout.add_widget(Label(text="Bluetooth MAC-адреса:", font_size='14sp', size_hint_y=0.05, halign='left'))
            self.mac_input = TextInput(text="", multiline=False, font_size='14sp', size_hint_y=0.1)
            layout.add_widget(self.mac_input)

            layout.add_widget(Label(text="Власна мелодія (пусто = стандартна):", font_size='14sp', size_hint_y=0.05))
            box_melody = BoxLayout(orientation='horizontal', size_hint_y=0.1, spacing=5)
            self.melody_input = TextInput(text="", multiline=False, font_size='12sp', size_hint_x=0.7)
            btn_choose_melody = Button(text="ОГЛЯД", font_size='14sp', background_color=(0.4, 0.4, 0.4, 1), size_hint_x=0.3)
            btn_choose_melody.bind(on_press=self.choose_melody)
            box_melody.add_widget(self.melody_input)
            box_melody.add_widget(btn_choose_melody)
            layout.add_widget(box_melody)

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

        def choose_melody(self, instance):
            try:
                from plyer import filechooser
                filechooser.open_file(on_selection=self.handle_selection, filters=[("Audio", "*.mp3", "*.wav")])
            except Exception as e:
                self.melody_input.text = "Помилка файлового менеджера"

        @mainthread
        def handle_selection(self, selection):
            if selection:
                self.melody_input.text = selection[0]
                
        @mainthread
        def on_device_found(self, address, name, rssi):
            if address not in self.found_devices:
                self.found_devices[address] = True
                dev_name = name if name else "Невідомий пристрій"
                
                dist = calc_distance(rssi)
                btn_text = f"{dev_name} \n[{address}] | {rssi} dBm (~{dist} м)"
                
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
                lbl = Label(text="Нічого не знайдено.", font_size='12sp', size_hint_y=None, height=40)
                self.devices_container.add_widget(lbl)
                self.devices_container.height += 40

        def select_device(self, address):
            self.mac_input.text = address

        def save_config(self, instance):
            save_full_config({
                "mac_address": self.mac_input.text.strip(),
                "melody_path": self.melody_input.text.strip()
            })
            self.manager.current = 'main'

        def load_config(self):
            config = load_full_config()
            self.mac_input.text = config.get("mac_address", "")
            self.melody_input.text = config.get("melody_path", "")

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
                    Permission.ACCESS_COARSE_LOCATION,
                    Permission.READ_EXTERNAL_STORAGE,  
                    Permission.READ_MEDIA_AUDIO        
                ])

            self.title = "VetTrack Anti-Lost"
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
