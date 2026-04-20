import os, re
import const
from typing import List, get_args, Callable
from tkinter import colorchooser
import customtkinter as ctk

"""OSに応じたデータ保存フォルダのベースパスを返す"""
def get_base_data_folder():
    if const.IS_MAC:  # macOS
        # ~/Library/Application Support/SushiEricDataEditor
        base = os.path.expanduser('~/Library/Application Support')
    elif const.IS_WIN:
        # C:\Users\user\AppData\Roaming
        base = os.getenv('APPDATA')
    else:
        # Linuxなどの場合 (XDG規格)
        base = os.path.expanduser('~/.config')
    
    folder = os.path.join(base, 'SushiEricDataEditor')
    os.makedirs(folder, exist_ok=True)
    return folder

"""設定ファイルのフルパスを返す"""
def get_settings_path():
    return os.path.join(get_base_data_folder(), 'settings.json')

"""サーバープロファイルのフルパスを返す"""
def get_server_profiles():
    return os.path.join(get_base_data_folder(), 'server_profiles.json')

def is_float(string: str) -> bool:
    try:
        float(string)
        return True
    except (ValueError, TypeError):
        return False

def is_color(name: str) -> bool:
    if not name or not isinstance(name, str):
        return False
    # Literal[ColorName] の値を取得して判定
    valid_names = get_args(const.MiniMessageTag.ColorName)
    if name.lower() in valid_names:
        return True
    # HexCode 判定
    if re.match(r'^#[0-9a-fA-F]{6}$', name):
        return True
    return False

"""Adventureソースコードのロジックに基づくバリデーション"""
def is_valid_tag(tag_name: str) -> bool:
    # 略称の正規化マップ
    deco_map = {"b": "bold", "i": "italic", "em": "italic", "st": "strikethrough", "u": "underlined", "obf": "obfuscated"}
    
    # 1. 装飾判定（略称含む）
    clean_name = tag_name[1:] if tag_name.startswith("!") else tag_name
    if clean_name in get_args(const.MiniMessageTag.DecorationTag) or clean_name in deco_map:
        return True
    
    # 2. 単色判定
    if is_color(tag_name): return True
    
    # 3. 特殊タグの分解
    parts = tag_name.split(":")
    tag_type = parts[0]

    if tag_type == "rainbow":
        if len(parts) == 1: return True
        arg = parts[1]
        phase = arg[1:] if arg.startswith("!") else arg
        return not phase or is_float(phase)

    if tag_type in ["gradient", "transition"]:
        if len(parts) < 2: return True
        # 最後以外は色、最後は色or数値
        for i, p in enumerate(parts[1:]):
            if i == len(parts[1:]) - 1:
                if not (is_color(p) or is_float(p)): return False
            else:
                if not is_color(p): return False
        return True

    if tag_type == "shadow":
        if tag_name == "!shadow": return True
        if len(parts) == 2: return is_color(parts[1])
        if len(parts) == 3: return is_color(parts[1]) and is_float(parts[2])
        return False

    return False

"""フラットなタグ(<bold>)を構造化辞書へ変換。略称はここで正規化する。"""
def categorize_tags(flat_tag_list: List[str]) -> const.TagData:
    data: const.TagData = {
        "decoration": [],
        "color": {"type": "color", "value": const.MiniMessageTag.DEFAULT_COLOR, "args": []},
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
        if norm_name in get_args(const.MiniMessageTag.DecorationTag):
            if norm_name not in data["decoration"]:
                data["decoration"].append(norm_name)
            continue

        # --- 影 ---
        if tag_type == "shadow":
            data["shadow"] = parts[1] if len(parts) > 1 else const.MiniMessageTag.DEFAULT_SHADOW_COLOR
            continue
        elif tag_type == "!shadow":
            data["shadow"] = None
            continue

        # --- カラー系 ---
        if tag_type in ["gradient", "transition"]:
            colors = [p for p in parts[1:] if is_color(p)]
            # ソース準拠: 色がない場合は白黒デフォルト
            if not colors: colors = ["white", "black"]
            data["color"] = {
                "type": tag_type,
                "value": colors,
                "args": [p for p in parts[1:] if is_float(p)][:1]
            }
        elif tag_type == "rainbow":
            data["color"] = {"type": "rainbow", "value": "rainbow", "args": parts[1:]}
        elif is_color(tag_type):
            data["color"] = {"type": "color", "value": tag_type, "args": []}

    return data

"""構造化辞書から正規化されたタグリストを生成"""
def flatten_tag_data(tag_data: const.TagData) -> List[str]:
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

"""MiniMessage文字列を構造化された辞書リストに変換"""
def parse_strict_minimessage(raw: str) -> List[const.MiniMessageItem]:
    if not raw:
        return [create_empty_minimessage_data()]

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

    return result if result else [create_empty_minimessage_data()]

"""構造化された辞書リストをMiniMessage文字列に変換"""
def list_to_strict_minimessage(parsed_list: List[const.MiniMessageItem]) -> str:
    output = ""
    for item in parsed_list:
        text = item["text"].replace("<", r"\<")
        
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

"""
指定したカテゴリ（color, decoration, shadow等）にタグが属するか判定する。
full_tag は "<white>" や "<bold>" の形式を想定。
正常に変換されたタグを使用すること。
"""
def is_tag(category: str, full_tag: str) -> bool:
    """
    category: 'decoration', 'color', 'shadow' 等
    full_tag: '<bold>' や '<#FFFFFF>'
    """
    content = full_tag.strip("<>/")
    parts = content.split(":")
    base = parts[0]
    
    if category == "decoration":
        # Literal["bold", "italic", ...] に含まれるか
        return base in get_args(const.MiniMessageTag.DecorationTag)

    if category == "color":
        # 単色（引数なし）かつ ColorName または HexCode
        return len(parts) == 1 and is_color(base)

    if category == "special":
        return base in ["gradient", "transition", "rainbow"]

    if category == "shadow":
        return base == "shadow" or base == "!shadow"

    return False

"""データ新規作成"""
def create_empty_minimessage_data(text: str = "") -> const.MiniMessageItem:
    return {
        "text": text,
        "tags": {
            "decoration": [],
            "color": {"type": "color", "value": "white", "args": []},
            "shadow": None
        }
    }

def get_new_color(initial_color="#FFFFFF"):
    """
    カラーピッカーを開き、選択された色（またはデフォルト値）を返す
    """
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
    def __init__(self, data: const.MiniMessageItem, callback: Callable[[], None]):
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
    :param tag: const.MiniMessageTag.DecorationTag
    :param stats: Trueで有効化、Falseで無効化
    """
    def change_deco_tag(self, tag: const.MiniMessageTag.DecorationTag, stats: bool):
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
    :param mode: 変更したい色のconst.MiniMessageTag.ColorTagType。
    :param color: 変更後の色。'hexcode'かconst.MiniMessageTag.ColorNameで指定。
    :param index: 色がリストで保存される形式の場合、リストのインデックスを指定。デフォルト値は0。
    """
    def change_color(self, mode: const.MiniMessageTag.ColorTagType, color: str, index: int = 0):
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