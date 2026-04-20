import customtkinter as ctk
from launcher import Launcher
from tkinter import messagebox
from item.main import ItemView
import const, common
import yaml, copy, sys, socket, logging, os, json, platform

"""対応OSかチェック"""
def check_os_compatibility():

    if not const.IS_SUPPORTED:
        # ユーザーに分かりやすくメッセージを出す（Tkinterのダイアログを使用）
        error_msg = (
            f"エラー: お使いのOS（{platform.system()}）はサポートされていません。\n"
            "このツールは Windows または macOS でのみ動作します。"
        )
        print(error_msg) # コンソールにも出力
        
        # ダイアログを表示して終了
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("OS非対応", error_msg)
        
        sys.exit() # ここで完全にプログラムを終了させる

# 起動時に実行
check_os_compatibility()

button_texts = list(const.DATA_PATHS.keys())

# ログの基本設定
logging.basicConfig(
    level=logging.DEBUG, # 開発時はDEBUG、完成後はINFOにする
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 最後に選択したデータの空辞書
        self.last_selected_data = {cat: "" for cat in const.DATA_PATHS.keys()}

        # データの集中管理
        self.all_data = {text: {} for text in button_texts}
        self.old_all_data = {text: {} for text in button_texts}
        
        # ウィンドウ終了時のプロトコル
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 接続が完了するまでメインウィンドウを隠す
        self.withdraw() 
        
        # SSH/SFTPオブジェクトを保持する変数
        self.ssh_client = None
        self.sftp = None
        self.current_profile = None

        # ランチャー起動
        # 第二引数に接続成功時に実行したい関数を渡す
        self.launcher = Launcher(self, self.on_connected)

    """Launcherで接続成功時の処理"""
    def on_connected(self, client, sftp, profile):
        logger.info(f"接続成功: {profile['name']} - {sftp.getcwd()}")

        self.ssh_client = client
        self.sftp = sftp
        self.current_profile = profile
        
        self.load_all_categories()
        self.load_all_last_selections()

        # メインUIの構築を開始
        self.setup_ui()
        self.deiconify() # メインウィンドウを表示

    """メインののUI構築処理"""
    def setup_ui(self):
        self.title(f"Editor - {self.current_profile['name']}")
        self.geometry("1500x1000")

        self.top_frame = ctk.CTkFrame(self, height=40, fg_color=const.line_color, corner_radius=0)
        self.top_frame.pack(side="top", fill="x")
        self.top_frame.grid_propagate(False)
        self.top_frame.grid_rowconfigure(0, weight=1)
        self.top_frame.grid_columnconfigure(5, weight=1)

        self.buttons = {}
        for i, text in enumerate(button_texts):
            btn = ctk.CTkButton(
                self.top_frame, text=text, fg_color=const.top_tab_fg_color, 
                corner_radius=0, hover_color=const.top_tab_hover_color, text_color=const.text_color,
                command=lambda t=text: self.select_tab(t)
            )
            btn.grid(row=0, column=i, padx=(1, 0), sticky="ns")
            self.buttons[text] = btn

        self.top_controller_frame = ctk.CTkFrame(self.top_frame, height=40, fg_color=const.top_tab_fg_color, corner_radius=0)
        self.top_controller_frame.grid(row=0, column=5, padx=(1, 0), sticky="nsew")

        # 保存ボタンを生成時に保持しておく（配置はしない）
        self.save_btn = ctk.CTkButton(self.top_controller_frame, text="保存", width=60, fg_color="blue", command=self.save_all_categories)

        ctk.CTkFrame(self, height=1, fg_color=const.line_color, corner_radius=0).pack(side="top", fill="x")
        
        # 他タブで変わる部分(下部分)
        self.bottom_frame = ctk.CTkFrame(self, fg_color=const.line_color, corner_radius=0)
        self.bottom_frame.pack(side="top", fill="both", expand=True)
        
        # 初期選択
        self.select_tab(button_texts[0])

        self.bind_all("<Control-s>", lambda e: self.save_all_categories())

    """タブの選択"""
    def select_tab(self, text):
        if text not in const.DATA_PATHS.keys():
            logger.error("不正なデータ名です")
            return

        # 1. 既存のビューを明示的に削除
        if hasattr(self, "current_view") and self.current_view is not None:
            # 念のため名前が残らないようパックを解除してから消す
            self.current_view.pack_forget()
            self.current_view.destroy()
            self.current_view = None # 参照を空にする

        # 2. ボタンの見た目更新などはそのまま
        self.refresh_save_btn()
        for btn_text, btn in self.buttons.items():
            btn.configure(
                fg_color=const.top_tab_hover_color if btn_text == text else const.top_tab_fg_color,
                border_width=1 if btn_text == text else 0
            )

        logger.info(f"{text} タブを開きます。")

        # 3. インスタンス作成
        for widget in self.bottom_frame.winfo_children():
            widget.destroy()

        match text:
            case "アイテム":
                self.current_view = ItemView(
                    master=self.bottom_frame,
                    sftp=self.sftp,
                    profile=self.current_profile,
                    data=self.all_data[text],
                    old_data=self.old_all_data[text],
                    update_callback=self.update_tab,
                    category=text,
                    last_selection_ref=self.last_selected_data
                )
            # case "鉱石": ... 他のカテゴリも同様に

        # 4. 作成に成功したか確認してから pack
        if self.current_view is not None:
            self.current_view.pack(fill="both", expand=True)
        else:
            logger.error(f"{text} のビュー作成に失敗しました")

    """タブの更新時に呼ぶ関数"""
    def update_tab(self):
        self.refresh_save_btn()
        self.refresh_tab_headers()
        self.current_view.update_sidebar_text()

    """全てのタブボタンのテキストを更新（変更があれば * をつける）"""
    def refresh_tab_headers(self):
        for text, btn in self.buttons.items():
            if self.all_data[text] != self.old_all_data[text]:
                btn.configure(text=f"● {text}") # 目印をつける
            else:
                btn.configure(text=text)

    """セーブボタンの表示・非表示"""
    def refresh_save_btn(self):
        if self.all_data != self.old_all_data:
            self.save_btn.pack(side="right", padx=5)
        else:
            self.save_btn.pack_forget()

    """終了時の保存確認"""
    def on_closing(self):
        if self.all_data != self.old_all_data:
            if messagebox.askyesno("確認", "未保存の変更があります。破棄して終了しますか？"):
                self.destroy()
        else:
            self.save_all_last_selections()
            self.destroy()

    """起動時に全カテゴリのデータを一括で読み込む"""
    def load_all_categories(self):
        
        logger.info("全データの読み込みを開始します...")
        success_count = 0

        # const.DATA_PATHS のキー（アイテム、鉱石など）を順番に処理
        for category in const.DATA_PATHS.keys():
            self.load_category_data(category)
            success_count += 1
            
        logger.info(f"{success_count} 件のデータの読み込みが完了しました。")

    """
    指定されたカテゴリのデータを読み込む。
    失敗・不在時は空の状態で開始し、all_dataを更新する。
    """
    def load_category_data(self, category):

        # カテゴリごとの「箱（辞書）」がまだなければ作成
        if category not in self.all_data:
            self.all_data[category] = {}
        if category not in self.old_all_data:
            self.old_all_data[category] = {}

        base_path = self.current_profile['path'].rstrip('/')
        target_path = const.DATA_PATHS.get(category)
        target_file = base_path + target_path

        loaded_dict = {}
        
        try:
            with self.sftp.open(target_file, 'r') as f:
                content = f.read().decode('utf-8')
                loaded_dict = yaml.safe_load(content)
                if loaded_dict is None:
                    loaded_dict = {}
                
                item_count = len(loaded_dict)
                logger.info(f"[{category}] {item_count} 件のデータを読み込みました。")

        except (FileNotFoundError, IOError):
            logger.warning(f"[{category}] ファイルが存在しないため空のデータを作成しました。")
        except Exception as e:
            logger.warning(f"[{category}] 構文エラーまたはその他の例外が発生: {e} 空のデータを作成しました。")

        # 親クラスの管理辞書を更新
        self.all_data[category].clear()
        self.all_data[category].update(loaded_dict)
        self.old_all_data[category].clear()
        self.old_all_data[category].update(copy.deepcopy(self.all_data[category]))

    """変更があるすべてのカテゴリを順番に保存する"""
    def save_all_categories(self, event=None):
        logger.info("全データの保存を開始します...")
        success_count = 0
        target_categories = const.DATA_PATHS.keys()

        for category in target_categories:
            # 変更があるかチェック（効率化のため）
            if self.all_data[category] != self.old_all_data[category]:
                if self.save_category_data(category):
                    success_count += 1
            else:
                logger.debug(f"[{category}] 変更がないためスキップしました")

        self.update_tab()

        logger.info(f"{success_count} 件のデータの保存が完了しました。")

    """指定された1つのカテゴリを保存する"""
    def save_category_data(self, category):
        base_path = self.current_profile['path'].rstrip('/')
        target_path = const.DATA_PATHS.get(category)
        if not target_path:
            logger.error(f"[{category}] パスが定義されていないため保存できません")
            return False

        target_file = base_path + target_path
        
        # ディレクトリ作成
        target_dir = os.path.dirname(target_file)
        self._makedirs_sftp(target_dir)

        try:
            # データの件数をログに出す
            item_count = len(self.all_data[category])
            yaml_content = yaml.dump(self.all_data[category], allow_unicode=True, sort_keys=False)
            
            with self.sftp.open(target_file, 'w') as f:
                f.write(yaml_content)
            
            # バックアップ同期
            self.old_all_data[category].clear()
            self.old_all_data[category].update(copy.deepcopy(self.all_data[category]))
            
            logger.info(f"[{category}] {item_count} 件のデータを保存しました。")
            
            # タブの「●」マークなどを更新
            if hasattr(self, "refresh_tab_headers"):
                self.refresh_tab_headers()
                
            return True
        except Exception as e:
            logger.error(f"[{category}] 保存に失敗しました: {e}")
            return False

    """SFTP経由で再帰的にディレクトリを作成する(mkdir -p 相当)"""  
    def _makedirs_sftp(self, remote_directory):
        
        dirs = remote_directory.split('/')
        current_dir = ""
        for d in dirs:
            if not d: 
                current_dir += "/"
                continue
            current_dir += d + "/"
            try:
                self.sftp.stat(current_dir)
            except FileNotFoundError:
                self.sftp.mkdir(current_dir)
                logger.info(f"ディレクトリを作成: {current_dir}")
    
    """全カテゴリの最終選択IDをロードして、self.last_selected_dataを直接更新する。"""
    def load_all_last_selections(self):
        path = common.get_settings_path()
        default_results = {cat: "" for cat in const.DATA_PATHS.keys()}

        loaded_data = {}

        if os.path.exists(path):
            try:
                # ファイルサイズが0でないか確認
                if os.path.getsize(path) > 0:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                        # content が None だった場合の対策
                        if content:
                            loaded_data = content.get("last_selected", {})
                    logger.info("最終選択状態を読み込みました。")
                else:
                    logger.warning("設定ファイルが空のため、デフォルトを使用します。")
            except Exception as e:
                # ここで落ちても default_results があるので安全
                logger.error(f"JSON解析エラー (設定ファイルを初期化します): {e}")

        # 箱（self.last_selected_data）の中身を更新
        self.last_selected_data.clear()
        for cat in default_results.keys():
            self.last_selected_data[cat] = loaded_data.get(cat, "")

    """self.last_selected_data の中身をそのまま保存する"""
    def save_all_last_selections(self):

        path = common.get_settings_path()
        
        target_dir = os.path.dirname(path)
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        # 構造化して保存
        data_to_save = {
            "last_selected": self.last_selected_data
        }

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            logger.info("最終選択状態を保存しました。")
        except Exception as e:
            logger.error(f"設定保存失敗: {e}")

# 多重起動防止用のダミーソケット
# 他のアプリと被りにくい大きな数字（49152–65535）
LOCK_PORT = 65432
_lock_socket = None

def is_already_running():
    global _lock_socket
    _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _lock_socket.bind(("127.0.0.1", LOCK_PORT))
    except socket.error:
        return True
    return False

if __name__ == "__main__":
    if is_already_running():
        messagebox.showwarning("二重起動", "アプリは既に起動しています。")
        sys.exit()
    else:
        try:
            app = App()
            app.mainloop()
        finally:
            if _lock_socket:
                _lock_socket.close()