import paramiko
import customtkinter as ctk
import os
import json
from tkinter import filedialog, messagebox
import common
import traceback, logging
from __future__ import annotations
from typing import TYPE_CHECKING, Callable, TypedDict, List

if TYPE_CHECKING:
    from main import App

CONFIG_FILE = common.get_server_profiles()

logger = logging.getLogger(__name__)

class Profile(TypedDict):
    name: str
    host: str
    port: str
    user: str
    path: str
    key: str

class ConfigData(TypedDict):
    list: List[Profile]
    last_selected: str

"""サーバー情報を追加・編集するためのサブウィンドウ"""
class AddServerWindow(ctk.CTkToplevel):
    def __init__(self, parent, edit_index=None):
        super().__init__(parent)
        self.parent = parent
        self.edit_index = edit_index 
        self.title("接続設定")
        self.geometry("400x620")
        
        self.attributes("-topmost", True)
        self.grab_set()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.label = ctk.CTkLabel(self, text="サーバー情報入力", font=("", 16, "bold"))
        self.label.pack(pady=15)

        # 各エントリーを変数として保持
        self.name_entry = self.create_input("プロファイル名 (例: マイクラ鯖1)")
        self.host_entry = self.create_input("ホスト名 (IPアドレス)")
        self.port_entry = self.create_input("ポート番号", "22")
        self.user_entry = self.create_input("ユーザー名")
        self.path_entry = self.create_input("サーバーのフォルダパス", "/C:/Users/...")
        
        ctk.CTkLabel(self, text="秘密鍵").pack(pady=(10, 0))
        self.key_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.key_frame.pack(pady=5, padx=20, fill="x")
        self.key_entry = ctk.CTkEntry(self.key_frame)
        self.key_entry.pack(side="left", expand=True, fill="x", padx=(0, 5))
        self.key_btn = ctk.CTkButton(self.key_frame, text="選択", width=50, command=self.select_key)
        self.key_btn.pack(side="right")

        self.add_btn = ctk.CTkButton(self, text="保存", fg_color="green", command=self.save_and_close)
        self.add_btn.pack(pady=20)

    def create_input(self, placeholder, default=""):
        ctk.CTkLabel(self, text=placeholder).pack(pady=(5, 0))
        entry = ctk.CTkEntry(self, width=300)
        entry.insert(0, default)
        entry.pack(pady=5)
        return entry

    def select_key(self):
        file_path = filedialog.askopenfilename(title="秘密鍵ファイルを選択", parent=self)
        if file_path:
            self.key_entry.delete(0, "end")
            self.key_entry.insert(0, file_path)

    def on_closing(self):
        if messagebox.askyesno("確認", "編集内容を破棄して閉じますか？", parent=self):
            self.destroy()

    def save_and_close(self):
        # バックスラッシュをスラッシュに変換して統一
        server_path = self.path_entry.get().replace("\\", "/")
        key_path = self.key_entry.get().replace("\\", "/")

        data = {
            "name": self.name_entry.get(),
            "host": self.host_entry.get(),
            "port": self.port_entry.get(),
            "user": self.user_entry.get(),
            "path": server_path,
            "key": key_path
        }

        if all(data.values()):
            if self.edit_index is not None:
                # 編集（更新）時は update_profile を呼び出す
                # ※Launcher側で名前重複チェックを行う
                success = self.parent.update_profile(self.edit_index, data, self)
            else:
                # 新規追加時は add_profile を呼び出す
                success = self.parent.add_profile(data, self)
            
            # 処理に成功（重複なし等）したらウィンドウを閉じる
            if success:
                self.destroy()
        else:
            messagebox.showwarning("入力エラー", "すべての項目を入力してください。", parent=self)

class Launcher(ctk.CTkToplevel):
    def __init__(self, parent: App, on_connect_callback: Callable[[paramiko.SSHClient, paramiko.SFTPClient, Profile], None]):
        super().__init__(parent)

        self.add_window: AddServerWindow = None

        self.parent = parent
        self.on_connect_callback = on_connect_callback # 成功時に実行する関数
        
        self.title("MC Server Manager")
        self.geometry("400x550")

        data = self.load_profiles()
        self.profiles = data["list"]
        initial_value = data.get("last_selected", "")
        self.selected_profile = ctk.StringVar(value=initial_value)

        # UI構築
        self.label = ctk.CTkLabel(self, text="接続するサーバーを選択", font=("", 18, "bold"))
        self.label.pack(pady=20)
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=350, height=300)
        self.scroll_frame.pack(pady=10, padx=20)
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=20)
        self.add_btn = ctk.CTkButton(self.btn_frame, text="追加", width=80, command=self.open_add_window)
        self.add_btn.pack(side="left", padx=5)
        self.connect_btn = ctk.CTkButton(self.btn_frame, text="接続", width=80, fg_color="green", command=self.connect_server)
        self.connect_btn.pack(side="left", padx=5)

        self.refresh_list()

    """設定ファイルを読み込み、ConfigData型として返す"""
    def load_profiles(self)-> ConfigData:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
                    else:
                        return {"list": data, "last_selected": ""}
            except: pass
        return {"list": [], "last_selected": ""}

    """設定をファイルを保存"""
    def save_profiles(self):
        data: ConfigData = {"list": self.profiles, "last_selected": self.selected_profile.get()}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    """プロファイルの一覧更新"""
    def refresh_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        for idx, p in enumerate(self.profiles):
            row_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            row_frame.pack(pady=2, padx=5, fill="x")

            rb = ctk.CTkRadioButton(
                row_frame, text=f"{p['name']} ({p['host']})", 
                variable=self.selected_profile, value=p['name'],
                command=self.save_profiles
            )
            rb.pack(side="left", padx=5, pady=5, expand=True, anchor="w")

            edit_btn_row = ctk.CTkButton(
                row_frame, text="編集", width=60, height=24, fg_color="gray",
                command=lambda i=idx: self.open_edit_window_by_index(i)
            )
            edit_btn_row.pack(side="right", padx=5)

    """追加ウィンドウを開く"""
    def open_add_window(self):
        if self.add_window is None or not self.add_window.winfo_exists():
            self.add_window = AddServerWindow(self)
        else:
            self.add_window.focus()

    """編集ウィンドウを開く"""
    def open_edit_window_by_index(self, index: int):
        profile_data = self.profiles[index]
        if self.add_window is None or not self.add_window.winfo_exists():
            # edit_index を渡してウィンドウを作成
            self.add_window = AddServerWindow(self, edit_index=index)
            self.add_window.title("サーバー編集")
            self.add_window.add_btn.configure(text="更新")
            
            # 既存データを流し込む
            self.add_window.name_entry.delete(0, "end")
            self.add_window.name_entry.insert(0, profile_data["name"])
            self.add_window.host_entry.delete(0, "end")
            self.add_window.host_entry.insert(0, profile_data["host"])
            self.add_window.port_entry.delete(0, "end")
            self.add_window.port_entry.insert(0, profile_data["port"])
            self.add_window.user_entry.delete(0, "end")
            self.add_window.user_entry.insert(0, profile_data["user"])
            self.add_window.path_entry.delete(0, "end")
            self.add_window.path_entry.insert(0, profile_data.get("path", ""))
            self.add_window.key_entry.delete(0, "end")
            self.add_window.key_entry.insert(0, profile_data["key"])
            
            self.delete_btn = ctk.CTkButton(
                self.add_window, text="削除", fg_color="red", 
                command=lambda: self.delete_profile(index, self.add_window)
            )
            self.delete_btn.pack(side="bottom", pady=10)
        else:
            self.add_window.focus()

    """プロファイルの追加"""
    def add_profile(self, data: Profile, window: AddServerWindow):
        if any(p['name'] == data['name'] for p in self.profiles):
            messagebox.showwarning("重複エラー", f"'{data['name']}' は既に存在します。", parent=window)
            return False

        self.profiles.append(data)
        self.selected_profile.set(data["name"])
        self.save_profiles()
        self.refresh_list()
        return True

    """プロファイルの更新"""
    def update_profile(self, index: int, new_data: Profile, window: AddServerWindow):
        # 名前重複チェック（自分自身以外の要素と比較）
        for i, p in enumerate(self.profiles):
            if i != index and p['name'] == new_data['name']:
                messagebox.showwarning("重複エラー", f"'{new_data['name']}' は他で使用されています。", parent=window)
                return False

        # リストの指定した番号を直接上書きする
        self.profiles[index] = new_data
        self.selected_profile.set(new_data["name"])
        self.save_profiles()
        self.refresh_list()
        return True

    """プロファイル削除"""
    def delete_profile(self, index: int, window: AddServerWindow):
        if messagebox.askyesno("削除確認", "このプロファイルを削除してもよろしいですか？", parent=window):
            self.profiles.pop(index)
            new_selection = self.profiles[0]["name"] if self.profiles else ""
            self.selected_profile.set(new_selection)
            self.save_profiles()
            self.refresh_list()
            window.destroy()

    """サーバーへ接続"""
    def connect_server(self):
        target = self.selected_profile.get()
        if not target:
            messagebox.showwarning("選択エラー", "サーバーを選択してください。", parent=self)
            return
        
        profile = next(p for p in self.profiles if p['name'] == target)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        logger.info("接続開始...")

        try:
            client.connect(
                hostname=profile['host'], port=int(profile['port']),
                username=profile['user'], key_filename=profile['key'], timeout=10
            )
            sftp = client.open_sftp()
            
            # コールバック関数を通じて SFTP と プロファイル をメインに渡す
            self.on_connect_callback(client, sftp, profile)
            
            # ランチャーを閉じる
            self.destroy()

        except Exception as e:
            error_detail = traceback.format_exc()
            logger.error("--- Detailed Error Log ---")
            logger.error(error_detail)

            messagebox.showerror("接続エラー", f"接続失敗:\n{e}", parent=self)

if __name__ == "__main__":
    # 単体で実行されたときだけ、テスト用のダミー画面を作る
    root = ctk.CTk()
    root.withdraw() # 親ウィンドウを隠す

    def test_callback(client, sftp, profile):
        print(f"テスト接続成功: {profile['name']}")

    # テスト用のコールバックを渡してランチャーを起動
    launcher = Launcher(root, test_callback)
    
    root.mainloop()