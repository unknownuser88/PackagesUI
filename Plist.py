import sublime
import sublime_plugin
import re
import zipfile
import json 
import os
import webbrowser

bullet_enabled = '✔'
bullet_disabled = '☐'
reg = r"\s{4}(?:("+bullet_enabled+"|"+bullet_disabled+"))(\s)(.+?(?=\s{5,}))(\s+)(\s|\|)(\s+)(?:("+bullet_enabled+"|"+bullet_disabled+"))(\s)(.+?(?=\s{3,}))"

class ChangeFontSizeCommand(sublime_plugin.WindowCommand):
	def run(self, plus):
		plistView = None
		window = sublime.active_window()
		for view in window.views():
			vset = view.settings()
			if vset.get("plist.interface") == 'plist':
				plistView = view
		if plistView:
			if plus == 'reset':
				return plistView.settings().set("font_size", 12)

			oldSize = plistView.settings().get("font_size")
			newSize = oldSize + (1 if plus else -1)
			if newSize < 4 or newSize > 20:
				return
			print("newSize", newSize)
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

	def create_view(self):
		view = self.window.new_file()

		view.settings().set('color_scheme', "Packages/PackagesUI/Plist.hidden-tmTheme")
		view.settings().set("plist.interface", 'plist')
		view.settings().set('highlight_line', True)
		view.settings().set("line_numbers", True)
		view.settings().set("font_size", 12)
		view.settings().set("spell_check", False)
		view.settings().set("scroll_past_end", False)
		view.settings().set("draw_centered", False)
		view.settings().set("line_padding_bottom", 2)
		view.settings().set("line_padding_top", 2)
		view.settings().set("caret_style", "solid")
		view.settings().set("tab_size", 4)
		# view.settings().set("rulers", [65, 127])
		view.settings().set("default_encoding", "UTF-8")
		view.settings().set("show_minimap", False)
		view.settings().set("word_wrap", False)
		view.set_syntax_file('Packages/PackagesUI/syntax/Plist.sublime-syntax')
		view.set_scratch(True)
		view.set_name(bullet_enabled + " Packages UI")

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
			pname = u"    {nshan} {packName}".format(packName=pack, nshan=nshan)
			nameLen = len(pname)
			space = " "*(60-int(nameLen))
			e = "\n" if (index+1)%2==0  else "     |"
			l = u"{pname}{space}{e}".format(pname=pname,space=space, e=e)
			self.view.insert(edit, 0, l)

		header = sublime.load_resource("Packages/PackagesUI/popups/header.html")
		header += "\n" + "="*127 + "\n"
		self.view.insert(edit, 0, header)
		self.view.set_read_only(True)

		pt = self.view.text_point(3, 0)
		self.view.sel().clear()
		self.view.sel().add(sublime.Region(pt))
		self.view.show(pt)

def replace_last(source_string, replace_what, replace_with):
    head, _sep, tail = source_string.rpartition(replace_what)
    return head + replace_with + tail

class TogglePackCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		packs = []
		for cursor in self.view.sel():
			pack = None
			(row,col) = self.view.rowcol(cursor.begin())
			leftPack = col < 66;
			line_regions = self.view.lines(cursor)
			for line_region in line_regions:
				string = self.view.substr(line_region)
				match = re.match(reg, string)
				if not match:
					continue
				pack = match.group(3 if leftPack else 9)
				nshan = bullet_disabled if match.group(1 if leftPack else 7) == bullet_enabled else bullet_enabled

				if leftPack:
					string = string.replace(match.group(1 if leftPack else 7), nshan, 1)
				else:
					string = replace_last(string, match.group(1 if leftPack else 7), nshan)

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

class openHomepageCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		view = self.view
		popupCont = []
		packs = []
		for cursor in view.sel():
			pack = None
			(row,col) = view.rowcol(cursor.begin())
			leftPack = col < 66;
			line_regions = view.lines(cursor)
			for line_region in line_regions:
				string = view.substr(line_region)
				match = re.match(reg, string)
				if not match:
					continue
				pack = match.group(3 if leftPack else 9)

				if pack and pack not in packs:
					info = getPackInfo(pack)
					url  = info.get('url', False)	
					if url:
						webbrowser.open_new_tab(url)


class toggleInfoPanelCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		view = self.view
		popupCont = []
		packs = []
		for cursor in view.sel():
			pack = None
			(row,col) = view.rowcol(cursor.begin())
			leftPack = col < 66;
			line_regions = view.lines(cursor)
			for line_region in line_regions:
				string = view.substr(line_region)
				match = re.match(reg, string)
				if not match:
					continue
	
				pack = match.group(3 if leftPack else 9)

				if pack and pack not in packs:
					info = getPackInfo(pack)		
					infoToShow = [		
						"<p class='row'><span class='title'>Name:&nbsp;&nbsp;&nbsp;</span><span class='val'><a href='"+info.get('url', '')+"'>" + pack + "</a></span></p>",		
						"<p class='row'><span class='title version'>Version: </span><span class='val version'>" + info.get('version', '') + "</span></p>",		
						"<p class='desc'>" + info.get('description', '') + "</p>"
					]		
					packs.append(pack)		
					popupCont.append("".join(infoToShow))

		if popupCont:
			css = sublime.load_resource("Packages/PackagesUI/popups/info.css")
			html = sublime.load_resource("Packages/PackagesUI/popups/info.html").format(css=css, content="<br>".join(popupCont))
			view.show_popup(html, 0, -1, max_width=500, max_height=600, on_navigate=webbrowser.open_new_tab)

class TogglePopupHelpCommand(sublime_plugin.TextCommand):
    def run(self, edit, view_name = "help"):
        css = sublime.load_resource("Packages/PackagesUI/popups/help.css")
        html = sublime.load_resource("Packages/PackagesUI/popups/" + view_name + ".html").format(css=css)
        self.view.show_popup(html, 0, -1,  max_width=600, max_height=600)

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



