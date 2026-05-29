import traceback

try:
    import asyncio
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
    from bleak import BleakScanner

    # ВИПРАВЛЕННЯ: Фіксуємо розмір тільки для ПК, на Android додаток буде на весь екран
    if platform not in ('android', 'ios'):
        Window.size = (400, 720)

    def get_config_path():
        # На Android зберігаємо конфіг у дозволену системну папку додатка
        return os.path.join(App.get_running_app().user_data_dir, "anti_lost_config.json")

    class MainScreen(Screen):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.monitor_task = None  
            self.disconnect_start_time = None
            self.alarm_start_time = None  
            
            self.alarm_sound = SoundLoader.load('sonar.wav')
            if self.alarm_sound:
                self.alarm_sound.loop = True
            
            layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

            layout.add_widget(Label(text="VET-TRACK: ANTI-LOST", font_size='22sp', bold=True, size_hint_y=None, height=40))

            self.status_label = Label(text="МОНІТОРИНГ ВИМКНЕНО", font_size='18sp', bold=True, color=(0.5, 0.5, 0.5, 1), size_hint_y=None, height=40)
            layout.add_widget(self.status_label)

            layout.add_widget(Label(text="🎚️ СИЛА СИГНАЛУ (RSSI / ВІДСТАНЬ)", font_size='13sp', size_hint_y=None, height=18))
            self.rssi_slider = Slider(min=-95, max=-60, value=-85, step=1, size_hint_y=None, height=25)
            self.rssi_slider.bind(value=self.on_rssi_change)
            self.rssi_info = Label(text="Поріг спрацювання: -85 dBm (~15м)", font_size='11sp', color=(0.7, 0.7, 0.7, 1), size_hint_y=None, height=15)
            layout.add_widget(self.rssi_slider)
            layout.add_widget(self.rssi_info)

            layout.add_widget(Label(text="⏱️ ІНТЕРВАЛ ПІНГУ (ЧАСТОТА ОПИТУВАННЯ)", font_size='13sp', size_hint_y=None, height=18))
            self.ping_slider = Slider(min=1, max=10, value=2, step=1, size_hint_y=None, height=25)
            self.ping_slider.bind(value=self.on_ping_change)
            self.ping_info = Label(text="Перевірка кожні: 2 сек", font_size='11sp', color=(0.7, 0.7, 0.7, 1), size_hint_y=None, height=15)
            layout.add_widget(self.ping_slider)
            layout.add_widget(self.ping_info)

            layout.add_widget(Label(text="⏳ ЧАС ВІДПОВІДІ (ЗАТРИМКА ТРИВОГИ)", font_size='13sp', size_hint_y=None, height=18))
            self.time_slider = Slider(min=2, max=30, value=5, step=1, size_hint_y=None, height=25)
            self.time_slider.bind(value=self.on_time_change)
            self.time_info = Label(text="Час очікування: 5 секунд", font_size='11sp', color=(0.7, 0.7, 0.7, 1), size_hint_y=None, height=15)
            layout.add_widget(self.time_slider)
            layout.add_widget(self.time_info)

            layout.add_widget(Label(text="🔔 ТРИВАЛІСТЬ ЗВУЧАННЯ ТРИВОГИ", font_size='13sp', size_hint_y=None, height=18))
            self.duration_slider = Slider(min=1, max=5, value=2, step=1, size_hint_y=None, height=25)
            self.duration_slider.bind(value=self.on_duration_change)
            self.duration_info = Label(text="Автовимкнення через: 2 хв", font_size='11sp', color=(0.7, 0.7, 0.7, 1), size_hint_y=None, height=15)
            layout.add_widget(self.duration_slider)
            layout.add_widget(self.duration_info)

            layout.add_widget(BoxLayout(size_hint_y=None, height=5))

            self.btn_start = Button(text="🟢 УВІМКНУТИ", font_size='16sp', bold=True, background_color=(0.2, 0.8, 0.2, 1), size_hint_y=None, height=48)
            self.btn_start.bind(on_press=self.start_monitoring)
            layout.add_widget(self.btn_start)

            self.btn_stop = Button(text="🔴 ВИМКНУТИ", font_size='16sp', bold=True, background_color=(0.8, 0.2, 0.2, 1), size_hint_y=None, height=48, disabled=True)
            self.btn_stop.bind(on_press=self.stop_monitoring)
            layout.add_widget(self.btn_stop)

            btn_settings = Button(text="⚙️ НАЛАШТУВАННЯ ПРИСТРОЮ", font_size='14sp', background_color=(0.3, 0.3, 0.3, 1), size_hint_y=None, height=42)
            btn_settings.bind(on_press=self.go_to_settings)
            layout.add_widget(btn_settings)

            self.add_widget(layout)

        def on_rssi_change(self, instance, value): self.rssi_info.text = f"Поріг спрацювання: {int(value)} dBm"
        def on_ping_change(self, instance, value): self.ping_info.text = f"Перевірка кожні: {int(value)} сек"
        def on_time_change(self, instance, value): self.time_info.text = f"Час очікування: {int(value)} секунд"
        def on_duration_change(self, instance, value): self.duration_info.text = f"Автовимкнення через: {int(value)} хв"

        def start_monitoring(self, instance):
            self.btn_start.disabled = True
            self.btn_stop.disabled = False
            self.toggle_sliders(disabled=True)
            
            self.status_label.text = "ПОШУК БРАСЛЕТА..."
            self.status_label.color = (0.2, 0.7, 0.8, 1)
            self.disconnect_start_time = None
            self.alarm_start_time = None
            self.monitor_task = asyncio.ensure_future(self.ble_monitor_loop())

        def stop_monitoring(self, instance):
            if self.monitor_task:
                self.monitor_task.cancel()
                self.monitor_task = None
                
            if self.alarm_sound and self.alarm_sound.state == 'play':
                self.alarm_sound.stop()
                
            self.status_label.text = "МОНІТОРИНГ ВИМКНЕНО"
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

        async def ble_monitor_loop(self):
            mac_address = ""
            config_file = get_config_path()
            if os.path.exists(config_file):
                try:
                    with open(config_file, "r") as f:
                        mac_address = json.load(f).get("mac_address", "").strip()
                except Exception:
                    pass

            if not mac_address:
                self.status_label.text = "ПОМИЛКА: ВКАЖІТЬ MAC-АДРЕСУ!"
                self.status_label.color = (1, 0.2, 0.2, 1)
                self.stop_monitoring(None)
                return

            while True:
                try:
                    target_rssi = self.rssi_slider.value
                    ping_interval = self.ping_slider.value
                    timeout_limit = self.time_slider.value
                    max_alarm_duration = self.duration_slider.value * 60

                    device = await BleakScanner.find_device_by_address(mac_address, timeout=1.5)
                    current_time = time.time()

                    if self.alarm_start_time and (current_time - self.alarm_start_time >= max_alarm_duration):
                        if self.alarm_sound and self.alarm_sound.state == 'play':
                            self.alarm_sound.stop()
                        self.status_label.text = "🔇 ТРИВОГА ВИМКНЕНА ЗА ТАЙМАУТОМ"
                        self.status_label.color = (0.7, 0.4, 0.7, 1)
                        await asyncio.sleep(ping_interval)
                        continue

                    if device is None or device.rssi < target_rssi:
                        if self.disconnect_start_time is None:
                            self.disconnect_start_time = current_time
                        
                        elapsed = current_time - self.disconnect_start_time
                        self.status_label.text = f"ВТРАТА ЗВ'ЯЗКУ! ({int(elapsed)}с)"
                        self.status_label.color = (0.9, 0.4, 0.1, 1)

                        if elapsed >= timeout_limit:
                            self.status_label.text = "💥 ТРИВОГА! ПРИСТРІЙ ВІДСУТНІЙ!"
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
                        self.status_label.text = f"ПРИСТРІЙ ПОРУЧ | Сигнал: {device.rssi} dBm"
                        self.status_label.color = (0.2, 0.8, 0.2, 1)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"Помилка циклу моніторингу: {e}")

                await asyncio.sleep(ping_interval)

    class SettingsScreen(Screen):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

            layout.add_widget(Label(text="⚙️ НАЛАШТУВАННЯ", font_size='20sp', bold=True, size_hint_y=None, height=35))

            layout.add_widget(Label(text="Bluetooth MAC-адреса:", font_size='14sp', size_hint_y=None, height=20, halign='left'))
            self.mac_input = TextInput(text="", multiline=False, font_size='14sp', size_hint_y=None, height=35)
            layout.add_widget(self.mac_input)

            layout.add_widget(Label(text="Ключ авторизації (Auth Key):", font_size='14sp', size_hint_y=None, height=20))
            self.key_input = TextInput(text="", multiline=False, font_size='14sp', size_hint_y=None, height=35)
            layout.add_widget(self.key_input)

            layout.add_widget(Label(text="🔍 БЛЮТУЗ РАДАР (Клікни на пристрій для вибору):", font_size='12sp', color=(0.2, 0.7, 0.8, 1), size_hint_y=None, height=20))
            
            self.scroll_view = ScrollView(size_hint=(1, 1))
            self.devices_container = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
            self.devices_container.bind(minimum_height=self.devices_container.setter('height'))
            
            self.scroll_view.add_widget(self.devices_container)
            layout.add_widget(self.scroll_view)

            self.btn_scan = Button(text="📡 ЗАПУСТИТИ РАДАР ЕФІРУ", font_size='14sp', background_color=(0.2, 0.6, 0.8, 1), size_hint_y=None, height=45)
            self.btn_scan.bind(on_press=self.start_ble_scan)
            layout.add_widget(self.btn_scan)

            btn_save = Button(text="💾 ЗБЕРЕГТИ КОНФІГ", font_size='16sp', bold=True, background_color=(0.2, 0.8, 0.2, 1), size_hint_y=None, height=50)
            btn_save.bind(on_press=self.save_config)
            layout.add_widget(btn_save)

            self.add_widget(layout)
            
        def on_enter(self):
            self.load_config()

        def start_ble_scan(self, instance):
            self.btn_scan.disabled = True
            self.btn_scan.text = "ШУКАЮ ПРИСТРОЇ..."
            self.devices_container.clear_widgets()
            self.devices_container.height = 0
            asyncio.ensure_future(self.scan_devices_async())

        async def scan_devices_async(self):
            try:
                devices = await BleakScanner.discover(timeout=4.0)
                self.devices_container.clear_widgets()
                self.devices_container.height = 0
                
                if not devices:
                    lbl = Label(text="Нічого не знайдено. Увімкніть Bluetooth.", font_size='12sp', size_hint_y=None, height=40)
                    self.devices_container.add_widget(lbl)
                    self.devices_container.height += 40
                else:
                    for d in devices:
                        name = d.name if d.name else "Невідомий пристрій"
                        btn_text = f"📱 {name} \n[{d.address}] | {d.rssi} dBm"
                        
                        dev_btn = ToggleButton(text=btn_text, group='ble_dev', size_hint=(1, None), height=55, font_size='11sp')
                        dev_btn.bind(on_press=lambda inst, addr=d.address: self.select_device(addr))
                        
                        self.devices_container.add_widget(dev_btn)
                        self.devices_container.height += 60
                        
            except Exception as e:
                print(f"Помилка радара: {e}")
            finally:
                self.btn_scan.disabled = False
                self.btn_scan.text = "📡 ЗАПУСТИТИ РАДАР ЕФІРУ"

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
            # Системний запит дозволів при старті додатка на Android
            if platform == "android":
                from android.permissions import request_permissions, Permission
                request_permissions([
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
        asyncio.run(AntiLostApp().async_run(async_lib='asyncio'))

except Exception as e:
    # Глобальний перехоплювач помилок
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
