import customtkinter as ctk
import const, common

decorations = {
    "太字": "bold",
    "斜体": "italic",
    "下線": "underlined",
    "取り消し線": "strikethrough",
    "難読化": "obfuscated"
}

class DisplayName(ctk.CTkFrame):
    def __init__(self, master, item_dict, update_callback, update_sidebar_callback, **kwargs):
        # 外側の枠線設定を引き継ぐ
        super().__init__(
            master, 
            fg_color="transparent", 
            border_color=const.line_color, 
            border_width=1, 
            corner_radius=0,
            **kwargs
        )

        self.is_initializing = True  # 初期化フラグを立てる

        self.item_dict = item_dict
        self.update_callback = update_callback
        self.update_sidebar_callback = update_sidebar_callback

        # 伝播を無効化（サイズ固定のため）
        self.grid_propagate(False)
        self.pack_propagate(False)

        self.name_data = common.parse_strict_minimessage(self.item_dict.get(const.ItemData.display, ""))

        self.setup_widgets()
        self.is_initializing = False # 初期化完了

    """親の辞書を書き換えてサイドバーとヘッダーを更新する"""
    def on_update(self):
        self.item_dict[const.ItemData.display] = common.list_to_strict_minimessage(self.name_data)

        if getattr(self, "is_initializing", False):
            return

        self.update_callback()
        self.update_sidebar_callback()

    """表示名のベースのフレーム"""
    def setup_widgets(self):
        label = ctk.CTkLabel(self, text="表示名", font=const.UI_FONT)
        label.pack(pady=3) 

        # スクロールエリア
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", border_width=0, corner_radius=0)
        self.scroll_frame.pack(expand=True, fill="both", padx=(1, 1), pady=(2, 1))

        # データを読み込んで配置
        self.refresh_frame()
        
    """フレームの構築"""
    def building_frame(self):
        """テキストの変更"""
        def change_text(index: int, text: str):
            self.name_data[index]["text"] = text

        """decorationタグの変更"""
        def change_deco_tag(index: int, tag: str, stats: bool):
            target = f"<{tag}>"
            if stats:
                if target not in self.name_data[index]["tags"]["decoration"]:
                    self.name_data[index]["tags"]["decoration"].append(target)
            else:
                # 存在するときだけ消す（エラー防止）
                if target in self.name_data[index]["tags"]["decoration"]:
                    self.name_data[index]["tags"]["decoration"].remove(target)

        """影の切り替え"""
        def change_shadow(index: int, is_shadow: bool):
            tag_data = self.name_data[index]["tags"]

            # 一旦全部剥がして順序をリセット
            self.shadow_option.pack_forget()

            if is_shadow:
                self.shadow_option.pack(pady=(3, 0))
                self.shadow_option.set("black")
                tag_data["shadow"] = "black"
            else:
                tag_data["shadow"] = None

        """オプションメニューの切り替えで呼び出す"""
        def change_color(
                mode: str, 
                tag_data: const.TagData, 
                color: str, 
                index: int = 0
        ):
            is_not_hex = color in const.MiniMessageTag.COLORS
            color_data = tag_data["color"]



            match mode:
                case "shadow":
                    if is_not_hex:
                        tag_data["shadow"] = color
                    else:
                        tag_data["shadow"] = common.get_new_color()
                case "color":
                    if is_not_hex:
                        tag_data["color"]["value"] = color
                    else:
                        tag_data["color"]["value"] = common.get_new_color()
                case "gradient" | "transition":
                    if is_not_hex:
                        tag_data["color"]["value"][index] = color
                    else:
                        tag_data["color"]["value"][index] = common.get_new_color()



            type = color_data["type"]
            value = color_data["value"]
            args = color_data["args"]

            match mode:
                case "color":


        """オプションメニューで呼び出す関数"""
        def shadow_frame_edit(color: str, index: int):
            tag_data = self.name_data[index]["tags"]

            if color in const.MiniMessageTag.COLORS:
                self.shadow_btn.pack_forget()
                tag_data["shadow"] = color
            else:
                # "hexcode" が選ばれた場合
                self.shadow_btn.pack(pady=(3, 0))
                # 文字列 "hexcode" をデータに入れないよう、
                # 現在の値が妥当な色なら維持、そうでなければ白にする
                if not common.is_color(tag_data.get("shadow")):
                    tag_data["shadow"] = "#FFFFFF"

            self.on_update(re_render=False)

        """
        引数に応じた色変更処理
        :param color_deco: tags['color'] または tags（shadow用）の辞書
        :param mode: "color", "gradient", "transition", "shadow" のいずれか
        :param index: リスト形式（gradient/transition）の場合の書き換え位置
        """
        def change_color_interactive(color_deco: dict, mode: str, index: int = 0, current_color: str= "#FFFFFF"):
            # 1. 現在の値をカラーピッカーの初期値として取得
            current_hex = current_color if common.is_color(current_color) else "#FFFFFF"

            if mode == "shadow":
                current_hex = color_deco.get("shadow") or "#FFFFFF"
            else:
                # color / gradient / transition の場合
                val = color_deco.get("value", "#FFFFFF")
                if isinstance(val, list):
                    # リストなら指定されたインデックスの色、なければ白
                    current_hex = val[index] if index < len(val) else "#FFFFFF"
                else:
                    current_hex = val

            # 2. カラーピッカーを開く
            new_color = common.get_new_color(current_hex)

            # 3. 分岐処理
            match mode:
                case "color":
                    color_deco["type"] = "color"
                    color_deco["value"] = new_color
                    color_deco["args"] = []

                case "gradient" | "transition":
                    color_deco["type"] = mode
                    # valueが文字列（単色）だった場合に備えてリスト化を保証
                    if not isinstance(color_deco["value"], list):
                        color_deco["value"] = [color_deco["value"]]

                    # 指定されたインデックスを上書き
                    if index < len(color_deco["value"]):
                        color_deco["value"][index] = new_color
                    else:
                        color_deco["value"].append(new_color)

                case "shadow":
                    # shadowの場合は tags 直下を書き換える想定
                    color_deco["shadow"] = new_color

            self.on_update(re_render=False)

        """データの新規作成"""
        def data_create(index: int):
            data = common.create_empty_minimessage_data()

            self.name_data.insert(index, data)
            self.on_update()

        """データの削除"""
        def data_delete(index: int):
            if len(self.name_data) > 1:
                self.name_data.pop(index)
                self.on_update()

        """データの入れ替え"""
        def data_move(old_index: int, new_index: int):
            # インデックスが両方とも有効範囲内かチェック
            if not (0 <= old_index < len(self.name_data) and 0 <= new_index < len(self.name_data)):
                return

            # 要素を入れ替える
            self.name_data[old_index], self.name_data[new_index] = \
                self.name_data[new_index], self.name_data[old_index]

            # データを反映
            self.on_update()

        # 一旦クリア
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        # name_dataはparse_strict_minimessageが初期値を返すので空にはならない
        for section_idx, data in enumerate(self.name_data):

            tag_data = data["tags"]

            # 親フレーム(追加ボタンや入力欄のまとまり)
            parent_frame = ctk.CTkFrame(self.scroll_frame, width=200)
            parent_frame.pack(pady=5, padx=10)

            # メインとコントロール
            main_frame = ctk.CTkFrame(parent_frame)
            main_frame.grid(row=0, column=0, sticky="nsew")
            control_frame = ctk.CTkFrame(parent_frame)
            control_frame.grid(row=0, column=1, sticky="nsew")

            # コントロールのボタン
            ctk.CTkButton(control_frame, text="前に追加", fg_color="green", command=lambda idx=section_idx: data_create(idx), width=100).pack(pady=(3, 0))
            ctk.CTkButton(control_frame, text="後ろに追加", fg_color="green", command=lambda idx=section_idx: data_create(idx + 1), width=100).pack(pady=(3, 0))
            ctk.CTkButton(control_frame, text="▲", command=lambda idx=section_idx: data_move(idx, idx - 1), width=100).pack(pady=(3, 0))
            ctk.CTkButton(control_frame, text="▼", command=lambda idx=section_idx: data_move(idx, idx + 1), width=100).pack(pady=(3, 0))
            ctk.CTkButton(control_frame, text="削除", fg_color="red", command=lambda idx=section_idx: data_delete(idx), width=100).pack(pady=(3, 0))

            # メインの入力欄フレーム
            entry_frame = ctk.CTkFrame(main_frame, width=200)
            entry_frame.grid(row=0, sticky="nsew")

            # 入力欄の設定
            name_var = ctk.StringVar(value=data.get("text", ""))
            name_var.trace_add("write", lambda *a, idx=section_idx, var=name_var: change_text(idx, var.get()))

            # 入力欄
            entry = ctk.CTkEntry(entry_frame, textvariable=name_var, width=200, font=const.UI_FONT)
            entry.grid(row=0, column=0, pady=5, padx=10)

            # --------------------------------

            # メインのボタンフレーム
            btn_frame = ctk.CTkFrame(main_frame, width=100)
            btn_frame.grid(row=1, sticky="nsew")

            # タグの操作スイッチ
            for deco_idx, (display, tag) in enumerate(decorations.items()):
                row = deco_idx
                tag_str = f"<{tag}>"
                is_on = tag_str in tag_data["decoration"]
                switch_var = ctk.BooleanVar(value=is_on)

                switch = ctk.CTkSwitch(
                    btn_frame,
                    text=display,
                    variable=switch_var,
                    command=lambda idx=section_idx, t=tag, v=switch_var: change_deco_tag(idx, t, v.get())
                )
                switch.grid(row=row, column=0, sticky="w", padx=10)

            # ------ 色操作 ------

            # 影フレームの作成
            self.shadow_frame = ctk.CTkFrame(btn_frame)
            self.shadow_frame.grid(row=0, column=1)
        
            # 1. OptionMenu (値が変わった時に shadow_frame_edit を呼ぶ)
            # val は OptionMenu から自動で渡される選択文字列
            self.shadow_option = ctk.CTkOptionMenu(
                self.shadow_frame,
                values=const.MiniMessageTag.COLORS + ["hexcode"],
                command=lambda val, idx=section_idx: shadow_frame_edit(val, idx)
            )
        
            # 2. カラーピッカーボタン (クリック時に change_color_interactive を呼ぶ)
            self.shadow_btn = ctk.CTkButton(
                self.shadow_frame, 
                text="色を設定", 
                width=50,
                command=lambda idx=section_idx: change_color_interactive(
                    self.name_data[idx]["tags"], 
                    "shadow"
                )
            )
        
            # 3. 影スイッチ (ON/OFF時に change_shadow を呼ぶ)
            is_shadow = bool(tag_data.get("shadow"))
            shadow_switch_var = ctk.BooleanVar(value=is_shadow)
            
            shadow_switch = ctk.CTkSwitch(
                self.shadow_frame, 
                text="影", 
                variable=shadow_switch_var,
                # スイッチの状態 (True/False) を渡す
                command=lambda idx=section_idx, var=shadow_switch_var: change_shadow(
                    idx, 
                    var.get()
                )
            )
            shadow_switch.pack(pady=(3, 0))
        
            # 初回のUI状態を反映（現在影ありならメニューを表示するなど）
            change_shadow(section_idx, is_shadow)
            


            # 影以外の色操作
            # self.color_data = common.get_color_info_dict(current_tags) # {"type": "color", "value": "white", "args": []}
            # color_type = self.color_data["type"]
# 
            # color_type_menu = ctk.CTkOptionMenu(
            #     btn_frame,
            #     values=const.MiniMessageTag.color_options,
            #     command=color_contorol # 自動で引数は渡される
            # )
            # color_type_menu.grid(row=1, column=1, pady=3)
            # color_type_menu.set(color_type)
            # color_contorol(color_type)
            