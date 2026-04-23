from typing import TYPE_CHECKING, Dict, Literal, TypedDict, List, Union, Optional, Annotated

DataType = Literal["item", "crop", "ore", "mob"]

# ========== アイテム ==========

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

Rarity = Literal["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY", "MYTHIC", "VERY_MYTHIC", "ULTIMATE"]

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

class DisplayContent(TypedDict):
    name: str
    lore: List[List[MiniMessageItem]]

class ItemDataContent(TypedDict):
    display: DisplayContent
    rarity: Rarity

# ========== 作物 ==========
class CropDataContent(TypedDict):
    drop: List[str]

# ========== 鉱石 ==========
class OreDataContent(TypedDict):
    drop: List[str]

# ========== モブ ==========
class MobsDataContetnt(TypedDict):
    drop: List[str]

# ========== 全データ ==========
class AllData(TypedDict):
    item: Dict[str, ItemDataContent]
    crop: Dict[str, CropDataContent]
    ore: Dict[str, OreDataContent]
    mob: Dict[str, MobsDataContetnt]