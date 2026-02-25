from PIL import ImageFilter, ImageOps

def process_manna_logo(logo_file):
    """將上傳的 Logo 去背景並生成黑、白兩色高對比向量風版本"""
    with st.spinner("🎨 Manna AI 正在進行高級 Logo 提煉 (Vector-Smoothing)..."):
        input_image = Image.open(logo_file)
        
        # 1. AI 高級去背景 (啟動 Alpha Matting 模式令邊緣更細緻)
        # alpha_matting=True 可以處理髮絲或細微邊緣
        no_bg = remove(input_image, alpha_matting=True, 
                       alpha_matting_foreground_threshold=240,
                       alpha_matting_background_threshold=10,
                       alpha_matting_erode_size=10)
        
        # 2. 提取透明層並進行平滑處理 (這是產生 SVG 質感的關鍵)
        alpha = no_bg.getchannel('A')
        # 輕微模糊邊緣
        alpha = alpha.filter(ImageFilter.GaussianBlur(radius=0.5))
        # 強化邊緣對比，消除半透明雜點
        alpha = alpha.point(lambda p: 255 if p > 128 else 0) 

        # 3. 生成「純白透明版」 (White Logo)
        # 直接創建純色層並蓋上處理好的 Alpha Mask
        white_logo = Image.new("RGBA", no_bg.size, (255, 255, 255, 255))
        white_logo.putalpha(alpha)

        # 4. 生成「純黑透明版」 (Black Logo)
        black_logo = Image.new("RGBA", no_bg.size, (0, 0, 0, 255))
        black_logo.putalpha(alpha)

        # 輔助函數：轉為 Base64
        def to_b64(img):
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True) # 優化檔案大小
            return base64.b64encode(buf.getvalue()).decode()

        return to_b64(white_logo), to_b64(black_logo)
