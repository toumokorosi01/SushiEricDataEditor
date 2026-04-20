import customtkinter as ctk
import const, common
from typing import Callable

DECORATIONS = {
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
        self.building_frame()
        
    """フレームの構築"""
    def building_frame(self):
        """データの新規作成"""
        def data_create(index: int):
            # 空のデータを作る(まだ作っただけで入れてない)
            data = common.create_empty_minimessage_data()

            # 指定のindexに挿入
            self.name_data.insert(index, data)

            # 追加したい位置以下のフレームを下にずらす
            for i in range(len(section_frame_list) - 1, index - 1, -1):
                section_frame_list[i].grid(row=i + 1, pady=5, padx=10)
            
            # フレームを作成、表示
            new_frame = create_edit_frame(data)
            section_frame_list.insert(index, new_frame)

            new_frame.grid(row=index, pady=5, padx=10)

            self.scroll_frame.update_idletasks()
            self.on_update()

        """データの入れ替え"""
        def data_move(old_index: int, new_index: int):
            # インデックスが両方とも有効範囲内かチェック
            if not (0 <= old_index < len(self.name_data) and 0 <= new_index < len(self.name_data)):
                return

            # 要素を入れ替える(データ)
            self.name_data[old_index], self.name_data[new_index] = \
                self.name_data[new_index], self.name_data[old_index]

            # 要素を入れ替える(フレーム)
            section_frame_list[old_index], section_frame_list[new_index] = \
                section_frame_list[new_index], section_frame_list[old_index]

            # grid再設定
            for i, frame in enumerate(section_frame_list):
                frame.grid(row=i, pady=5, padx=10)

            self.scroll_frame.update_idletasks()
            self.on_update()

        """データの削除"""
        def data_delete(index: int):
            if len(self.name_data) > 1:
                # データ削除
                self.name_data.pop(index)
                # フレームをリストから取り出す(削除)
                target_frame = section_frame_list.pop(index)
                # フレームを破壊
                target_frame.destroy()

                # 詰めなおし
                for i, frame in enumerate(section_frame_list):
                    frame.grid(row=i, pady=5, padx=10)

                self.scroll_frame.update_idletasks()
                self.on_update()

        # 一旦クリア
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        """編集フレームを作成"""
        def create_edit_frame(data: const.MiniMessageItem):

            data_edit_tool = common.EditMiniMessage(data, self.on_update)

            # タグのデータ
            tag_data = data["tags"]

            # 親フレーム(追加ボタンや入力欄のまとまり)
            parent_frame = ctk.CTkFrame(self.scroll_frame, width=200)

            # 補助関数：自分が今何番目かを取得
            def get_my_idx():
                return section_frame_list.index(parent_frame)

            # decorationやtextの操作用フレーム
            main_frame = ctk.CTkFrame(parent_frame)
            main_frame.grid(row=0, column=0, sticky="nsew")

            # ============ 表示文字列入力欄 ============
            # メインの入力欄フレーム
            entry_frame = ctk.CTkFrame(main_frame, width=200)
            entry_frame.grid(row=0, sticky="nsew")

            # 入力欄の設定
            name_var = ctk.StringVar(value=data.get("text", ""))
            name_var.trace_add("write", lambda *_: data_edit_tool.change_text(name_var.get()))

            # 入力欄
            entry = ctk.CTkEntry(entry_frame, textvariable=name_var, width=200, font=const.UI_FONT)
            entry.grid(row=0, column=0, pady=5, padx=10)
            # ====================================

            # decorationやcolorのボタン配置用フレーム
            btn_frame = ctk.CTkFrame(main_frame, width=100)
            btn_frame.grid(row=1, sticky="nsew")

            # ============ decorationのトグル ============
            for deco_idx, (display, tag) in enumerate(DECORATIONS.items()):
                is_on = tag in tag_data["decoration"]
                switch_var = ctk.BooleanVar(value=is_on)

                switch = ctk.CTkSwitch(
                    btn_frame,
                    text=display,
                    variable=switch_var,
                    command=lambda t=tag, v=switch_var: data_edit_tool.change_deco_tag(t, v.get())
                )
                switch.grid(row=deco_idx, column=0, sticky="w", padx=10)
            # ====================================
            
            # ============ 影の操作 ============
            # フレームの作成
            shadow_frame = ctk.CTkFrame(btn_frame, fg_color="transparent")
            shadow_frame.grid(row=0, column=1)
        
            # OptionMenu (値が変わった時に change_color を呼ぶ)
            # color は OptionMenu から自動で渡される選択文字列
            # この時点ではまだ置かない
            shadow_option = ctk.CTkOptionMenu(
                shadow_frame,
                values=const.MiniMessageTag.COLORS + ["hexcode"],
                command=lambda color: data_edit_tool.change_color("shadow", color)
            )
        
            # スイッチ (ON/OFF時に change_shadow を呼ぶ)
            # NoneならFalse
            is_shadow = bool(tag_data.get("shadow"))
            shadow_switch_var = ctk.BooleanVar(value=is_shadow)
            
            shadow_switch = ctk.CTkSwitch(
                shadow_frame, 
                text="影", 
                variable=shadow_switch_var,
                command=lambda: data_edit_tool.change_shadow(shadow_switch_var.get(), shadow_option)
            )
            shadow_switch.pack(pady=(3, 0))

            # データが入っていれば表示
            if is_shadow:
                shadow_option.pack(pady=(3, 0))
                shadow_option.set(tag_data.get("shadow"))

            # ====================================

            # 新規作成やデータの移動などの操作用フレーム
            control_frame = ctk.CTkFrame(parent_frame)
            control_frame.grid(row=0, column=1, sticky="nsew")

            # 操作用フレームのボタン
            ctk.CTkButton(control_frame, text="前に追加", fg_color="green", command=lambda: data_create(get_my_idx()), width=100).pack(pady=(3, 0))
            ctk.CTkButton(control_frame, text="後ろに追加", fg_color="green", command=lambda: data_create(get_my_idx() + 1), width=100).pack(pady=(3, 0))
            ctk.CTkButton(control_frame, text="▲", command=lambda: data_move(get_my_idx(), get_my_idx() - 1), width=100).pack(pady=(3, 0))
            ctk.CTkButton(control_frame, text="▼", command=lambda: data_move(get_my_idx(), get_my_idx() + 1), width=100).pack(pady=(3, 0))
            ctk.CTkButton(control_frame, text="削除", fg_color="red", command=lambda: data_delete(get_my_idx()), width=100).pack(pady=(3, 0))

            return parent_frame

        section_frame_list: list[ctk.CTkFrame] = []

        for section_idx, data in enumerate(self.name_data):
            # 作成
            frame = create_edit_frame(data)
            # リストに追加
            section_frame_list.append(frame)
            # 表示
            frame.grid(row=section_idx, pady=5, padx=10)
            
