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
            self.status_label = Label(text="ГОТОВИЙ ДО ЗАПУСКУ", font_size='14sp', bold=True, color=(0.5, 0.5, 0.5, 1), size_hint_y=0.1)
            layout.add_widget(self.status_label)
            self.target_label = Label(text="ПРИСТРІЙ НЕ ВИБРАНО", font_size='22sp', bold=True, color=(0.2, 0.8, 0.2, 0.2), size_hint_y=0.1)
            layout.add_widget(self.target_label)

            config = load_full_config()
            box_rssi = BoxLayout(orientation='vertical', size_hint_y=0.15)
            self.rssi_slider = Slider(min=-95, max=-60, value=config["rssi_threshold"], step=1)
            self.rssi_slider.bind(value=self.on_rssi_change)
            self.rssi_info = Label(text=f"Поріг: {int(self.rssi_slider.value)} dBm", font_size='12sp')
            box_rssi.add_widget(self.rssi_slider); box_rssi.add_widget(self.rssi_info)
            layout.add_widget(box_rssi)

            self.btn_start = Button(text="ЗАПУСТИТИ СЛУЖБУ", font_size='16sp', bold=True, size_hint_y=0.1)
            self.btn_start.bind(on_press=self.start_service)
            layout.add_widget(self.btn_start)
            
            self.btn_stop = Button(text="ЗУПИНИТИ СЛУЖБУ", size_hint_y=0.1)
            self.btn_stop.bind(on_press=self.stop_service)
            layout.add_widget(self.btn_stop)

            btn_settings = Button(text="НАЛАШТУВАННЯ", size_hint_y=0.1)
            btn_settings.bind(on_press=lambda x: setattr(self.manager, 'current', 'settings'))
            layout.add_widget(btn_settings)
            self.add_widget(layout)
            Clock.schedule_interval(self.update_live_ui, 0.5)

        def start_service(self, instance):
            save_full_config({"rssi_threshold": self.rssi_slider.value, "ping_interval": 2, "timeout_limit": 5})
            if platform == 'android':
                try:
                    from jnius import autoclass
                    service = autoclass("org.kivy.android.PythonService")
                    mActivity = autoclass("org.kivy.android.PythonActivity").mActivity
                    service.start(mActivity, "scanner")
                    self.service_running = True
                except Exception as e:
                    self.status_label.text = f"Помилка: {str(e)}"

        def stop_service(self, instance):
            if platform == 'android':
                from jnius import autoclass
                service = autoclass("org.kivy.android.PythonService")
                mActivity = autoclass("org.kivy.android.PythonActivity").mActivity
                service.stop(mActivity)
            self.service_running = False
            self.status_label.text = "СЛУЖБУ ЗУПИНЕНО"

        def update_live_ui(self, dt):
            # Тут ваш код оновлення з файлу стану
            pass

        def on_rssi_change(self, instance, value):
            self.rssi_info.text = f"Поріг: {int(value)} dBm"

        def go_to_settings(self, instance): self.manager.current = 'settings'

    class SettingsScreen(Screen):
        # (Ваш клас SettingsScreen залишається без змін)
        pass

    class AntiLostApp(App):
        def build(self):
            sm = ScreenManager()
            sm.add_widget(MainScreen(name='main'))
            sm.add_widget(SettingsScreen(name='settings'))
            return sm

    if __name__ == "__main__":
        AntiLostApp().run()

except Exception:
    # (Ваш код ErrorApp залишається без змін)
    pass
