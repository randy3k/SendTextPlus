import sublime
import sublime_plugin
import os
from .textgetter import TextGetter, \
    RTextGetter, \
    PythonTextGetter, \
    JuliaTextGetter, \
    MarkDownTextGetter
from .textsender import TextSender


class SendTextPlusBuild(sublime_plugin.WindowCommand):

    def run(self, cmd=None, prog=None):
        self.window.active_view().run_command(
            "send_text_plus",
            {"cmd": cmd, "prog": prog}
        )


class SendTextPlusCommand(sublime_plugin.TextCommand):

    @staticmethod
    def escape_dquote(cmd):
        cmd = cmd.replace('\\', '\\\\')
        cmd = cmd.replace('"', '\\"')
        return cmd

    def resolve(self, cmd):
        view = self.view
        file = view.file_name()
        if file:
            file_name = os.path.basename(file)
            file_path = os.path.dirname(file)
            file_base_name, file_ext = os.path.splitext(file_name)
            cmd = cmd.replace("$file_path", self.escape_dquote(file_path))
            cmd = cmd.replace("$file_name", file_name)
            cmd = cmd.replace("$file_base_name", file_base_name)
            cmd = cmd.replace("$file_extension", file_ext)
            cmd = cmd.replace("$file", self.escape_dquote(file))

        pd = view.window().project_data()
        if pd and "folders" in pd and len(pd["folders"]) > 0:
            project_path = pd["folders"][0].get("path")
            if project_path:
                cmd = cmd.replace("$project_path", self.escape_dquote(project_path))

        # resolve $project_path again
        if file and file_path:
            cmd = cmd.replace("$project_path", self.escape_dquote(file_path))

        if len(view.sel()) == 1:
            word = view.substr(view.sel()[0])
            if not word:
                word = view.substr(view.word(view.sel()[0].begin()))

            cmd = cmd.replace("$selection", word)

        return cmd

    def run(self, edit, cmd=None, prog=None):
        view = self.view
        pt = view.line(view.sel()[0]).begin() if len(view.sel()) > 0 else 0

        if cmd:
            cmd = self.resolve(cmd)
        else:
            if view.score_selector(pt, "source.r"):
                getter = RTextGetter(view)
            elif view.score_selector(pt, "source.python"):
                getter = PythonTextGetter(view)
            elif view.score_selector(pt, "source.julia"):
                getter = JuliaTextGetter(view)
            elif view.score_selector(pt, "punctuation.definition.fenced.markdown"):
                getter = MarkDownTextGetter(view)
            else:
                getter = TextGetter(view)
            cmd = getter.get_text()

        sender = TextSender(view, prog)
        sender.send_text(cmd)


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
            self.app_list = ["[Defaults]", "gnome-terminal", "tmux", "screen",
                             "RStudio", "SublimeREPL"]
        else:
            sublime.error_message("Platform not supported!")

        self.show_quick_panel(self.app_list, self.on_done)

    def on_done(self, action):
        if action == -1:
            return
        settings = sublime.load_settings('SendTextPlus.sublime-settings')
        settings.set("prog", self.app_list[action] if action > 0 else None)
        sublime.save_settings('SendTextPlus.sublime-settings')
