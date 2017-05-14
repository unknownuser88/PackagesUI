import sublime
import sublime_plugin
import re

try:
    str_cls = unicode
except (NameError):
    str_cls = str


class PlistCommand(sublime_plugin.WindowCommand):

	def run(self):
		view = self.window.new_file()
		view.set_syntax_file('Packages/plist/Plist.sublime-syntax')


		view.set_name("✔ Packages")
		view.set_scratch(True)
		# view.set_read_only(True)
		self.disable_other_plugins(view)

		# view.settings().add_on_change('ignored_packages', lambda: self.settchange(view))
		view.settings().set('color_scheme', "Packages/plist/Plist.hidden-tmTheme")
		view.settings().set('highlight_line', True)
		view.settings().set("font_size", 13)
		self.window.run_command("renderlist")


	def settchange(self, view):
		print("pass")

	def disable_other_plugins(self, view):
	    if sublime.load_settings("Plist.sublime-settings").get("vintageous_friendly", False) is False:
	        view.settings().set("__vi_external_disable", False)
		
class RenderlistCommand(sublime_plugin.TextCommand):
	def run(self, edit, line=0):

		print('render-----------------------------------------------------------------', line)

		self.view.set_read_only(False)
		selections = self.view.sel()
		full_region = sublime.Region(0, self.view.size())
		self.view.replace(edit, full_region, '')

		sett = sublime.load_settings('Package Control.sublime-settings')
		user_s = sublime.load_settings('Preferences.sublime-settings')

		installed_packages = sett.get('installed_packages', [])
		ignored_packages = user_s.get('ignored_packages', [])

		for index, pack in enumerate(installed_packages[::-1]):
			nshan="✔"
			if pack in ignored_packages:
				nshan="☐"
			e = "\n"
			l = u"\t{nshan} {packName}{e}".format(packName=pack, nshan=nshan, e=e)
			self.view.insert(edit, 0, l)
		self.view.set_read_only(True)
		self.view.sel().clear()
		self.view.sel().add(sublime.Region(line))
		sublime.set_timeout(lambda: self.view.show_at_center(sublime.Region(line)), 0)
		


class TogglepackCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		reg = r"^\s*(?:(\+|✓|✔|☐|√|\[x\])(\s+)((?:[^\@\n]|(?<!\s)\@|\@(?=\s))*)([^\n]*))|^\s*(?:(-)(\s+(?:[^\@]|(?<!\s)\@|\@(?=\s))*))"
		for r in self.view.sel():
			l = self.view.line(r)
			s = self.view.substr(l)
			matches = re.findall(reg, s)
			pack = matches[0][2]
			self.toggle(pack, self.view)

		linePos = [w for w in r][0]
		sublime.set_timeout(lambda: self.view.run_command("renderlist", {"line": linePos}), 500)

		

	def toggle(self, pack, view):
		user_s = sublime.load_settings('Preferences.sublime-settings')
		ignored_packages = load_list_setting(user_s, 'ignored_packages')

		if pack in ignored_packages: # disabled
			ignored_packages.remove(pack)
		else:
			ignored_packages.append(pack)

		save_list_setting(user_s, 'Preferences.sublime-settings', "ignored_packages", ignored_packages)

		


def load_list_setting(settings, name):
    value = settings.get(name)
    if not value:
        value = []
    if isinstance(value, str_cls):
        value = [value]
    return value


def save_list_setting(settings, filename, name, new_value, old_value=None):
    new_value = list(set(new_value))
    new_value = sorted(new_value, key=lambda s: s.lower())

    if old_value is not None:
        if old_value == new_value:
            return

    settings.set(name, new_value)
    sublime.save_settings(filename)
