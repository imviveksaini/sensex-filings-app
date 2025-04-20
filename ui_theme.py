def apply_custom_styles(theme):
    if theme == "Dark":
        bg_color = "#0f1117"
        text_color = "#ffffff"
        table_bg = "#1c1e26"
    else:
        bg_color = "#f4f9fc"
        text_color = "#1f2937"
        table_bg = "#ffffff"

    return f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        html, body, [class*='css'] {{
            font-family: 'Inter', sans-serif !important;
            background-color: {bg_color} !important;
            color: {text_color} !important;
        }}
        .stButton>button {{
            background-color: #3b82f6;
            color: white;
            padding: 0.5em 1em;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            font-size: 16px;
        }}
        table {{
            background-color: {table_bg};
            font-size: 14px;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
        }}
    </style>
    """
