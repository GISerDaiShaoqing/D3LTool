# -*- coding: utf-8 -*-
"""Main application window."""

from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QIcon
from PySide6.QtWidgets import (QDialog, QLabel, QMainWindow, QMessageBox,
                               QSplitter, QVBoxLayout, QWidget)

from .. import __version__, auth, config, engine, i18n, search
from .. import APP_NAME
from .bridge import EngineBridge
from .login_dialog import LoginDialog
from .results_table import ResultsTable
from .search_panel import SearchPanel
from .settings_dialog import SettingsDialog
from .task_table import TaskTable

RES_DIR = Path(__file__).resolve().parent.parent / "resources"

SITE_URLS = {
    "site_home": "https://gisersqdai.top/D3LTool/",
    "site_baidupan": "https://pan.baidu.com/share/home?uk=2855623577"
                     "&suk=QR0keGnZkZWNh9Pf3aQyaQ&view=share#category/type=0",
    "site_blog": "https://gisersqdai.top/",
    "site_nasa": "https://ladsweb.modaps.eosdis.nasa.gov/",
    "site_nasa_tools": "https://ladsweb.modaps.eosdis.nasa.gov/tools-and-services/",
}

# 2026-09 verified: domains moved / refreshed (old rscloudmart.com domain
# was taken over by spam and dropped in favour of the national platform)
RS_URLS = [
    ("rs_envi", "https://www.cnblogs.com/enviidl"),
    ("rs_cpeos", "https://www.cpeos.org.cn/"),
    ("rs_chinageo", "https://www.chinageoss.cn/"),
    ("rs_gscloud", "https://www.gscloud.cn/"),
    ("rs_nrscc", "http://www.nrscc.most.cn/"),
    ("rs_usgs", "https://www.usgs.gov/landsat-missions"),
    ("rs_cresda", "https://www.cresda.cn/"),
]


class _SearchThread(QThread):
    done = Signal(list, float)     # granules, elapsed seconds
    failed = Signal(str)

    def __init__(self, params, parent=None):
        super().__init__(parent)
        self._params = params

    def run(self):
        import time as _time

        t0 = _time.time()
        try:
            granules = search.run_search(self._params)
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        self.done.emit(granules, _time.time() - t0)


class MainWindow(QMainWindow):
    def __init__(self):
        self.config = config.load_config()
        i18n.set_language(self.config.get("language", "zh"))

        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{__version__}")
        self.resize(1100, 680)
        icon_file = RES_DIR / "D3L.ico"
        if icon_file.exists():
            self.setWindowIcon(QIcon(str(icon_file)))

        self.engine = engine.DownloadEngine(
            session_factory=auth.new_download_session,
            dest_dir=Path(self.config["download_dir"]),
            max_workers=int(self.config.get("max_workers", 3)),
        )
        self.bridge = EngineBridge(self)
        self.bridge.attach(self.engine)
        self._search_thread = None

        self._build_ui()
        self._build_menus()
        self._refresh_login_status()

    # -------------------------------------------------------------------- UI

    def _build_ui(self):
        central = QWidget(self)
        layout = QVBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.search_panel = SearchPanel(splitter)
        self.results_table = ResultsTable(splitter)
        self.task_table = TaskTable(self.engine, splitter)
        self.task_table.set_engine(self.engine)

        right = QSplitter(Qt.Orientation.Vertical)
        right.addWidget(self.results_table)
        right.addWidget(self.task_table)
        right.setSizes([380, 300])

        splitter.addWidget(self.search_panel)
        splitter.addWidget(right)
        splitter.setSizes([340, 760])
        layout.addWidget(splitter)
        self.setCentralWidget(central)

        self.statusBar().showMessage(i18n.tr("status_logged_out"))

        self.search_panel.search_requested.connect(self._do_search)
        self.results_table.enqueue_requested.connect(self._enqueue)
        self.bridge.status.connect(self.task_table.on_status)
        self.bridge.progress.connect(self.task_table.on_progress)
        self.bridge.cleared.connect(self.task_table.on_cleared)

    def _build_menus(self):
        # ---- websites: personal + NASA
        menu_sites = self.menuBar().addMenu(i18n.tr("menu_sites"))
        for key in ("site_home", "site_baidupan", "site_blog"):
            act = QAction(i18n.tr(key), self)
            act.triggered.connect(lambda _c=False, u=SITE_URLS[key]: self._open_url(u))
            menu_sites.addAction(act)
        menu_sites.addSeparator()
        for key in ("site_nasa", "site_nasa_tools"):
            act = QAction(i18n.tr(key), self)
            act.triggered.connect(lambda _c=False, u=SITE_URLS[key]: self._open_url(u))
            menu_sites.addAction(act)

        # ---- remote sensing resources (kept from v1.0)
        menu_rs = self.menuBar().addMenu(i18n.tr("menu_rs"))
        for key, url in RS_URLS:
            act = QAction(i18n.tr(key), self)
            act.triggered.connect(lambda _c=False, u=url: self._open_url(u))
            menu_rs.addAction(act)

        menu_language = self.menuBar().addMenu(i18n.tr("menu_language"))
        self._lang_actions = QActionGroup(self)
        for code, label in (("zh", i18n.tr("lang_zh")), ("en", i18n.tr("lang_en"))):
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(code == i18n.get_language())
            act.setData(code)
            act.triggered.connect(lambda _checked, c=code: self._switch_language(c))
            self._lang_actions.addAction(act)
            menu_language.addAction(act)

        menu_settings = self.menuBar().addMenu(i18n.tr("menu_settings"))
        self.act_login = QAction(i18n.tr("act_login"), self)
        self.act_login.triggered.connect(self._on_login)
        self.act_logout = QAction(i18n.tr("act_logout"), self)
        self.act_logout.triggered.connect(self._on_logout)
        self.act_settings = QAction(i18n.tr("act_settings"), self)
        self.act_settings.triggered.connect(self._on_settings)
        menu_settings.addAction(self.act_login)
        menu_settings.addAction(self.act_logout)
        menu_settings.addSeparator()
        menu_settings.addAction(self.act_settings)

        menu_help = self.menuBar().addMenu(i18n.tr("menu_help"))
        act_donate = QAction(i18n.tr("act_donate"), self)
        act_donate.triggered.connect(self._on_donate)
        menu_help.addAction(act_donate)
        act_about = QAction(i18n.tr("act_about"), self)
        act_about.triggered.connect(self._on_about)
        menu_help.addAction(act_about)
        menu_help.addSeparator()
        act_quit = QAction(i18n.tr("act_quit"), self)
        act_quit.triggered.connect(self.close)
        menu_help.addAction(act_quit)

        toolbar = self.addToolBar("main")
        toolbar.addAction(self.act_login)
        toolbar.addAction(self.act_settings)
        self._menus_built = True

    # ----------------------------------------------------------------- login

    def _refresh_login_status(self):
        if auth.is_authenticated():
            user = auth.current_user() or self.config.get("username", "")
            self.statusBar().showMessage(i18n.tr("status_logged_in", user=user))
            self.act_login.setEnabled(False)
            self.act_logout.setEnabled(True)
        else:
            self.statusBar().showMessage(i18n.tr("status_logged_out"))
            self.act_login.setEnabled(True)
            self.act_logout.setEnabled(False)

    def _on_login(self):
        dlg = LoginDialog(self, username=self.config.get("username", ""))
        if dlg.exec() == LoginDialog.DialogCode.Accepted:
            if auth.is_authenticated():
                if dlg.remember_username():
                    self.config = config.update_config(username=dlg.logged_username())
                self._refresh_login_status()

    def _on_logout(self):
        try:
            import earthaccess

            earthaccess.auth.logout()
        except Exception:
            pass
        auth._logged_in_user["name"] = ""
        self._refresh_login_status()

    # ---------------------------------------------------------------- search

    def _do_search(self, params):
        if self._search_thread is not None and self._search_thread.isRunning():
            return
        self.statusBar().showMessage(i18n.tr("search_running", product=params.short_name))
        self.search_panel.set_searching(True)
        self._search_thread = _SearchThread(params, self)
        self._search_thread.done.connect(self._on_search_done)
        self._search_thread.failed.connect(self._on_search_failed)
        self._search_thread.start()

    def _on_search_done(self, granules, elapsed):
        self.search_panel.set_searching(False)
        self._search_thread = None
        if not granules:
            self.results_table.clear()
            self.statusBar().showMessage(i18n.tr("search_none"))
            return
        self.results_table.populate(granules)
        self.statusBar().showMessage(i18n.tr("search_done", n=len(granules), secs=elapsed))

    def _on_search_failed(self, message):
        self.search_panel.set_searching(False)
        self._search_thread = None
        self.statusBar().showMessage(i18n.tr("search_failed", reason=message))
        QMessageBox.warning(self, i18n.tr("err_title"),
                            i18n.tr("search_failed", reason=message))

    # --------------------------------------------------------------- download

    def _ensure_logged_in(self) -> bool:
        if auth.is_authenticated():
            return True
        QMessageBox.information(self, i18n.tr("info_title"), i18n.tr("msg_need_login"))
        self._on_login()
        return auth.is_authenticated()

    def _enqueue(self, items):
        if not items:
            QMessageBox.information(self, i18n.tr("info_title"), i18n.tr("msg_enqueue_none"))
            return
        if not self._ensure_logged_in():
            return
        self.engine.dest_dir = Path(self.config["download_dir"])
        self.engine.max_workers = int(self.config.get("max_workers", 3))
        for it in items:
            self.engine.add(it["url"], filename=it["filename"],
                            size_hint=it.get("size_bytes", 0))
        self.statusBar().showMessage(f"+{len(items)} → {self.engine.dest_dir}")

    # --------------------------------------------------------------- settings

    def _on_settings(self):
        def apply(values):
            self.config = config.update_config(**values)
            self.engine.dest_dir = Path(self.config["download_dir"])
            self.engine.max_workers = int(self.config["max_workers"])
            self.statusBar().showMessage(i18n.tr("settings_saved"))

        SettingsDialog(self, config=self.config, on_save=apply).exec()

    def _switch_language(self, code):
        self.config = config.update_config(language=code)
        i18n.set_language(code)
        QMessageBox.information(self, i18n.tr("info_title"),
                                i18n.tr("msg_lang_restart",
                                        lang="中文" if code == "zh" else "English"))

    def _on_about(self):
        QMessageBox.about(self, i18n.tr("act_about"), i18n.tr("about_text"))

    # ------------------------------------------------------- links & donate

    def _open_url(self, url):
        QDesktopServices.openUrl(QUrl(url))

    def _on_donate(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(i18n.tr("act_donate"))
        layout = QVBoxLayout(dlg)
        pic = QLabel(dlg)
        gif = RES_DIR / "alipay.gif"
        if gif.exists():
            from PySide6.QtGui import QPixmap

            pic.setPixmap(QPixmap(str(gif)).scaled(
                260, 260, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(pic)
        text = QLabel(i18n.tr("donate_text"), dlg)
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text)
        dlg.exec()
