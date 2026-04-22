import platform
from typing import Dict, TypedDict
import data_content as dc

# OSの判定
CURRENT_OS = platform.system()
IS_WIN = (CURRENT_OS == "Windows")
IS_MAC = (CURRENT_OS == "Darwin")
IS_SUPPORTED = IS_WIN or IS_MAC

# フォントの設定
if IS_MAC:
    # Mac用の高品質フォント
    UI_FONT_FAMILY = "Hiragino Kaku Gothic ProN"
    CODE_FONT_FAMILY = "Menlo"
else:
    # Windows用の高品質フォント
    UI_FONT_FAMILY = "Meiryo"
    CODE_FONT_FAMILY = "Consolas"

# サイズ
FONT_SIZE_NORMAL = 15
FONT_SIZE_TITLE = 18

# 最終的なフォント指定用（タプル形式）
UI_FONT = (UI_FONT_FAMILY, FONT_SIZE_NORMAL)
UI_FONT_BOLD = (UI_FONT_FAMILY, FONT_SIZE_NORMAL, "bold")
TITLE_FONT = (UI_FONT_FAMILY, FONT_SIZE_TITLE, "bold")

top_tab_fg_color = ("#f1f1f1", "#191a1b")
top_tab_hover_color = ("#FFFFFF", "#121314")
top_tab_select_line_color = "#00ffff"
line_color = ("#e8e8e8", "#2c2d2e")
bottom_main_color = top_tab_hover_color
bottom_side_color = top_tab_fg_color
bottom_side_hover_color = line_color
text_color = ("#000000", "#ffffff")

dataFolder = "/plugins/SushiEricServerPlugin21"
item_stats_path = f"{dataFolder}/item/stats.yml"

# 2. 1つ分のデータ構造を定義
class DataInfo(TypedDict):
    path: str
    display_name: str

# 3. まとめて定義
# こうすることで、DATA_CONFIG["item"]["path"] のようにアクセスでき、補完も効きます
DATA_CONFIG: Dict[dc.DataType, DataInfo] = {
    "item": {
        "path": f"{dataFolder}/item/stats.yml",
        "display_name": "アイテム"
    },
    "crop": {
        "path": f"{dataFolder}/block/stat/wood.yml",
        "display_name": "作物"
    },
    "ore": {
        "path": f"{dataFolder}/block/stats/ore",
        "display_name": "鉱石"
    },
    "mob": {
        "path": f"{dataFolder}/mobs.yml",
        "display_name": "モブ"
    }
}

EMPTY_ITEM_DATA: dc.ItemDataContent = {
    "display": {
        "name": "",
        "lore": []
    },
    "rarity": "COMMON"
}