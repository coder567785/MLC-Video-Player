import gi
import os
import webbrowser
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst, GObject, Gdk, Gio

class MacOSVideoPlayer(Gtk.Window):
    def __init__(self):
        super().__init__(title="macOS Media Player")
        self.set_default_size(960, 540)
        self.is_fullscreen = False
        self.setup_gstreamer()
        self.setup_ui()
        self.load_css()
        self.connect("destroy", self.on_close)

    def setup_gstreamer(self):
        Gst.init(None)
        self.player = Gst.ElementFactory.make("playbin", "player")
        self.player.set_property("volume", 0.5)
        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message::eos", self.on_eos)
        self.bus.connect("message::error", self.on_error)

    def setup_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)

        # Menu Bar
        menubar = Gtk.MenuBar()
        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem(label="File")
        file_item.set_submenu(file_menu)
        
        open_item = Gtk.MenuItem(label="Open")
        open_item.connect("activate", self.on_open_clicked)
        file_menu.append(open_item)
        
        about_menu = Gtk.Menu()
        about_item = Gtk.MenuItem(label="Help")
        about_item.set_submenu(about_menu)
        
        about_content = Gtk.MenuItem(label="About")
        about_content.connect("activate", self.show_about)
        about_menu.append(about_content)
        
        menubar.append(file_item)
        menubar.append(about_item)
        main_box.pack_start(menubar, False, False, 0)

        # Video area
        self.video_area = Gtk.DrawingArea()
        self.video_area.set_hexpand(True)
        self.video_area.set_vexpand(True)
        main_box.pack_start(self.video_area, True, True, 0)

        # Controls container
        controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        controls_box.get_style_context().add_class("controls")
        main_box.pack_end(controls_box, False, False, 0)

        # Progress bar
        self.progress = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.progress.set_draw_value(False)
        self.progress.connect("button-release-event", self.on_seek)
        controls_box.pack_start(self.progress, False, False, 0)

        # Controls buttons
        controls_buttons = Gtk.Box(spacing=15)
        controls_buttons.set_halign(Gtk.Align.CENTER)
        controls_buttons.set_margin_top(10)
        controls_buttons.set_margin_bottom(10)
        controls_box.pack_start(controls_buttons, False, False, 0)

        self.prev_btn = self.create_button("media-skip-backward-symbolic", "Previous")
        self.play_btn = self.create_button("media-playback-start-symbolic", "Play")
        self.next_btn = self.create_button("media-skip-forward-symbolic", "Next")
        self.volume_btn = self.create_volume_button()
        self.fullscreen_btn = self.create_button("view-fullscreen-symbolic", "Fullscreen")

        controls_buttons.pack_start(self.prev_btn, False, False, 0)
        controls_buttons.pack_start(self.play_btn, False, False, 0)
        controls_buttons.pack_start(self.next_btn, False, False, 0)
        controls_buttons.pack_start(self.volume_btn, False, False, 0)
        controls_buttons.pack_start(self.fullscreen_btn, False, False, 0)

        # Time labels
        time_box = Gtk.Box(spacing=10)
        time_box.set_margin_bottom(10)
        controls_box.pack_start(time_box, False, False, 0)

        self.current_time = Gtk.Label(label="00:00:00")
        self.current_time.get_style_context().add_class("time-label")
        self.total_time = Gtk.Label(label="00:00:00")
        self.total_time.get_style_context().add_class("time-label")
        time_box.pack_start(self.current_time, False, False, 10)
        time_box.pack_end(self.total_time, False, False, 10)

    def create_button(self, icon_name, tooltip):
        btn = Gtk.Button.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
        btn.set_tooltip_text(tooltip)
        btn.get_style_context().add_class("control-btn")
        if icon_name == "media-playback-start-symbolic":
            btn.connect("clicked", self.toggle_playback)
        elif icon_name == "view-fullscreen-symbolic":
            btn.connect("clicked", self.toggle_fullscreen)
        return btn

    def create_volume_button(self):
        btn = Gtk.VolumeButton()
        btn.set_tooltip_text("Volume")
        btn.get_style_context().add_class("control-btn")
        btn.connect("value-changed", self.on_volume_changed)
        return btn

    def load_css(self):
        css = b"""
        .controls {
            background-color: rgba(0, 0, 0, 0.8);
            border-radius: 15px;
            margin: 15px;
            padding: 10px;
        }
        .control-btn {
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 8px;
            margin: 0 5px;
        }
        .control-btn:hover {
            background-color: rgba(255, 255, 255, 0.2);
        }
        scale trough {
            min-height: 4px;
            background-color: rgba(255, 255, 255, 0.3);
            border-radius: 2px;
        }
        scale highlight {
            min-height: 4px;
            background-color: #007AFF;
            border-radius: 2px;
        }
        .time-label {
            color: #ffffff;
            font-size: 12px;
            font-weight: bold;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def on_open_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Open Media File",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            "Open", Gtk.ResponseType.OK
        )
        
        filter_media = Gtk.FileFilter()
        filter_media.set_name("Media files")
        filter_media.add_mime_type("video/*")
        filter_media.add_mime_type("audio/*")
        filter_media.add_pattern("*.mp4")
        filter_media.add_pattern("*.mkv")
        filter_media.add_pattern("*.mp3")
        dialog.add_filter(filter_media)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file_path = dialog.get_filename()
            self.open_file(file_path)
        dialog.destroy()

    def open_file(self, path):
        self.player.set_property("uri", "file://" + os.path.abspath(path))
        self.player.set_state(Gst.State.PLAYING)
        self.play_btn.set_image(Gtk.Image.new_from_icon_name(
            "media-playback-pause-symbolic", Gtk.IconSize.BUTTON))
        GObject.timeout_add(200, self.update_progress)

    def show_about(self, widget):
        about = Gtk.AboutDialog()
        about.set_program_name("macOS Media Player")
        about.set_version("1.0")
        about.set_copyright("© 2023 Your Company")
        about.set_comments("A modern media player with macOS-style UI")
        about.set_authors(["Your Name"])
        about.set_website("https://example.com")
        about.run()
        about.destroy()

    def toggle_playback(self, btn):
        if self.player.get_state(0)[1] == Gst.State.PLAYING:
            self.player.set_state(Gst.State.PAUSED)
            btn.set_image(Gtk.Image.new_from_icon_name(
                "media-playback-start-symbolic", Gtk.IconSize.BUTTON))
        else:
            self.player.set_state(Gst.State.PLAYING)
            btn.set_image(Gtk.Image.new_from_icon_name(
                "media-playback-pause-symbolic", Gtk.IconSize.BUTTON))
            GObject.timeout_add(200, self.update_progress)

    def on_seek(self, scale, event):
        value = scale.get_value()
        self.player.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            value * Gst.SECOND
        )

    def update_progress(self):
        success, position = self.player.query_position(Gst.Format.TIME)
        success, duration = self.player.query_duration(Gst.Format.TIME)
        
        if success:
            self.progress.set_range(0, duration / Gst.SECOND)
            self.progress.set_value(position / Gst.SECOND)
            self.current_time.set_text(self.format_time(position))
            self.total_time.set_text(self.format_time(duration))
        return self.player.get_state(0)[1] == Gst.State.PLAYING

    def format_time(self, nanoseconds):
        seconds = nanoseconds // Gst.SECOND
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def on_volume_changed(self, btn, volume):
        self.player.set_property("volume", volume)

    def toggle_fullscreen(self, btn):
        if self.is_fullscreen:
            self.unfullscreen()
            self.is_fullscreen = False
        else:
            self.fullscreen()
            self.is_fullscreen = True

    def on_eos(self, bus, msg):
        self.player.set_state(Gst.State.NULL)
        self.play_btn.set_image(Gtk.Image.new_from_icon_name(
            "media-playback-start-symbolic", Gtk.IconSize.BUTTON))

    def on_error(self, bus, msg):
        err, debug = msg.parse_error()
        print(f"Error: {err.message}")
        self.player.set_state(Gst.State.NULL)

    def on_close(self, window):
        self.player.set_state(Gst.State.NULL)
        Gtk.main_quit()

if __name__ == "__main__":
    player = MacOSVideoPlayer()
    player.show_all()
    Gtk.main()
