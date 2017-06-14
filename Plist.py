import sublime
import sublime_plugin
import re
import zipfile
import json 
import os 

bullet_enabled = '✔'
bullet_disabled = '☐'

class OnLoadedViewCommand( sublime_plugin.EventListener ):
	def check(self, view): 
		sett = view.settings()
		return sett.get("plist.interface") != 'plist' or not sett.get("showInfo")

	def on_selection_modified( self, view):
		if view.settings().get("plist.interface") != 'plist':
			return

		# markActivePack(view)

		if  not view.settings().get("showInfo"):
			return
			
		show_info_in_panel(view)

	def on_deactivated_async( self, view):
		if self.check(view):
			return
		sublime.active_window().run_command("hide_panel", {"panel": "output.info"})

	def on_activated_async( self, view):
		if self.check(view):
			return
		sublime.active_window().run_command("show_panel", {"panel": "output.info"})

class ChangeFontSizeCommand(sublime_plugin.WindowCommand):

	def run(self, plus):

		plistView = None
		window = sublime.active_window()
		for view in window.views():
			vset = view.settings()
			if vset.get("plist.interface") == 'plist':
				plistView = view
		if plistView:
			oldSize = plistView.settings().get("font_size")
			if plus:
				newSize = oldSize + 1
			else:
				newSize = oldSize - 1

			plistView.settings().set("font_size", newSize)

class PackagesUiCommand(sublime_plugin.WindowCommand):
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
		pass

	def create_view(self):
		view = self.window.new_file()

		view.settings().set('color_scheme', "Packages/PackagesUI/Plist.hidden-tmTheme")
		view.settings().set("plist.interface", 'plist')
		view.settings().set('highlight_line', True)
		# view.settings().set("font_face", "Consolas")
		view.settings().set("line_numbers", True)
		view.settings().set("font_size", 12)
		view.settings().set("spell_check", False)
		view.settings().set("scroll_past_end", False)
		view.settings().set("draw_centered", False)
		view.settings().set("line_padding_bottom", 2)
		view.settings().set("line_padding_top", 2)

		view.settings().set("caret_style", "solid")
		view.settings().set("tab_size", 4)
		view.settings().set("default_encoding", "UTF-8")
		view.settings().set("showInfo", False)
		# view.settings().set("rulers", [33])
		view.settings().set("word_wrap", False)
		view.set_syntax_file('Packages/PackagesUI/syntax/Plist.sublime-syntax')
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

		print('[Packages UI] render')
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
			l = u"    {nshan} {packName}{e}".format(packName=pack, nshan=nshan, e="\n")
			self.view.insert(edit, 0, l)

		header = u"""    ================             [t] toggle package
        PACKAGES                 [r] refresh view
    ================             [i] show info"""
		header += "\n" + "-"*60 + "\n"
		self.view.insert(edit, 0, header)
		self.view.set_read_only(True)

		pt = self.view.text_point(3, 0)
		self.view.sel().clear()
		self.view.sel().add(sublime.Region(pt))
		self.view.show(pt)
		sublime.active_window().run_command("hide_panel", {"panel": "output.info"})
		self.view.settings().set("showInfo", False)

class TogglePackCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		reg = r"^\s*(?:("+bullet_enabled+"|"+bullet_disabled+")(\s+)((?:[^\@\n]|(?<!\s)\@|\@(?=\s))*)([^\n]*))|^\s*(?:(-)(\s+(?:[^\@]|(?<!\s)\@|\@(?=\s))*))"
		packs = []
		for cursor in self.view.sel():
			pack = None
			line_regions = self.view.lines(cursor)
			for line_region in line_regions:
				string = self.view.substr(line_region)
				match = re.match(reg, string)
				if not match:
					continue
				pack = match.group(3)
				nshan = bullet_disabled if match.group(1) == bullet_enabled else bullet_enabled
				string = string.replace(match.group(1), nshan, 1)

				if pack and pack not in packs:
					packs.append(pack)
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

class toggleInfoPanelCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		showInfo = self.view.settings().get("showInfo")
		if showInfo:
			sublime.active_window().run_command("hide_panel", {"panel": "output.info"})
		else:
			show_info_in_panel(self.view)
			sublime.active_window().run_command("show_panel", {"panel": "output.info"})
		self.view.settings().set("showInfo", not showInfo)


def markActivePack(view):

	reg = r"^\s*(?:("+bullet_enabled+"|"+bullet_disabled+")(\s+))"
	packs = []
	regions = []
	for cursor in view.sel():
		pack = None
		line_regions = view.lines(cursor)
		for line_region in line_regions:
			string = view.substr(line_region)
			match = re.match(reg, string)
			if not match:
				continue
			regions.append(sublime.Region(line_region.a+1,line_region.b))

	view.add_regions('active', regions, "string.poiner", flags=sublime.DRAW_NO_FILL)

def show_info_in_panel(view):
	reg = r"^\s*(?:("+bullet_enabled+"|"+bullet_disabled+")(\s+)((?:[^\@\n]|(?<!\s)\@|\@(?=\s))*)([^\n]*))|^\s*(?:(-)(\s+(?:[^\@]|(?<!\s)\@|\@(?=\s))*))"
	popupCont = []
	packs = []
	for cursor in view.sel():
		pack = None
		line_regions = view.lines(cursor)
		for line_region in line_regions:
			string = view.substr(line_region)
			match = re.match(reg, string)
			if not match:
				continue
			pack = match.group(3)

			if pack and pack not in packs:
				info = getPackInfo(pack)
				packs.append(pack)
				infoToShow = [
					"Name:        " + pack,
					"Version:     " + info.get('version', ''),
					"Url:         " + info.get('url', ''),
					# "Paltforms:   " + ", ".join(info.get('platforms', [])),
					"Description: " + info.get('description', ''),
				]
				popupCont.append(u"\n".join(infoToShow))

	if popupCont:
		output_view = view.window().create_output_panel("info")
		output_view.set_read_only(False)
		text = ("\n" + u"-"*100 + "\n").join(popupCont)
		output_view.run_command("gs_replace_view_text", {"text": text, "nuke_cursors": False})
		output_view.set_syntax_file("Packages/PackagesUI/syntax/Packinfo.sublime-syntax")
		output_view.sel().clear()
		output_view.set_read_only(True)
		# view.window().run_command("show_panel", {"panel": "output.info"})

def save_list_setting(settings, filename, name, new_value, old_value=None):
	new_value = list(set(new_value))
	new_value = sorted(new_value, key=lambda s: s.lower())

	if old_value is not None:
		if old_value == new_value:
			return

	settings.set(name, new_value)
	sublime.save_settings(filename)

def getPackInfo(package):
	package_location = os.path.join(sublime.installed_packages_path(), package + ".sublime-package")

	if not os.path.exists(package_location):
		package_location = os.path.join(os.path.dirname(sublime.packages_path()), "Packages", package)

		with open(os.path.join(package_location, "package-metadata.json")) as pack:    
			data = json.load(pack)
			return data

		if not os.path.isdir(package_location):
			return False

	if package_location:
		with zipfile.ZipFile(sublime.installed_packages_path() + '/' + package + '.sublime-package', "r") as z:
			file = z.read('package-metadata.json')
			d = json.loads(file.decode("utf-8"))
		return d
	return False



