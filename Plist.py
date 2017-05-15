import sublime
import sublime_plugin
import re

bullet_enabled = '✔'
bullet_disabled = '☐'

class PlistCommand(sublime_plugin.WindowCommand):
	def run(self):
		plistView = None
		window = sublime.active_window()
		for view in window.views():
			vset = view.settings()
			if vset.get("plist.interface") == 'plist':
				plistView = view

		if plistView:
			window.focus_view(plistView)
		else:
			plistView = self.create_view()

		plistView.run_command("renderlist")

	def settchange(self, view):
		print("pass")

	def create_view(self):
		view = self.window.new_file()

		view.settings().set('color_scheme', "Packages/PackagesUI/Plist.hidden-tmTheme")
		view.settings().set("plist.interface", 'plist')
		view.settings().set('highlight_line', True)
		view.settings().set("font_face", "Consolas")
		view.settings().set("line_numbers", True)
		view.settings().set("font_size", 13)
		# view.settings().set("rulers", [40])
		view.settings().set("word_wrap", True)
		view.set_syntax_file('Packages/PackagesUI/Plist.sublime-syntax')
		view.set_scratch(True)
		view.set_name(bullet_enabled + " Packages")

		# view.settings().add_on_change('ignored_packages', lambda: self.settchange(view))

		self.disable_other_plugins(view)

		return view

	def disable_other_plugins(self, view):
		if sublime.load_settings("Plist.sublime-settings").get("vintageous_friendly", False) is False:
			view.settings().set("__vi_external_disable", False)
	

class RenderlistCommand(sublime_plugin.TextCommand):
	def run(self, edit):

		print('render-----------------------------------------------------------------')
		self.view.set_read_only(False)
		selections = self.view.sel()
		full_region = sublime.Region(0, self.view.size())
		self.view.replace(edit, full_region, '')

		sett = sublime.load_settings('Package Control.sublime-settings')
		user_s = sublime.load_settings('Preferences.sublime-settings')

		installed_packages = sett.get('installed_packages', [])
		ignored_packages = user_s.get('ignored_packages', [])

		for index, pack in enumerate(installed_packages[::-1]):
			nshan = bullet_disabled if pack in ignored_packages else bullet_enabled
			l = u"\t{nshan} {packName}{e}".format(packName=pack, nshan=nshan, e="\n")
			self.view.insert(edit, 0, l)

		self.view.set_read_only(True)

		self.view.sel().clear()
		self.view.sel().add(sublime.Region(0))


class TogglePackCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		reg = r"^\s*(?:("+bullet_enabled+"|"+bullet_disabled+")(\s+)((?:[^\@\n]|(?<!\s)\@|\@(?=\s))*)([^\n]*))|^\s*(?:(-)(\s+(?:[^\@]|(?<!\s)\@|\@(?=\s))*))"

		for cursor in self.view.sel():
			line_region = self.view.line(cursor)
			string = self.view.substr(line_region)
			matches = re.finditer(reg, string)

			for match in matches:
				pack = match.group(3)
				nshan = bullet_disabled if match.group(1) == bullet_enabled else bullet_enabled
				string = string.replace(match.group(1), nshan)

			self.toggle(pack, self.view)
			self.view.set_read_only(False)
			self.view.replace(edit, line_region, string)
			self.view.set_read_only(True)

	def toggle(self, pack, view):
		user_s = sublime.load_settings('Preferences.sublime-settings')
		ignored_packages = user_s.get('ignored_packages', [])

		if pack in ignored_packages: # disabled
			ignored_packages.remove(pack)
		else:
			ignored_packages.append(pack)

		save_list_setting(user_s, 'Preferences.sublime-settings', "ignored_packages", ignored_packages)


############################
# IN-VIEW HELPER FUNCTIONS #
############################
		
def save_list_setting(settings, filename, name, new_value, old_value=None):
	new_value = list(set(new_value))
	new_value = sorted(new_value, key=lambda s: s.lower())

	if old_value is not None:
		if old_value == new_value:
			return

	settings.set(name, new_value)
	sublime.save_settings(filename)

