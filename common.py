import os, re
import const
from typing import List
from tkinter import colorchooser

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

"""カラーに使えるか"""
def is_color(name: str) -> bool:
    if not name or not isinstance(name, str):
        return False
    return (name in const.MiniMessageTag.COLORS or re.match(r'^#[0-9a-fA-F]{6}$', name))

"""浮動小数点数か"""
def is_float(val: str) -> bool:
    try:
        float(val)
        return True
    except ValueError:
        return False
    
"""タグが正常か判別する関数"""
def is_valid_tag(tag_name: str) -> bool:
    # 基本的な装飾と単色判定
    if tag_name in const.MiniMessageTag.DECORATIONS: return True
    if is_color(tag_name): return True
    if tag_name == f"!{const.MiniMessageTag.SHADOW}": return True # <!shadow>

    # 引数付きタグの分解
    parts = tag_name.split(":")
    tag_type = parts[0]

    # --- Rainbow: <rainbow:[!][phase]> ---
    if tag_type == const.MiniMessageTag.RAINBOW:
        if len(parts) == 1: return True # <rainbow>
        arg = parts[1]
        # 先頭が ! なら除外して残りが数値かチェック
        phase_str = arg[1:] if arg.startswith("!") else arg
        return not phase_str or is_float(phase_str)

    # --- Gradient / Transition: <tag:color:color...:phase> ---
    if tag_type in [const.MiniMessageTag.GRADIENT, const.MiniMessageTag.TRANSITION]:
        if len(parts) == 1: return True
        # 引数が「色」または「数値(phase)」であることを確認
        # <gradient:red:blue:0.5> のように複数を許容
        return all(is_color(p) or is_float(p) for p in parts[1:])

    # --- Shadow: <shadow:color> (floatなし) ---
    if tag_type == const.MiniMessageTag.SHADOW:
        if len(parts) == 2:
            return is_color(parts[1]) # 2番目が色ならOK。3番目以降(float)があればFalse
        return False

    return False

"""フラットなタグリストを構造化辞書に変換する"""
def categorize_tags(flat_tag_list: List[str]) -> const.TagData:
    data: const.TagData = {
        "decoration": [],
        "color": {"type": "color", "value": "white", "args": []},
        "shadow": None
    }

    for full_tag in flat_tag_list:
        if is_tag(const.MiniMessageTag.TYPE_DECORATION, full_tag):
            data["decoration"].append(full_tag)
            
        elif is_tag(const.MiniMessageTag.TYPE_SHADOW, full_tag):
            content = full_tag.strip("<>/")
            # <!shadow> なら None、<shadow:red> なら "red"
            data["shadow"] = None if content.startswith("!") else content.split(":")[-1]

        elif is_tag(const.MiniMessageTag.TYPE_SPECIAL, full_tag) or \
             is_tag(const.MiniMessageTag.TYPE_COLOR, full_tag):
            # 色は最後の一つが有効（上書き）
            content = full_tag.strip("<>/")
            parts = content.split(":")
            tag_type = parts[0]
            
            if tag_type in [const.MiniMessageTag.GRADIENT, const.MiniMessageTag.TRANSITION]:
                # value は色のリスト、args は比率などの数値リスト
                data["color"] = {
                    "type": tag_type,
                    "value": [p for p in parts[1:] if is_color(p)],
                    "args": [p for p in parts[1:] if is_float(p)]
                }
            elif tag_type == const.MiniMessageTag.RAINBOW:
                data["color"] = {"type": tag_type, "value": tag_type, "args": parts[1:]}
            else:
                # 単色
                data["color"] = {"type": "color", "value": tag_type, "args": []}

    return data

"""構造化辞書をフラットなタグリスト( <tag> の形 )に戻す"""
def flatten_tag_data(tag_data: const.TagData) -> List[str]:
    result = []
    
    # 1. カラー
    c = tag_data["color"]
    if c["type"] == "color":
        result.append(f"<{c['value']}>")
    elif c["type"] == const.MiniMessageTag.RAINBOW:
        arg_str = f":{':'.join(c['args'])}" if c["args"] else ""
        result.append(f"<{c['type']}{arg_str}>")
    else:
        # gradient, transition (valueのリストとargsのリストを結合)
        combined = c["value"] + c["args"]
        result.append(f"<{c['type']}:{':'.join(combined)}>")

    # 2. 装飾
    result.extend(tag_data["decoration"])

    # 3. 影
    if tag_data["shadow"]:
        result.append(f"<shadow:{tag_data['shadow']}>")
    
    return result

"""MiniMessage文字列を構造化された辞書リストに変換"""
def parse_strict_minimessage(raw: str) -> List[const.MiniMessageItem]:
    if not raw:
        # デフォルト値も新構造に合わせる
        return [{"text": "", "tags": categorize_tags([])}]

    pattern = r'((?<!\\)</?[^>]+>)'
    parts = re.split(pattern, raw)
    
    result = []
    active_stack = []

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
                        # 閉じタグとスタックの最後を比較（コロンより前で判定）
                        last_base = active_stack[-1].split(":")[0]
                        if last_base == tag_content:
                            active_stack.pop()
                else:
                    active_stack.append(tag_content)
                continue

        # テキスト部分の処理
        clean_text = part.replace(r"\<", "<")
        # ここで構造化！
        formatted_tags_dict = categorize_tags([f"<{t}>" for t in active_stack])
        
        result.append({
            "text": clean_text,
            "tags": formatted_tags_dict
        })

    return result if result else [{"text": "", "tags": categorize_tags([])}]

"""構造化された辞書リストをMiniMessage文字列に変換"""
def list_to_strict_minimessage(parsed_list: List[const.MiniMessageItem]) -> str:
    
    output = ""
    for item in parsed_list:
        text = item["text"].replace("<", r"\<")
        # 一旦フラットなリストに戻す
        flat_tags = flatten_tag_data(item["tags"])
        
        tags_open = "".join(flat_tags)
        
        # 閉じタグ生成（全てのタグに対して </base> を作る）
        close_tags = "".join([
            f"</{t.strip('<>/').split(':')[0]}>" 
            for t in reversed(flat_tags)
        ])
        
        output += f"{tags_open}{text}{close_tags}"
    return output

"""
指定したカテゴリ（color, decoration, shadow等）にタグが属するか判定する。
full_tag は "<white>" や "<bold>" の形式を想定。
正常に変換されたタグを使用すること。
"""
def is_tag(category: const.CategoryType, full_tag: str) -> bool:
    content = full_tag.strip("<>/")
    parts = content.split(":", 1)
    base = parts[0]
    
    # 装飾
    if category == const.MiniMessageTag.TYPE_DECORATION:
        return base in const.MiniMessageTag.DECORATIONS

    # 単色 (引数がある場合は False)
    if category == const.MiniMessageTag.TYPE_COLOR:
        if len(parts) > 1: return False
        return base in const.MiniMessageTag.COLORS or re.match(r'^#[0-9a-fA-F]{6}$', base) is not None

    # 特殊カラー (rainbow等)
    if category == const.MiniMessageTag.TYPE_SPECIAL:
        return base in const.MiniMessageTag.SPECIAL_COLOR_TAGS

    # 影
    if category == const.MiniMessageTag.TYPE_SHADOW:
        return base == const.MiniMessageTag.SHADOW or base == f"!{const.MiniMessageTag.SHADOW}"

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