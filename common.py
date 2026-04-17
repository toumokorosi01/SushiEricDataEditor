import os, re, const
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
    
def minimessage_to_dict(raw: str) -> list[dict[str, list[str]]]:
    """
    MiniMessage形式の文字列を解析し、テキストとそのテキストに適用されるタグのリストを返す。
    """
    if not raw:
        return []

    # 1. 正規表現で分割
    # (?<!\\) は直前に \ がないことを確認（エスケープ対応）
    # <[^>]+> は最短一致でタグを抽出
    pattern = r'((?<!\\)<[^>]+>)'
    parts = re.split(pattern, raw)
    
    result = []
    current_tags = [] # 現在有効なタグのスタック

    for part in parts:
        if not part:
            continue
            
        # タグとしての条件判定
        # 1. < で始まり > で終わる
        # 2. かつ DUMMY_TAGS に含まれる
        # 3. かつ 直前に \ がない（re.splitの時点で分離済みだが念のため）
        if part.startswith("<") and part.endswith(">") and part in minimessage_tag.ALL_TAG:
            # タグとして処理
            # ※Adventure仕様に寄せるなら、ここで色タグなら上書き、boldなら追加等のロジックが必要
            # 今回は単純にリストに溜めていく形にします
            if part not in current_tags:
                current_tags.append(part)
        else:
            # 文字として処理（エスケープされた \<red> 等もここに来る）
            # エスケープ記号自体は表示不要なので除去
            clean_text = part.replace(r"\<", "<")
            
            # リストに追加
            # current_tags[:] でコピーを渡さないと、後でタグが変わった時に全部書き換わるので注意
            result.append({clean_text: current_tags[:]})

    return result

# def dict_to_minimessage(raw_data: list) -> str:
#     for data in raw_data:
#         

raw = minimessage_to_dict(r"通常\\<red>文字<red>赤色<bold>太字の赤</bold>")
print(raw)