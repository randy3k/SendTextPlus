import sublime
import os
import re
import subprocess
import threading
from .settings import SettingManager


class TextSender:
    cb = None
    thread = None

    def __init__(self, view, prog=None):
        self.view = view
        self.sget = SettingManager(view).get
        plat = sublime.platform()
        if not prog:
            prog = self.sget("prog")
        function_str = "_dispatch_" + prog.lower().replace("-", "_")
        if getattr(self, function_str + "_" + plat, None):
            function_str = function_str + "_" + plat
        self._send_text = eval("self." + function_str)

    def is_python(self):
        pt = self.view.sel()[0].begin() if len(self.view.sel()) > 0 else 0
        return self.view.score_selector(pt, "source.python") > 0

    def wrap_paste_magic_for_python(self, cmd):
        if self.is_python():
            cmd = cmd.rstrip("\n")
            if len(re.findall("\n", cmd)) > 0:
                cmd = "%cpaste -q\n" + cmd + "\n--"
        return cmd

    def send_text(self, cmd):
        self._send_text(cmd)

    def clean_cmd(self, cmd):
        cmd = cmd.expandtabs(4)
        cmd = cmd.rstrip('\n')
        if self.sget("remove_line_indentation", True) and len(re.findall("\n", cmd)) == 0:
            cmd = cmd.lstrip()
        return cmd

    @staticmethod
    def escape_dquote(cmd):
        cmd = cmd.replace('\\', '\\\\')
        cmd = cmd.replace('"', '\\"')
        return cmd

    @classmethod
    def set_clipboard(cls, cmd):
        if not cls.thread:
            cls.cb = sublime.get_clipboard()
        else:
            cls.thread.cancel()
            cls.thread = None
        sublime.set_clipboard(cmd)

    @classmethod
    def reset_clipboard(cls):
        def _reset_clipboard():
            if cls.cb is not None:
                sublime.set_clipboard(cls.cb)
            cls.cb = None
            cls.thread = None
        cls.thread = threading.Timer(0.5, _reset_clipboard)
        cls.thread.start()

    def _dispatch_terminal(self, cmd):
        cmd = self.wrap_paste_magic_for_python(cmd)
        cmd = self.clean_cmd(cmd)
        cmd = self.escape_dquote(cmd)
        if self.sget("bracketed_paste_mode", False):
            head = '(ASCII character 27) & "[200~'
            tail = '" & (ASCII character 27) & "[201~"'
            cmd = head + cmd + tail
        else:
            cmd = '"' + cmd + '"'
        args = ['osascript']
        args.extend(['-e',
                     'tell application "Terminal" to do script ' + cmd + ' in front window'])
        subprocess.check_call(args)

    @staticmethod
    def iterm_version():
        args = ['osascript', '-e', 'tell application "iTerm" to get version']
        ver = subprocess.check_call(args).decode().strip()
        return tuple((int(i) for i in re.split(r"\.", ver)[0:2]))

    def _dispatch_iterm(self, cmd):
        cmd = self.wrap_paste_magic_for_python(cmd)
        cmd = self.clean_cmd(cmd)
        bpm = self.sget("bracketed_paste_mode", False)
        if bpm:
            cmd = self.escape_dquote(cmd)
            head = '(ASCII character 27) & "[200~'
            tail = '" & (ASCII character 27) & "[201~"'
            cmd = head + cmd + tail
            subprocess.check_call([
                'osascript', '-e',
                'tell application "iTerm" to tell the current window ' +
                'to tell current session to write text '
            ])
        elif self.iterm_version() >= (2, 9):
            n = 1000
            chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
            for chunk in chunks:
                subprocess.check_call([
                    'osascript', '-e',
                    'tell application "iTerm" to tell the current window ' +
                    'to tell current session to write text "' +
                    self.escape_dquote(chunk) + '" without newline'
                ])
            subprocess.check_call([
                'osascript', '-e',
                'tell application "iTerm" to tell the current window ' +
                'to tell current session to write text ""'
            ])
        else:
            subprocess.check_call([
                'osascript', '-e',
                'tell application "iTerm" to tell the current terminal ' +
                'to tell current session to write text "' +
                self.escape_dquote(cmd) + '"'
            ])

    def _dispatch_r_osx(self, cmd):
        cmd = self.clean_cmd(cmd)
        cmd = self.escape_dquote(cmd)
        args = ['osascript']
        args.extend(['-e', 'tell application "R" to cmd "' + cmd + '"'])
        subprocess.check_call(args)

    def _dispatch_rstudio_osx(self, cmd):
        cmd = self.clean_cmd(cmd)
        script = """
        on run argv
            tell application "RStudio"
                cmd item 1 of argv
            end tell
        end run
        """
        subprocess.check_call(['osascript', '-e', script, cmd])

    def _dispatch_chrome_rstudio(self, cmd):
        cmd = self.clean_cmd(cmd)
        cmd = self.escape_dquote(cmd)
        cmd = cmd.replace("\n", r"\n")
        script = """
        on run argv
            tell application "Google Chrome"
                set URL of front window's active tab to "javascript:{" & "
                    var input = document.getElementById('rstudio_console_input');
                    var textarea = input.getElementsByTagName('textarea')[0];
                    textarea.value += \\"" & item 1 of argv & "\\";
                    var e = document.createEvent('KeyboardEvent');
                    e.initKeyboardEvent('input');
                    textarea.dispatchEvent(e);
                    var e = document.createEvent('KeyboardEvent');
                    e.initKeyboardEvent('keydown');
                    Object.defineProperty(e, 'keyCode', {'value' : 13});
                    input.dispatchEvent(e);
                " & "}"
            end tell
        end run
        """
        subprocess.check_call(['osascript', '-e', script, cmd])

    def _dispatch_safari_rstudio(self, cmd):
        cmd = self.clean_cmd(cmd)
        cmd = self.escape_dquote(cmd)
        cmd = cmd.replace("\n", r"\n")
        script = """
        on run argv
            tell application "Safari"
                tell front window's current tab to do JavaScript "
                    var input = document.getElementById('rstudio_console_input');
                    var textarea = input.getElementsByTagName('textarea')[0];
                    textarea.value += \\"" & item 1 of argv & "\\";
                    var e = document.createEvent('KeyboardEvent');
                    e.initKeyboardEvent('input');
                    textarea.dispatchEvent(e);
                    var e = document.createEvent('KeyboardEvent');
                    e.initKeyboardEvent('keydown');
                    Object.defineProperty(e, 'keyCode', {'value' : 13});
                    input.dispatchEvent(e);
                "
            end tell
        end run
        """
        subprocess.check_call(['osascript', '-e', script, cmd])

    def _dispatch_chrome_jupyter(self, cmd):
        cmd = self.clean_cmd(cmd)
        cmd = self.escape_dquote(cmd)
        cmd = cmd.replace("\n", r"\n")
        script = """
        on run argv
            tell application "Google Chrome"
                set URL of front window's active tab to "javascript:{" & "
                    var mycell = IPython.notebook.get_selected_cell();
                    mycell.set_text(\\"" & item 1 of argv & "\\");
                    mycell.execute();
                    var nextcell = IPython.notebook.insert_cell_below();
                    IPython.notebook.select_next();
                    IPython.notebook.scroll_to_cell(IPython.notebook.find_cell_index(nextcell));
                " & "}"
            end tell
        end run
        """
        subprocess.check_call(['osascript', '-e', script, cmd])

    def _dispatch_safari_jupyter(self, cmd):
        cmd = self.clean_cmd(cmd)
        cmd = self.escape_dquote(cmd)
        cmd = cmd.replace("\n", r"\n")
        script = """
        on run argv
            tell application "Safari"
                tell front window's current tab to do JavaScript "
                    var mycell = IPython.notebook.get_selected_cell();
                    mycell.set_text(\\"" & item 1 of argv & "\\");
                    mycell.execute();
                    var nextcell = IPython.notebook.insert_cell_below();
                    IPython.notebook.select_next();
                    IPython.notebook.scroll_to_cell(IPython.notebook.find_cell_index(nextcell));
                "
            end tell
        end run
        """
        subprocess.check_call(['osascript', '-e', script, cmd])

    def _dispatch_tmux(self, cmd):
        cmd = self.wrap_paste_magic_for_python(cmd)
        tmux = self.sget("tmux", "tmux")
        cmd = self.clean_cmd(cmd) + "\n"
        n = 200
        chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
        for chunk in chunks:
            subprocess.check_call([tmux, 'set-buffer', chunk])
            subprocess.check_call([tmux, 'paste-buffer', '-d'])

    def _dispatch_screen(self, cmd):
        cmd = self.wrap_paste_magic_for_python(cmd)
        screen = self.sget("screen", "screen")
        plat = sublime.platform()
        cmd = self.clean_cmd(cmd) + "\n"
        n = 200
        chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
        for chunk in chunks:
            if plat == "linux":
                chunk = chunk.replace("\\", r"\\")
                chunk = chunk.replace("$", r"\$")
            subprocess.check_call([screen, '-X', 'stuff', chunk])

    def _dispatch_gnome_terminal(self, cmd):
        cmd = self.wrap_paste_magic_for_python(cmd)
        wid = subprocess.check_call(["xdotool", "search", "--onlyvisible",
                                       "--class", "gnome-terminal"])
        sid = subprocess.check_call(["xdotool", "getactivewindow"]).decode("utf-8").strip()
        if wid:
            wid = wid.decode("utf-8").strip().split("\n")[-1]
            cmd = self.clean_cmd(cmd) + "\n"
            self.set_clipboard(cmd)
            subprocess.check_call(["xdotool", "windowfocus", wid])
            subprocess.check_call(["xdotool", "key", "--clearmodifiers", "ctrl+shift+v"])
            subprocess.check_call(["xdotool", "windowfocus", sid])
            self.reset_clipboard()

    def _dispatch_rstudio_linux(self, cmd):
        wid = subprocess.check_call(["xdotool", "search", "--onlyvisible", "--class", "rstudio"])
        if wid:
            wid = wid.decode("utf-8").strip().split("\n")[-1]
            cmd = self.clean_cmd(cmd)
            self.set_clipboard(cmd)
            subprocess.check_call(["xdotool", "key", "--window", wid,
                                     "--clearmodifiers", "ctrl+v"])
            subprocess.check_call(["xdotool", "key", "--window", wid,
                                     "--clearmodifiers", "Return"])
            self.reset_clipboard()

    @staticmethod
    def execute_ahk_script(script, args=[]):
        ahk_path = os.path.join(sublime.packages_path(),
                                'User', 'SendTextPlus', 'bin', 'AutoHotkeyU32')
        ahk_script_path = os.path.join(sublime.packages_path(),
                                       'User', 'SendTextPlus', 'bin', script)
        subprocess.check_call([ahk_path, ahk_script_path] + args)

    def _dispatch_cygwin(self, cmd):
        cmd = self.wrap_paste_magic_for_python(cmd)
        cmd = self.clean_cmd(cmd) + "\n"
        self.set_clipboard(cmd)
        self.execute_ahk_script("Cygwin.ahk")
        self.reset_clipboard()

    def _dispatch_cmder(self, cmd):
        cmd = self.wrap_paste_magic_for_python(cmd)
        cmd = self.clean_cmd(cmd) + "\n"
        self.set_clipboard(cmd)
        self.execute_ahk_script("Cmder.ahk")
        self.reset_clipboard()

    def _dispatch_r32_windows(self, cmd):
        cmd = self.clean_cmd(cmd) + "\n"
        self.set_clipboard(cmd)
        self.execute_ahk_script("Rgui.ahk", [self.sget("R32", "0")])
        self.reset_clipboard()

    def _dispatch_r64_windows(self, cmd):
        cmd = self.clean_cmd(cmd) + "\n"
        self.set_clipboard(cmd)
        self.execute_ahk_script("Rgui.ahk", [self.sget("R64", "1")])
        self.reset_clipboard()

    def _dispatch_rstudio_windows(self, cmd):
        cmd = self.clean_cmd(cmd)
        if cmd:
            self.set_clipboard(cmd)
            self.execute_ahk_script("RStudio.ahk")
            self.reset_clipboard()

    def _dispatch_sublimerepl(self, cmd):
        cmd = self.clean_cmd(cmd)
        window = sublime.active_window()
        view = window.active_view()
        external_id = view.scope_name(0).split(" ")[0].split(".", 1)[1]
        window.run_command(
            "repl_send", {"external_id": external_id, "text": cmd})
