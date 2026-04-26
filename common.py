import os, re
import const
from typing import get_args
import data_content as dc

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
    valid_names = get_args(dc.MiniMessageTag.ColorName)
    if name.lower() in valid_names:
        return True
    # HexCode 判定
    if re.match(r'^#[0-9a-fA-F]{6}$', name):
        return True
    return False

