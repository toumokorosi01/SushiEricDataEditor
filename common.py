import os, re
import const

minimessage_tag = const.MiniMessageTag

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

"""タグが正常か判別する関数"""
def is_valid_tag(tag_name):
    # 名前付きカラー、16進数カラー(#RRGGBB)、装飾、影(shadow:...)を判定
    if tag_name in const.MiniMessageTag.COLORS: return True
    if tag_name in const.MiniMessageTag.DECORATIONS: return True
    if re.match(r'^#[0-9a-fA-F]{6}$', tag_name): return True
    if tag_name.startswith("shadow:"): return True
    return False

"""MiniMessageを[{'text': '文字列', 'tags': ['タグ']}]に変換する関数"""
def parse_strict_minimessage(raw: str) -> list[dict]:
    # <reset> は禁止なので事前に除去、または無効化
    if not raw: return []

    # タグの分割パターン (shadow: や #hex を含む)
    pattern = r'((?<!\\)</?[^>]+>)'
    parts = re.split(pattern, raw)
    
    result = []
    active_stack = [] # 開いているタグを順番に保持

    for part in parts:
        if not part: continue

        # タグの判定
        if part.startswith("<") and part.endswith(">"):
            is_closing = part.startswith("</")
            # タグの中身を取り出す (例: <shadow:red> -> shadow:red)
            tag_content = part.strip("<>/")

            # 厳格モード: reset は無視（処理しない）
            if tag_content == "reset":
                continue

            if is_valid_tag(tag_content):
                if is_closing:
                    # 厳格モード: 最後に開いたタグと一致する場合のみ閉じる
                    if active_stack and active_stack[-1] == tag_content:
                        active_stack.pop()
                    # ※一致しない場合は閉じない（何もしない）
                else:
                    # 開始タグ: スタックに追加
                    active_stack.append(tag_content)
                continue

        # テキストデータの作成
        clean_text = part.replace(r"\<", "<")
        
        # スタックにあるタグを <tag> 形式で保持
        formatted_tags = [f"<{t}>" for t in active_stack]
        
        result.append({
            "text": clean_text,
            "tags": formatted_tags
        })

    return result

"""[{'text': '文字列', 'tags': ['タグ']}]をMiniMessageに変換する関数"""
def list_to_strict_minimessage(parsed_list: list[dict]) -> str:
    output = ""
    for item in parsed_list:
        text = item["text"].replace("<", r"\<")
        tags_open = "".join(item["tags"])
        # 閉じタグはスタックの逆順で生成
        tags_close = "".join([f"</{t.strip('<>')}>" for t in reversed(item["tags"])])
        
        # 実際には、連続する同じタグなら結合する処理が必要ですが、
        # 最も安全なのは「各テキストごとにタグで挟む」形式です。
        output += f"{tags_open}{text}{tags_close}"
    return output

