
import gi
import os
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import Gtk, Gst, GObject, Gdk, GLib

class MacOSVideoPlayer(Gtk.Window):
    def __init__(self):
        super().__init__(title="macOS Media Player")
        self.current_file = None
        self.is_fullscreen = False
        
        # Window setup
        self.set_default_size(960, 540)
        self.setup_gstreamer()
        self.init_ui()
        self.connect_signals()
        self.load_styles()
        self.show_all()

    def setup_gstreamer(self):
        Gst.init(None)
        self.player = Gst.ElementFactory.make("playbin", "player")
        self.player.set_property("volume", 0.5)
        
        # Configure video sink
        videosink = Gst.ElementFactory.make("xvimagesink", "xv-sink")
        videosink.set_property("force-aspect-ratio", True)
        self.player.set_property("video-sink", videosink)
        
        # Connect signals
        self.player.connect("video-changed", self.on_video_changed)
        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message::eos", self.on_eos)
        self.bus.connect("message::error", self.on_error)

    def init_ui(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.main_box)
        
        # Menu Bar
        menubar = Gtk.MenuBar()
        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem(label="File")
        file_item.set_submenu(file_menu)
        
        open_item = Gtk.MenuItem(label="Open")
        open_item.connect("activate", self.on_open_file)
        file_menu.append(open_item)
        
        menubar.append(file_item)
        self.main_box.pack_start(menubar, False, False, 0)

        # Video area
        self.video_area = Gtk.DrawingArea()
        self.video_area.set_hexpand(True)
        self.video_area.set_vexpand(True)
        self.video_area.connect("realize", self.on_video_area_realized)
        self.main_box.pack_start(self.video_area, True, True, 0)

        # Controls
        controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        controls_box.get_style_context().add_class("controls")
        
        # Progress bar
        self.progress = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.progress.set_draw_value(False)
        self.progress.connect("button-release-event", self.on_seek)
        controls_box.pack_start(self.progress, False, False, 0)

        # Buttons
        btn_box = Gtk.Box(spacing=10, margin_top=10, margin_bottom=10)
        self.play_btn = self.create_button("media-playback-start-symbolic", self.toggle_playback)
        self.volume_btn = Gtk.VolumeButton()
        self.volume_btn.connect("value-changed", self.on_volume_changed)
        self.fullscreen_btn = self.create_button("view-fullscreen-symbolic", self.toggle_fullscreen)
        
        btn_box.pack_start(self.play_btn, False, False, 0)
        btn_box.pack_start(self.volume_btn, False, False, 0)
        btn_box.pack_start(self.fullscreen_btn, False, False, 0)
        controls_box.pack_start(btn_box, False, False, 0)

        # Time labels
        time_box = Gtk.Box(spacing=10, margin_bottom=10)
        self.current_time = Gtk.Label(label="00:00:00")
        self.total_time = Gtk.Label(label="00:00:00")
        time_box.pack_start(self.current_time, False, False, 0)
        time_box.pack_end(self.total_time, False, False, 0)
        controls_box.pack_start(time_box, False, False, 0)
        
        self.main_box.pack_end(controls_box, False, False, 0)

    def create_button(self, icon, callback):
        btn = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
        btn.get_style_context().add_class("control-btn")
        btn.connect("clicked", callback)
        return btn

    def load_styles(self):
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
        }
        scale highlight {
            min-height: 4px;
            background-color: #007AFF;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def on_video_area_realized(self, widget):
        self.update_video_window()

    def on_video_changed(self, element):
        GLib.idle_add(self.update_video_window)

    def update_video_window(self):
        if self.video_area.get_realized():
            xid = self.video_area.get_window().get_xid()
            self.player.get_property("video-sink").set_window_handle(xid)

    def on_open_file(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Open File",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Open", Gtk.ResponseType.OK)
        
        filter_media = Gtk.FileFilter()
        filter_media.set_name("Media files")
        filter_media.add_pattern("*.mp4")
        filter_media.add_pattern("*.mkv")
        filter_media.add_pattern("*.mp3")
        dialog.add_filter(filter_media)

        if dialog.run() == Gtk.ResponseType.OK:
            self.current_file = dialog.get_filename()
            self.player.set_state(Gst.State.NULL)
            self.player.set_property("uri", "file://" + os.path.abspath(self.current_file))
            self.player.set_state(Gst.State.PLAYING)
            self.play_btn.set_image(Gtk.Image.new_from_icon_name(
                "media-playback-pause-symbolic", Gtk.IconSize.BUTTON))
            GObject.timeout_add(200, self.update_progress)
        dialog.destroy()

    def toggle_playback(self, btn):
        state = self.player.get_state(0)[1]
        if state == Gst.State.PLAYING:
            self.player.set_state(Gst.State.PAUSED)
            btn.set_image(Gtk.Image.new_from_icon_name(
                "media-playback-start-symbolic", Gtk.IconSize.BUTTON))
        else:
            self.player.set_state(Gst.State.PLAYING)
            btn.set_image(Gtk.Image.new_from_icon_name(
                "media-playback-pause-symbolic", Gtk.IconSize.BUTTON))
            GObject.timeout_add(200, self.update_progress)

    def update_progress(self):
        success, position = self.player.query_position(Gst.Format.TIME)
        success, duration = self.player.query_duration(Gst.Format.TIME)
        if success:
            self.progress.set_range(0, duration / Gst.SECOND)
            self.progress.set_value(position / Gst.SECOND)
            self.current_time.set_text(self.format_time(position))
            self.total_time.set_text(self.format_time(duration))
        return self.player.get_state(0)[1] == Gst.State.PLAYING

    def format_time(self, ns):
        s = ns // Gst.SECOND
        return f"{s // 3600:02}:{(s // 60) % 60:02}:{s % 60:02}"

    def on_seek(self, scale, event):
        self.player.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            int(scale.get_value() * Gst.SECOND)
        )

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

    def connect_signals(self):
        self.connect("destroy", Gtk.main_quit)

if __name__ == "__main__":
    player = MacOSVideoPlayer()
    Gtk.main()
