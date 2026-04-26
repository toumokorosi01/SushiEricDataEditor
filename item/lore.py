import const
import common
from typing import List, get_args, Callable
import re
import customtkinter as ctk
from tkinter import colorchooser
import data_content as dc

"""Adventureソースコードのロジックに基づくバリデーション"""
def is_valid_tag(tag_name: str) -> bool:
    # 略称の正規化マップ
    deco_map = {"b": "bold", "i": "italic", "em": "italic", "st": "strikethrough", "u": "underlined", "obf": "obfuscated"}
    
    # 1. 装飾判定（略称含む）
    clean_name = tag_name[1:] if tag_name.startswith("!") else tag_name
    if clean_name in get_args(dc.MiniMessageTag.DecorationTag) or clean_name in deco_map:
        return True
    
    # 2. 単色判定
    if common.is_color(tag_name): return True
    
    # 3. 特殊タグの分解
    parts = tag_name.split(":")
    tag_type = parts[0]

    if tag_type == "rainbow":
        if len(parts) == 1: return True
        arg = parts[1]
        phase = arg[1:] if arg.startswith("!") else arg
        return not phase or common.is_float(phase)

    if tag_type in ["gradient", "transition"]:
        if len(parts) < 2: return True
        # 最後以外は色、最後は色or数値
        for i, p in enumerate(parts[1:]):
            if i == len(parts[1:]) - 1:
                if not (common.is_color(p) or common.is_float(p)): return False
            else:
                if not common.is_color(p): return False
        return True

    if tag_type == "shadow":
        if tag_name == "!shadow": return True
        if len(parts) == 2: return common.is_color(parts[1])
        if len(parts) == 3: return common.is_color(parts[1]) and common.is_float(parts[2])
        return False

    return False

"""フラットなタグ(<bold>)を構造化辞書へ変換。略称はここで正規化する。"""
def categorize_tags(flat_tag_list: List[str]) -> dc.TagData:
    data: dc.TagData = {
        "decoration": [],
        "color": {"type": "color", "value": dc.MiniMessageTag.DEFAULT_COLOR, "args": []},
        "shadow": None
    }
    
    # 略称から正式名称への逆引き
    deco_norm = {"b": "bold", "i": "italic", "em": "italic", "st": "strikethrough", "u": "underlined", "obf": "obfuscated"}

    for full_tag in flat_tag_list:
        content = full_tag.strip("<>/")
        parts = content.split(":")
        tag_type = parts[0]

        # --- 装飾 ---
        norm_name = deco_norm.get(tag_type, tag_type)
        if norm_name in get_args(dc.MiniMessageTag.DecorationTag):
            if norm_name not in data["decoration"]:
                data["decoration"].append(norm_name)
            continue

        # --- 影 ---
        if tag_type == "shadow":
            data["shadow"] = parts[1] if len(parts) > 1 else dc.MiniMessageTag.DEFAULT_SHADOW_COLOR
            continue
        elif tag_type == "!shadow":
            data["shadow"] = None
            continue

        # --- カラー系 ---
        if tag_type in ["gradient", "transition"]:
            colors = [p for p in parts[1:] if common.is_color(p)]
            # ソース準拠: 色がない場合は白黒デフォルト
            if not colors: colors = ["white", "black"]
            data["color"] = {
                "type": tag_type,
                "value": colors,
                "args": [p for p in parts[1:] if common.is_float(p)][:1]
            }
        elif tag_type == "rainbow":
            data["color"] = {"type": "rainbow", "value": "rainbow", "args": parts[1:]}
        elif common.is_color(tag_type):
            data["color"] = {"type": "color", "value": tag_type, "args": []}

    return data

"""構造化辞書から正規化されたタグリストを生成"""
def flatten_tag_data(tag_data: dc.TagData) -> List[str]:
    result = []
    
    # 1. カラー
    c = tag_data["color"]
    if c["type"] == "color":
        result.append(f"<{c['value']}>")
    elif c["type"] == "rainbow":
        arg_str = f":{':'.join(c['args'])}" if c["args"] else ""
        result.append(f"<rainbow{arg_str}>")
    else: # gradient, transition
        vals = ":".join(c["value"]) if isinstance(c["value"], list) else c["value"]
        args = f":{':'.join(c['args'])}" if c["args"] else ""
        result.append(f"<{c['type']}:{vals}{args}>")

    # 2. 装飾 (<>を付与)
    for d in tag_data["decoration"]:
        result.append(f"<{d}>")

    # 3. 影
    if tag_data["shadow"]:
        result.append(f"<shadow:{tag_data['shadow']}>")
    
    return result

"""
MiniMessage文字列を構造化された辞書リストに変換
空文字など変換できない場合空リストを返します。
"""
def parse_strict_minimessage(raw: str) -> List[dc.MiniMessageItem]:
    if not raw:
        return []

    # タグを分離する正規表現
    pattern = r'((?<!\\)</?[^>]+>)'
    parts = re.split(pattern, raw)
    
    result = []
    active_stack = [] # <> を含まないタグ内容のリスト

    for part in parts:
        if not part: continue

        if part.startswith("<") and part.endswith(">"):
            is_closing = part.startswith("</")
            tag_content = part.strip("<>/")

            if tag_content == "reset":
                active_stack = []
                continue

            if is_valid_tag(tag_content):
                if is_closing:
                    if active_stack:
                        # 閉じタグは「ベース名」で判定 (e.g., </bold> で <bold:true> を閉じる)
                        clean_close = tag_content.split(":")[0]
                        # スタックを逆順に探して一致するものを消す（Adventureの挙動に近似）
                        for i in range(len(active_stack) - 1, -1, -1):
                            if active_stack[i].split(":")[0] == clean_close:
                                active_stack.pop(i)
                                break
                else:
                    active_stack.append(tag_content)
                continue

        # --- テキスト部分の処理 ---
        clean_text = part.replace(r"\<", "<")
        # active_stack に入っている文字列を、<> 付きのリストにして categorize_tags に渡す
        formatted_tags_dict = categorize_tags([f"<{t}>" for t in active_stack])
        
        result.append({
            "text": clean_text,
            "tags": formatted_tags_dict
        })

    return result if result else []

"""構造化された辞書リストをMiniMessage文字列に変換"""
def list_to_strict_minimessage(parsed_list: List[dc.MiniMessageItem]) -> str:
    output = ""
    for item in parsed_list:
        text = item["text"].replace("<", r"\<")

        # テキストが空なら、このセグメントのタグ生成をスキップ
        if not text:
            continue
        
        # 1. 構造化辞書を正規化されたタグリスト (<bold>, <red> 等) に変換
        flat_tags = flatten_tag_data(item["tags"])
        
        # 2. 開きタグを結合
        tags_open = "".join(flat_tags)
        
        # 3. 閉じタグを生成
        # flatten_tag_data が返すのはフルネームなので、略称を気にする必要なし
        close_tags = ""
        for t in reversed(flat_tags):
            base_name = t.strip("<>/").split(":")[0]
            close_tags += f"</{base_name}>"
        
        output += f"{tags_open}{text}{close_tags}"
    return output

"""データ新規作成"""
def create_empty_minimessage_data(text: str = "") -> dc.MiniMessageItem:
    return {
        "text": text,
        "tags": {
            "decoration": [],
            "color": {"type": "color", "value": "white", "args": []},
            "shadow": None
        }
    }

"""
カラーピッカーを開き、選択された色（またはデフォルト値）を返す
"""
def get_new_color(initial_color="#FFFFFF"):
    # カラーピッカーを表示
    # color_code は ((R, G, B), "#hex") のタプルが返る
    color_code = colorchooser.askcolor(initialcolor=initial_color, title="色を選択")

    # ユーザーが色を選択したかチェック
    if color_code[1] is not None:
        return color_code[1]  # 選択された "#RRGGBB" を返す
    else:
        return "#FFFFFF"      # キャンセルされた場合は白を返す
    
"""MiniMessageのデータとGUIの編集用関数をまとめたクラス"""
class EditMiniMessage:
    def __init__(self, data: dc.MiniMessageItem, callback: Callable[[], None]):
        # インスタンス変数として保存
        self.data = data
        self.callback = callback

    """
    テキストの変更
    :param text: 新しい文字列
    """
    def change_text(self, text: str):
        self.data["text"] = text
        self.callback()

    """
    decorationタグの変更
    :param tag: const.const.MiniMessageTag.DecorationTag
    :param stats: Trueで有効化、Falseで無効化
    """
    def change_deco_tag(self, tag: dc.MiniMessageTag.DecorationTag, stats: bool):
        deco_data = self.data["tags"]["decoration"]

        if stats:
            if tag not in deco_data:
                deco_data.append(tag)
        else:
            # 存在するときだけ消す（エラー防止）
            if tag in deco_data:
                deco_data.remove(tag)  

        self.callback()

    """
    影の切り替え。トグルで呼び出す
    :param is_shadow: Trueで有効化、Falseで無効化
    :param menu: 表示・非表示をしたいctk.CTkOptionMenu
    """
    def change_shadow(self, is_shadow: bool, menu: ctk.CTkOptionMenu):
        tag_data = self.data["tags"]

        # 一旦全部剥がして順序をリセット
        menu.grid_forget()

        if is_shadow:
            menu.pack(pady=(3, 0))
            menu.set("black")
            tag_data["shadow"] = "black"
        else:
            tag_data["shadow"] = None

        self.callback()

    """
    オプションメニューの切り替えで呼び出す。
    ・color
    ・shadow
    ・gradient
    ・transition
    の色指定で使用。
    :param mode: 変更したい色のconst.const.MiniMessageTag.ColorTagType。
    :param color: 変更後の色。'hexcode'かconst.const.MiniMessageTag.ColorNameで指定。
    :param index: 色がリストで保存される形式の場合、リストのインデックスを指定。デフォルト値は0。
    """
    def change_color(self, mode: dc.MiniMessageTag.ColorTagType, color: str, index: int = 0):
        is_hex = color == "hexcode"
        tag_data = self.data["tags"]
        color_data = tag_data["color"]

        match mode:
            case "color":
                if is_hex:
                    color_data["value"] = get_new_color()
                else:
                    color_data["value"] = color
            case "shadow":
                if is_hex:
                    tag_data["shadow"] = get_new_color()
                else:
                    tag_data["shadow"] = color
            case "gradient" | "transition":
                if is_hex:
                    color_data["value"][index] = get_new_color()
                else:
                    color_data["value"][index] = color

        self.callback()

DECORATIONS = {
    "太字": "bold",
    "斜体": "italic",
    "下線": "underlined",
    "取り消し線": "strikethrough",
    "難読化": "obfuscated"
}

"""loreのsectionのフレームの作成"""
class LoreSection(ctk.CTkFrame):
    def __init__(
            self, 
            master: ctk.CTkScrollableFrame, 
            section_data: dc.MiniMessageItem, 
            on_update: Callable[[], None], 
            create_callback: Callable[[ctk.CTkFrame, int], None], 
            delete_callback: Callable[[ctk.CTkFrame], None], 
            move_callback: Callable[[ctk.CTkFrame, int], None], 
            **kwargs
    ):
        # master は LoreLine(self) 
        super().__init__(master, fg_color="transparent", border_width=1, border_color=const.line_color, corner_radius=0, width=200, **kwargs)
        
        # このセクションが担当する1つの MiniMessageItem
        self.section_data = section_data
        self.on_update = on_update
        self.create_callback = create_callback
        self.delete_callback = delete_callback
        self.move_callback = move_callback
        
        # GUIパーツの構築
        self.setup_widgets()

    def setup_widgets(self):
        # 例: タグ編集用の入力欄やテキストラベルなど
        data_edit_tool = EditMiniMessage(self.section_data, self.on_update)

        # タグのデータ
        tag_data = self.section_data["tags"]
            
        # 入力欄、×ボタン
        frame_1 = ctk.CTkFrame(self, fg_color="transparent")
        frame_1.grid(row=0, sticky="nsew", pady=(1, 0), padx=1)

        # デコレーションの操作
        frame_2 = ctk.CTkFrame(self, fg_color="transparent")
        frame_2.grid(row=1, sticky="nsew", padx=1)
            
        # データの移動や追加のボタン
        frame_3 = ctk.CTkFrame(self, fg_color="transparent")
        frame_3.grid(row=2, sticky="nsew", pady=(0, 1), padx=1)

        # ============ 表示名・削除ボタン ============
        # 入力欄の設定
        name_var = ctk.StringVar(value=self.section_data.get("text", ""))
        name_var.trace_add("write", lambda *_: data_edit_tool.change_text(name_var.get()))
        # 入力欄
        entry = ctk.CTkEntry(frame_1, textvariable=name_var, width=180, font=const.UI_FONT)
        entry.grid(row=0, column=0, pady=5, padx=10)

        # 削除ボタン
        ctk.CTkButton(frame_1, text="✕", fg_color="red", command=lambda: self.delete_callback(self), width=28).grid(row=0, column=1, pady=5, padx=10)

        # ============ デコレーションと色操作 ============
        # デコレーションのフレーム
        deco_frame = ctk.CTkFrame(frame_2, fg_color="transparent")
        deco_frame.grid(row=0, column=0, sticky="nsew")

        # カラーのフレーム
        color_frame = ctk.CTkFrame(frame_2, fg_color="transparent")
        color_frame.grid(row=0, column=1, sticky="nsew")

        # デコレーション
        for deco_idx, (display, tag) in enumerate(DECORATIONS.items()):
            is_on = tag in tag_data["decoration"]
            switch_var = ctk.BooleanVar(value=is_on)

            switch = ctk.CTkSwitch(
                deco_frame,
                text=display,
                variable=switch_var,
                command=lambda t=tag, v=switch_var: data_edit_tool.change_deco_tag(t, v.get())
            )
            switch.grid(row=deco_idx, sticky="w", padx=10)

        # 影
        shadow_frame = ctk.CTkFrame(color_frame, fg_color="transparent")
        shadow_frame.grid(row=0)
        
        # OptionMenu (値が変わった時に change_color を呼ぶ)
        # color は OptionMenu から自動で渡される選択文字列
        # この時点ではまだ置かない
        shadow_option = ctk.CTkOptionMenu(
            shadow_frame,
            values=dc.MiniMessageTag.COLORS + ["hexcode"],
            width=100,
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

        # ============ 作成・移動 ============
        ctk.CTkButton(frame_3, text="◀", command=lambda: self.move_callback(self, -1), width=35).pack(side="left", expand=True, padx=2, pady=3)
        ctk.CTkButton(frame_3, text="▶", command=lambda: self.move_callback(self, 1), width=35).pack(side="left", expand=True, padx=2, pady=3)
        ctk.CTkButton(frame_3, text="前に追加", fg_color="green", command=lambda: self.create_callback(self, -1), width=80).pack(side="left", expand=True, padx=2, pady=3)
        ctk.CTkButton(frame_3, text="後ろに追加", fg_color="green", command=lambda: self.create_callback(self, 1), width=80).pack(side="left", expand=True, padx=2, pady=3)



"""LoreのLineのフレーム作成"""
class LoreLine(ctk.CTkFrame):
    def __init__(
            self, 
            master: ctk.CTkScrollableFrame, 
            line_data: List[dc.MiniMessageItem], 
            on_update: Callable[[], None], 
            create_callback: Callable[[ctk.CTkFrame, int], None], 
            delete_callback: Callable[[ctk.CTkFrame], None], 
            move_callback: Callable[[ctk.CTkFrame, int], None], 
            **kwargs
    ):
        # master は親である Lore クラスのインスタンス（またはその中のコンテナ）になります
        super().__init__(master, fg_color="transparent", border_width=1, border_color="cyan", corner_radius=0, **kwargs, width=570, height=220)
        
        self.grid_propagate(False)
        self.pack_propagate(False)

        # List[MiniMessageItem]
        self.line_data = line_data  
        # サイドバーとヘッダーのの表示更新関数
        self.on_update = on_update
        # このラインのフレームのリスト
        self.frame_list: List[ctk.CTkFrame] = []

        self.create_callback = create_callback
        self.delete_callback = delete_callback
        self.move_callback = move_callback

        self.setup_widgets()

    """
    セクションの作成
    :parm direction: -1(上)/1(下)
    """
    def section_create(self, section_instance: ctk.CTkFrame, direction: int):
        # リアルタイムで「自分がいま何番目か」をリストから検索する
        base_idx = self.frame_list.index(section_instance)
        insert_idx = base_idx + direction
        insert_idx = max(0, min(insert_idx, len(self.frame_list)))
        
        # 空のデータを作る(まだ作っただけで入れてない)
        new_data = create_empty_minimessage_data()
        # 指定のindexに挿入
        self.line_data.insert(insert_idx, new_data)

        new_frame = LoreSection(self.scrollable_frame, new_data, self.on_update, self.section_create, self.section_delete, self.section_move)
        self.frame_list.insert(insert_idx, new_frame)

        # 再配置
        for i, frame in enumerate(self.frame_list):
            frame.grid(row=0, column=i, pady=2, padx=3)

        self.on_update()

    """セクションの削除"""
    def section_delete(self, section_instance: ctk.CTkFrame):
        if len(self.line_data) <= 1:
            return

        idx = self.frame_list.index(section_instance)

        self.line_data.pop(idx)
        target_frame = self.frame_list.pop(idx)
        target_frame.destroy()

        for i, frame in enumerate(self.frame_list):
            frame.grid(row=0, column=i, pady=2, padx=3)

        self.on_update()

    """
    セクションの移動
    :parm direction: -1(上)/1(下)
    """
    def section_move(self, section_instance: ctk.CTkFrame, direction: int):
        if direction == 0:
            return
        old_idx = self.frame_list.index(section_instance)
        new_idx = old_idx + direction
        new_idx = max(0, min(new_idx, len(self.frame_list)))

        if 0 <= new_idx < len(self.frame_list):
            # 要素を入れ替える(データ)
            self.line_data[old_idx], self.line_data[new_idx] = \
                self.line_data[new_idx], self.line_data[old_idx]
            # 要素を入れ替える(フレーム)
            self.frame_list[old_idx], self.frame_list[new_idx] = \
                self.frame_list[new_idx], self.frame_list[old_idx]
            
            # grid再設定
            for i, frame in enumerate(self.frame_list):
                frame.grid(row=0, column=i, pady=2, padx=3)

            self.on_update()

    def setup_widgets(self):
        # ここでラベルやボタンなどを配置
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self, 
            orientation="horizontal",
            fg_color="transparent",
            corner_radius=0
        )
        self.grid_columnconfigure(0, weight=1)

        self.scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=(1, 0), pady=1)

        control_frame = ctk.CTkFrame(self, width=100, fg_color="transparent", corner_radius=0)
        control_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 1), pady=1)
        
        ctk.CTkButton(control_frame, text="▲", command=lambda: self.move_callback(self, -1), width=90).pack(expand=True, padx=2, pady=3)
        ctk.CTkButton(control_frame, text="▼", command=lambda: self.move_callback(self, 1), width=90).pack(expand=True, padx=2, pady=3)
        ctk.CTkButton(control_frame, text="前に追加", fg_color="green", command=lambda: self.create_callback(self, -1), width=90).pack(expand=True, padx=2, pady=3)
        ctk.CTkButton(control_frame, text="後ろに追加", fg_color="green", command=lambda: self.create_callback(self, 1), width=90).pack(expand=True, padx=2, pady=3)

        for i, item in enumerate(self.line_data):
            section = LoreSection(self.scrollable_frame, item, self.on_update, self.section_create, self.section_delete, self.section_move)
            self.frame_list.append(section)
            section.grid(row=0, column=i, pady=2, padx=3)
            

