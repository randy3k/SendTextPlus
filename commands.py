import sublime
import sublime_plugin
import os
from .sendtext import TextGetter, TextSender


def escape_dquote(cmd):
    cmd = cmd.replace('\\', '\\\\')
    cmd = cmd.replace('"', '\\"')
    return cmd


class SendTextPlusCommand(sublime_plugin.TextCommand):

    def resolve(self, cmd):
        view = self.view
        file = view.file_name()
        if file:
            file_name = os.path.basename(file)
            file_path = os.path.dirname(file)
            file_base_name, file_ext = os.path.splitext(file_name)
            cmd = cmd.replace("$file_path", escape_dquote(file_path))
            cmd = cmd.replace("$file_name", escape_dquote(file_name))
            cmd = cmd.replace("$file_base_name", escape_dquote(file_base_name))
            cmd = cmd.replace("$file_extension", file_ext)
            cmd = cmd.replace("$file", escape_dquote(file))

        pd = view.window().project_data()
        if pd and "folders" in pd and len(pd["folders"]) > 0:
            project_path = pd["folders"][0].get("path")
            if project_path:
                cmd = cmd.replace("$project_path", escape_dquote(project_path))

        # resolve $project_path again
        if file and file_path:
            cmd = cmd.replace("$project_path", escape_dquote(file_path))

        return cmd

    def run(self, edit, cmd=None):
        view = self.view
        if cmd:
            sender = TextSender.init(view)
            sender.send_text(self.resolve(cmd))
        else:
            getter = TextGetter.init(view)
            cmd = getter.get_text()
            sender = TextSender.init(view)
            sender.send_text(cmd)


class SendTextPlus(sublime_plugin.WindowCommand):

    def run(self, cmd):
        self.window.active_view().run_command("send_text_plus", {"cmd": cmd})


class SendTextPlusChooseProgramCommand(sublime_plugin.WindowCommand):

    def show_quick_panel(self, options, done):
        sublime.set_timeout(lambda: self.window.show_quick_panel(options, done), 10)

    def run(self):
        plat = sublime.platform()
        if plat == 'osx':
            self.app_list = ["[Defaults]", "Terminal", "iTerm",
                             "R", "RStudio", "Chrome-RStudio", "Chrome-Jupyter",
                             "Safari-RStudio", "Safari-Jupyter",
                             "tmux", "screen", "SublimeREPL"]
        elif plat == "windows":
            self.app_list = ["[Defaults]", "Cmder", "Cygwin",
                             "R32", "R64", "RStudio", "SublimeREPL"]
        elif plat == "linux":
            self.app_list = ["[Defaults]", "tmux", "screen", "SublimeREPL"]
        else:
            sublime.error_message("Platform not supported!")

        self.show_quick_panel(self.app_list, self.on_done)

    def on_done(self, action):
        if action == -1:
            return
        settings = sublime.load_settings('SendText+.sublime-settings')
        settings.set("prog", self.app_list[action] if action > 0 else None)
        sublime.save_settings('SendText+.sublime-settings')
