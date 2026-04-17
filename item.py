import customtkinter as ctk
import const
import logging

ITEM_KEYS = const.ItemData()

# レコーダー作成
logger = logging.getLogger(__name__)

class ItemView(ctk.CTkFrame):
    def __init__(
            self, 
            master, 
            sftp, 
            profile, 
            data, 
            old_data, 
            update_callback, 
            category,
            last_selection_ref
    ):
        super().__init__(master, fg_color="transparent")
        self.sftp = sftp # 接続済みインスタンス
        self.profile = profile # パスなどの情報
        self.all_data = data # このタブで使う現在の編集データ
        self.old_all_data = old_data # このタブで使う保存済みデータ
        self.update_callback = update_callback # 親への更新通知
        self.category = category # 自分の名前
        self.last_selection_ref = last_selection_ref # 最後に選択したデータの辞書

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.setup_widgets()
        self.refresh_data(True)

    """サイドバーとメインフレームを作成する"""
    def setup_widgets(self):
        # サイドバー
        self.sidebar_frame = ctk.CTkScrollableFrame(
            self, width=200, corner_radius=0, fg_color=const.bottom_side_color
        )
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")

        # メイン編集エリア
        self.main_frame = ctk.CTkFrame(self, fg_color=const.bottom_main_color, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")

    """辞書の内容を元にサイドバーのボタンを並べる"""
    def refresh_data(self, auto_select: bool=False):
        for widget in self.sidebar_frame.winfo_children():
            widget.destroy()

        # 新規作成ボタン
        new_btn = ctk.CTkButton(self.sidebar_frame, text="+ 新規作成", fg_color="blue", command=self.data_create)
        new_btn.pack(pady=10, padx=10, fill="x")

        if not self.all_data:
            return

        for item_id in self.all_data.keys():
            btn = ctk.CTkButton(
                self.sidebar_frame, text=item_id, 
                fg_color=const.bottom_side_color, hover_color=const.bottom_side_hover_color,
                command=lambda i=item_id: self.select_data(i)
            )
            btn.pack(fill="x")

        if auto_select:
            # 並べた後、前回選択したものを開く、データがないまたは不正なら一番上
            last_selected = self.last_selection_ref[self.category]
            if last_selected in self.all_data.keys():
                self.select_data(last_selected)
            else:
                id = next(iter(self.all_data))
                self.select_data(id)

    """特定のIDを選択状態にする"""
    def select_data(self, item_id: str):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # すべてのボタンの中から対象を探して色を変える
        for widget in self.sidebar_frame.winfo_children():
            if isinstance(widget, ctk.CTkButton):
                # 「+ 新規作成」ボタンは除外する
                if widget.cget("text") == "+ 新規作成":
                    continue
                
                # IDが一致したボタンを gray に、それ以外を control に
                if widget.cget("text") == item_id:
                    widget.configure(fg_color=const.bottom_side_hover_color)
                    self.selected_button = widget # 保持しておく
                else:
                    widget.configure(fg_color=const.bottom_side_color)
        
        # 最終選択の辞書更新
        self.last_selection_ref[self.category] = item_id

        # --- メイン画面表示 ---
        item_dict = self.all_data.get(item_id, {})

        # 表示名
        # 外側の枠線用フレーム
        display_name_base_frame = ctk.CTkFrame(
            master=self.main_frame,
            fg_color="transparent",
            border_color=const.line_color,
            border_width=1,
            width=200, 
            height=100,
            corner_radius=0
        )
        display_name_base_frame.grid(row=0, column=0, padx=10, pady=10)

        # 2. 内側のスクロールフレーム（線なし・背景透過）
        self.display_name_frame = ctk.CTkScrollableFrame(
            master=display_name_base_frame,    # 親をbase_frameにする
            fg_color="transparent",
            border_width=0,                    # 線なし
            orientation="horizontal",
            corner_radius=0
        )
        # 外枠いっぱいに広げる（padx, padyを1〜2にするとバーが枠に重ならない）
        self.display_name_frame.pack(expand=True, fill="both", padx=1, pady=1)
        
        name_var = ctk.StringVar(value=item_dict.get("display_name", ""))

        def update_name(*args):
            item_dict["display_name"] = name_var.get()
            self.update_callback()

        name_var.trace_add("write", update_name)

        ctk.CTkLabel(self.display_name_frame, text="表示名:", font=const.UI_FONT).grid(row=0, column=0, pady=5, padx=10)

        self.display_name_entry = ctk.CTkEntry(
            self.display_name_frame, 
            placeholder_text="表示名を入力",
            textvariable=name_var,
            width=200,
            font=const.UI_FONT
        )
        self.display_name_entry.grid(row=0, column=1, pady=5, padx=(0, 10))

        logger.info(f"選択中: {item_id}")
    
    def data_create(self):
        # 1. サブウィンドウの設定
        dialog = ctk.CTkToplevel(self)
        dialog.title("新規IDの追加")
        dialog.geometry("300x200")
        dialog.attributes("-topmost", True) # 常に最前面
        dialog.grab_set() # この窓を閉じるまで親を操作不可にする

        # 中央に配置するための調整
        dialog.grid_columnconfigure(0, weight=1)

        label = ctk.CTkLabel(dialog, text="新しいIDを入力してください:")
        label.grid(row=0, column=0, pady=(20, 5))

        entry = ctk.CTkEntry(dialog, width=200)
        entry.grid(row=1, column=0, pady=5)
        entry.focus() # 最初から入力できる状態にする

        # エラー表示用ラベル
        error_label = ctk.CTkLabel(dialog, text="", text_color="red", font=("", 11))
        error_label.grid(row=2, column=0)

        # ボタン配置用のフレーム
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.grid(row=3, column=0, pady=10)

        def add_id():
            new_id = entry.get().strip()
            
            if not new_id:
                error_label.configure(text="IDを入力してください")
                return
            
            if new_id in self.all_data:
                error_label.configure(text="そのIDは既に存在します")
                return

            # データの追加と更新
            self.all_data[new_id] = {}
            dialog.destroy() # 窓を閉じる
            self.refresh_data() # 画面を再構築してボタンを増やす
            self.update_callback()
            self.select_data(new_id)

        add_btn = ctk.CTkButton(btn_frame, text="追加", width=80, command=add_id)
        add_btn.pack(side="left", padx=5)

        cancel_btn = ctk.CTkButton(btn_frame, text="キャンセル", width=80, 
                                  fg_color="gray", command=dialog.destroy)
        cancel_btn.pack(side="left", padx=5)

        # Enterキーでも追加できるようにする
        entry.bind("<Return>", lambda e: add_id())

    def data_verification(self, id: str, key: str):
        return_data = []

        if id not in self.all_data:
            warn = f"{id} が辞書にありません"
            logger.error(warn)
            return_data.append((False, warn))

            return return_data
        
        data = self.all_data[id]

        # 表示名
        display_name = data.get(ITEM_KEYS.display)
        if not display_name:
            warn = "表示名が空です。"
            logger.warning(warn)
            return_data.append((False, warn))




        
        lore_list = data.get(ITEM_KEYS.lore, [])

        if not return_data:
            return [(True, "")]
        else:
            return return_data
        
        

