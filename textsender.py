import sublime
import os
import re
import subprocess
import threading


def sget(key, default=None):
    s = sublime.load_settings("SendText+.sublime-settings")
    return s.get(key, default)


def get_program(view):
    plat = sublime.platform()
    prog = sget("prog")
    if prog:
        return prog
    defaults = sget("defaults")
    pt = view.sel()[0].begin() if len(view.sel()) > 0 else 0

    for d in defaults:
        match_platform = plat == d.get("platform", plat)
        scopes = d.get("scopes", None)
        match_scopes = not scopes or any([view.score_selector(pt, s) > 0 for s in scopes])
        if match_platform and match_scopes and "prog" in d:
            return d.get("prog")
    return None


class TextSender:
    cb = None
    thread = None

    def __init__(self, view, prog=None):
        self.view = view
        if not prog:
            prog = get_program(view)
        plat = sublime.platform()
        function_str = "_dispatch_" + prog.lower().replace("-", "_")
        if getattr(self, function_str + "_" + plat, None):
            function_str = function_str + "_" + plat
        self._send_text = eval("self." + function_str)

    def send_text(self, cmd):
        self._send_text(cmd)

    @staticmethod
    def clean_cmd(cmd):
        cmd = cmd.expandtabs(4)
        cmd = cmd.rstrip('\n')
        if sget("remove_line_indentation", True) and len(re.findall("\n", cmd)) == 0:
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
        cmd = self.clean_cmd(cmd)
        cmd = self.escape_dquote(cmd)
        args = ['osascript']
        args.extend(['-e',
                     'tell application "Terminal" to do script "' + cmd + '" in front window'])
        subprocess.Popen(args)

    @staticmethod
    def iterm_version():
        args = ['osascript', '-e', 'tell application "iTerm" to get version']
        ver = subprocess.check_output(args).decode().strip()
        return tuple((int(i) for i in re.split(r"\.", ver)[0:2]))

    def _dispatch_iterm(self, cmd):
        cmd = self.clean_cmd(cmd)
        if self.iterm_version() >= (2, 9):
            n = 1000
            chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
            for chunk in chunks:
                subprocess.call([
                    'osascript', '-e',
                    'tell application "iTerm" to tell the current window ' +
                    'to tell current session to write text "' +
                    self.escape_dquote(chunk) + '" without newline'
                ])
            subprocess.call([
                'osascript', '-e',
                'tell application "iTerm" to tell the current window ' +
                'to tell current session to write text ""'
            ])
        else:
            subprocess.call([
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
        subprocess.Popen(args)

    def _dispatch_rstudio_osx(self, cmd):
        cmd = self.clean_cmd(cmd)
        script = """
        on run argv
            tell application "RStudio"
                cmd item 1 of argv
            end tell
        end run
        """
        subprocess.call(['osascript', '-e', script, cmd])

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
        subprocess.call(['osascript', '-e', script, cmd])

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
        subprocess.call(['osascript', '-e', script, cmd])

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
        subprocess.call(['osascript', '-e', script, cmd])

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
        subprocess.call(['osascript', '-e', script, cmd])

    def _dispatch_tmux(self, cmd):
        tmux = sget("tmux", "tmux")
        cmd = self.clean_cmd(cmd) + "\n"
        n = 200
        chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
        for chunk in chunks:
            subprocess.call([tmux, 'set-buffer', chunk])
            subprocess.call([tmux, 'paste-buffer', '-d'])

    def _dispatch_screen(self, cmd):
        screen = sget("screen", "screen")
        plat = sublime.platform()
        cmd = self.clean_cmd(cmd) + "\n"
        n = 200
        chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
        for chunk in chunks:
            if plat == "linux":
                chunk = chunk.replace("\\", r"\\")
                chunk = chunk.replace("$", r"\$")
            subprocess.call([screen, '-X', 'stuff', chunk])

    def _dispatch_gnome_terminal(self, cmd):
        wid = subprocess.check_output(["xdotool", "search", "--onlyvisible",
                                       "--class", "gnome-terminal"])
        sid = subprocess.check_output(["xdotool", "getactivewindow"]).decode("utf-8").strip()
        if wid:
            wid = wid.decode("utf-8").strip().split("\n")[-1]
            cmd = self.clean_cmd(cmd) + "\n"
            self.set_clipboard(cmd)
            subprocess.check_output(["xdotool", "windowfocus", wid])
            subprocess.check_output(["xdotool", "key", "--clearmodifiers", "ctrl+shift+v"])
            subprocess.check_output(["xdotool", "windowfocus", sid])
            self.reset_clipboard()

    def _dispatch_rstudio_linux(self, cmd):
        wid = subprocess.check_output(["xdotool", "search", "--onlyvisible", "--class", "rstudio"])
        if wid:
            wid = wid.decode("utf-8").strip().split("\n")[-1]
            cmd = self.clean_cmd(cmd)
            self.set_clipboard(cmd)
            subprocess.check_output(["xdotool", "key", "--window", wid,
                                     "--clearmodifiers", "ctrl+v"])
            subprocess.check_output(["xdotool", "key", "--window", wid,
                                     "--clearmodifiers", "Return"])
            self.reset_clipboard()

    @staticmethod
    def execute_ahk_script(script, args=[]):
        ahk_path = os.path.join(sublime.packages_path(),
                                'User', 'SendTextPlus', 'bin', 'AutoHotkeyU32')
        ahk_script_path = os.path.join(sublime.packages_path(),
                                       'User', 'SendTextPlus', 'bin', script)
        subprocess.check_output([ahk_path, ahk_script_path] + args)

    def _dispatch_cygwin(self, cmd):
        cmd = self.clean_cmd(cmd) + "\n"
        self.set_clipboard(cmd)
        self.execute_ahk_script("Cygwin.ahk")
        self.reset_clipboard()

    def _dispatch_cmder(self, cmd):
        cmd = self.clean_cmd(cmd) + "\n"
        self.set_clipboard(cmd)
        self.execute_ahk_script("Cmder.ahk")
        self.reset_clipboard()

    def _dispatch_r32_windows(self, cmd):
        cmd = self.clean_cmd(cmd) + "\n"
        self.set_clipboard(cmd)
        self.execute_ahk_script("Rgui.ahk", [sget("R32", "0")])
        self.reset_clipboard()

    def _dispatch_r64_windows(self, cmd):
        cmd = self.clean_cmd(cmd) + "\n"
        self.set_clipboard(cmd)
        self.execute_ahk_script("Rgui.ahk", [sget("R64", "1")])
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


class PythonTextSender(TextSender):

    def send_text(self, cmd):
        if self._send_text != self._dispatch_chrome_jupyter and \
                self._send_text != self._dispatch_safari_jupyter:

            cmd = cmd.rstrip("\n")
            if len(re.findall("\n", cmd)) > 0:
                cmd = "%cpaste -q\n" + cmd + "\n--"

        TextSender.send_text(self, cmd)
