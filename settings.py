import sublime


class SettingManager:

    def __init__(self, view):
        self.s = sublime.load_settings("SendTextPlus.sublime-settings")
        self.view = view
        self.plat = sublime.platform()

    def match(self, d):
        match_platform = self.plat == d.get("platform", self.plat)
        scopes = d.get("scopes", None)
        pt = self.view.sel()[0].begin() if len(self.view.sel()) > 0 else 0
        match_scopes = not scopes or any([self.view.score_selector(pt, s) > 0 for s in scopes])
        return match_platform and match_scopes

    def get(self, key, default=None):
        # hijacking the setting if key exsits in top level
        if self.s.has(key) and self.s.get(key):
            return self.s.get(key)

        user_settings = self.s.get("user")
        if user_settings:
            for u in user_settings:
                if self.match(u) and key in u and u[key]:
                    return u[key]
        default_settings = self.s.get("defaults")
        for d in default_settings:
            if self.match(d) and key in d and d[key]:
                return d[key]
        return default
