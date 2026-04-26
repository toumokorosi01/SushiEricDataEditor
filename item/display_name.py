import customtkinter as ctk
import const, data_content as dc

class DisplayName(ctk.CTkFrame):
    def __init__(self, master, item_data: dc.ItemDataContent, update_callback, update_sidebar_callback, **kwargs):
        # 外側の枠線設定を引き継ぐ
        super().__init__(
            master, 
            fg_color="transparent", 
            border_color=const.line_color, 
            border_width=1, 
            corner_radius=0,
            **kwargs
        )
        
        self.item_data = item_data
        self.display_data = item_data["display"]
        self.update_callback = update_callback
        self.update_sidebar_callback = update_sidebar_callback

        self.setup_widgets()

    """サイドバーとヘッダーを更新する"""
    def on_update(self):
        self.update_callback()
        self.update_sidebar_callback()

    """
    テキストの変更
    :param text: 新しい文字列
    """
    def change_text(self, text: str):
        self.display_data["name"] = text
        self.on_update()

    """表示名のベースのフレーム"""
    def setup_widgets(self):
        label = ctk.CTkLabel(self, text="表示名", font=const.UI_FONT)
        label.pack(pady=3) 

        # 入力欄の設定
        name_var = ctk.StringVar(value=self.display_data.get("name", ""))
        name_var.trace_add("write", lambda *_: self.change_text(name_var.get()))
        # 入力欄
        entry = ctk.CTkEntry(self, textvariable=name_var, width=200, font=const.UI_FONT)
        entry.pack(pady=3) 
    