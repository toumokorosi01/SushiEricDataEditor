import platform
from typing import Literal, TypedDict, List, Union, Optional, Annotated

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

DATA_PATHS = {
    "アイテム": f"{dataFolder}/item/stats.yml",
    "鉱石": f"{dataFolder}/block/stats/ore",
    "作物": f"{dataFolder}/block/stat/wood.yml",
    "木": f"{dataFolder}/block/stat/wood.yml",
    "モブ": f"{dataFolder}/mobs.yml"
}

# カラーデコレーションの構造
class ColorDeco(TypedDict):
    type: MiniMessageTag.ColorTagType
    value: Union[
        MiniMessageTag.CustomColor, 
        List[MiniMessageTag.CustomColor]
    ] # 単色なら "#ffffff", グラデーションなら ["red", "blue"]
    args: List[str]  # 引数（!5 や phase数値など）

# タグ全体の構造
class TagData(TypedDict):
    decoration: List[MiniMessageTag.DecorationTag]      # ["<bold>", "<italic>"]
    color: ColorDeco           # カラー情報
    shadow: Optional[MiniMessageTag.CustomColor]      # 色 or None

class MiniMessageItem(TypedDict):
    text: str
    tags: TagData

class MiniMessageTag:
    ColorTagType = Literal["color", "rainbow", "gradient", "transition", "shadow"]
    DecorationTag = Literal["bold", "italic", "underlined", "strikethrough", "obfuscated"]

    ColorName = Literal[
        "black", "dark_blue", "dark_green", "dark_aqua", "dark_red", 
        "dark_purple", "gold", "gray", "grey", "dark_gray", "dark_grey", 
        "blue", "green", "aqua", "red", "light_purple", "yellow", "white"
    ]
    HexCode = Annotated[str, "pattern: ^#[0-9a-fA-F]{6}$"]
    CustomColor = Union[ColorName, HexCode, str]

    DEFAULT_COLOR: CustomColor = "white"
    DEFAULT_SHADOW_COLOR: CustomColor = "black"
    DEFAULT_HEX: HexCode = "#FFFFFF"
    COLORS = [
        "black", "dark_blue", "dark_green", "dark_aqua", "dark_red", 
        "dark_purple", "gold", "gray", "grey", "dark_gray", "dark_grey", 
        "blue", "green", "aqua", "red", "light_purple", "yellow", "white"
    ]


class ItemData:
    display = "display_name"
    lore = "lore"
