"""
Modern Theme System with Smooth Transitions
Professional UI styling for PyQt5
"""

from PyQt5.QtGui import QColor, QPalette, QFont
from typing import Dict, Any


class ModernTheme:
    """Modern theme with smooth animations and professional styling"""

    # Color palettes
    MODERN_LIGHT = {
        'primary': '#2196F3',          # Blue
        'primary_dark': '#1976D2',     # Dark blue
        'primary_light': '#BBDEFB',    # Light blue
        'secondary': '#FFC107',        # Amber
        'secondary_dark': '#FFA000',   # Dark amber
        'success': '#4CAF50',          # Green
        'warning': '#FF9800',          # Orange
        'error': '#F44336',            # Red
        'info': '#00BCD4',             # Cyan
        'background': '#FAFAFA',       # Light grey
        'surface': '#FFFFFF',          # White
        'surface_elevated': '#FFFFFF', # White with shadow
        'text_primary': '#212121',     # Almost black
        'text_secondary': '#757575',   # Grey
        'text_disabled': '#BDBDBD',    # Light grey
        'divider': '#E0E0E0',          # Very light grey
        'border': '#E0E0E0',           # Very light grey
        'hover': '#F5F5F5',            # Very light grey
        'pressed': '#EEEEEE',          # Light grey
        'shadow': 'rgba(0, 0, 0, 0.1)' # Subtle shadow
    }

    MODERN_DARK = {
        'primary': '#BB86FC',          # Purple
        'primary_dark': '#985EFF',     # Dark purple
        'primary_light': '#E1BEE7',    # Light purple
        'secondary': '#03DAC6',        # Teal
        'secondary_dark': '#018786',   # Dark teal
        'success': '#00C853',          # Green
        'warning': '#FFB300',          # Amber
        'error': '#CF6679',            # Pink
        'info': '#00E5FF',             # Cyan
        'background': '#121212',       # Almost black
        'surface': '#1E1E1E',          # Dark grey
        'surface_elevated': '#2C2C2C', # Lighter dark grey
        'text_primary': '#FFFFFF',     # White
        'text_secondary': '#B0B0B0',   # Light grey
        'text_disabled': '#666666',    # Grey
        'divider': '#373737',          # Dark grey
        'border': '#373737',           # Dark grey
        'hover': '#2C2C2C',            # Lighter dark grey
        'pressed': '#3C3C3C',          # Even lighter grey
        'shadow': 'rgba(0, 0, 0, 0.3)' # Darker shadow
    }

    CLASSIC = {
        'primary': '#1E88E5',          # Classic blue
        'primary_dark': '#1565C0',
        'primary_light': '#90CAF9',
        'secondary': '#424242',        # Grey
        'secondary_dark': '#212121',
        'success': '#43A047',
        'warning': '#FB8C00',
        'error': '#E53935',
        'info': '#039BE5',
        'background': '#ECEFF1',
        'surface': '#FFFFFF',
        'surface_elevated': '#FFFFFF',
        'text_primary': '#263238',
        'text_secondary': '#546E7A',
        'text_disabled': '#90A4AE',
        'divider': '#CFD8DC',
        'border': '#B0BEC5',
        'hover': '#F5F5F5',
        'pressed': '#E0E0E0',
        'shadow': 'rgba(0, 0, 0, 0.08)'
    }

    @staticmethod
    def get_stylesheet(theme_name: str = 'modern_light') -> str:
        """
        Get complete stylesheet for the application

        Args:
            theme_name: 'modern_light', 'modern_dark', or 'classic'

        Returns:
            Complete QSS stylesheet string
        """
        themes = {
            'modern_light': ModernTheme.MODERN_LIGHT,
            'modern_dark': ModernTheme.MODERN_DARK,
            'classic': ModernTheme.CLASSIC
        }

        colors = themes.get(theme_name, ModernTheme.MODERN_LIGHT)

        return f"""
        /* ==================== GLOBAL ==================== */
        QMainWindow {{
            background-color: {colors['background']};
        }}

        QWidget {{
            font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
            font-size: 13px;
            color: {colors['text_primary']};
        }}

        /* ==================== BUTTONS ==================== */
        QPushButton {{
            background-color: {colors['primary']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: 500;
            font-size: 13px;
            min-height: 36px;
        }}

        QPushButton:hover {{
            background-color: {colors['primary_dark']};
        }}

        QPushButton:pressed {{
            background-color: {colors['primary_dark']};
            padding: 11px 19px 9px 21px;
        }}

        QPushButton:disabled {{
            background-color: {colors['divider']};
            color: {colors['text_disabled']};
        }}

        QPushButton#secondary {{
            background-color: {colors['surface']};
            color: {colors['primary']};
            border: 2px solid {colors['primary']};
        }}

        QPushButton#secondary:hover {{
            background-color: {colors['primary_light']};
        }}

        QPushButton#success {{
            background-color: {colors['success']};
        }}

        QPushButton#warning {{
            background-color: {colors['warning']};
        }}

        QPushButton#error {{
            background-color: {colors['error']};
        }}

        /* ==================== GROUP BOXES ==================== */
        QGroupBox {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 8px;
            margin-top: 16px;
            padding-top: 20px;
            font-weight: 600;
            font-size: 14px;
        }}

        QGroupBox::title {{
            color: {colors['primary']};
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 0 8px;
            background-color: {colors['surface']};
        }}

        /* ==================== TABS ==================== */
        QTabWidget::pane {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 8px;
            margin-top: -1px;
        }}

        QTabBar::tab {{
            background-color: {colors['surface']};
            color: {colors['text_secondary']};
            border: none;
            border-bottom: 3px solid transparent;
            padding: 12px 24px;
            font-weight: 500;
            min-width: 100px;
        }}

        QTabBar::tab:selected {{
            color: {colors['primary']};
            border-bottom: 3px solid {colors['primary']};
            background-color: {colors['surface']};
        }}

        QTabBar::tab:hover:!selected {{
            color: {colors['text_primary']};
            background-color: {colors['hover']};
        }}

        /* ==================== SLIDERS ==================== */
        QSlider::groove:horizontal {{
            background: {colors['divider']};
            height: 6px;
            border-radius: 3px;
        }}

        QSlider::handle:horizontal {{
            background: {colors['primary']};
            width: 20px;
            height: 20px;
            margin: -7px 0;
            border-radius: 10px;
        }}

        QSlider::handle:horizontal:hover {{
            background: {colors['primary_dark']};
            width: 24px;
            height: 24px;
            margin: -9px 0;
        }}

        QSlider::sub-page:horizontal {{
            background: {colors['primary']};
            border-radius: 3px;
        }}

        /* ==================== LINE EDITS ==================== */
        QLineEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border']};
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
            min-height: 36px;
        }}

        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 2px solid {colors['primary']};
        }}

        QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
            background-color: {colors['hover']};
            color: {colors['text_disabled']};
        }}

        /* ==================== COMBO BOX ==================== */
        QComboBox {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 2px solid {colors['border']};
            border-radius: 6px;
            padding: 8px 12px;
            min-height: 36px;
        }}

        QComboBox:hover {{
            border: 2px solid {colors['primary']};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}

        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {colors['text_secondary']};
            margin-right: 10px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            selection-background-color: {colors['primary']};
            selection-color: white;
            padding: 4px;
        }}

        /* ==================== PROGRESS BAR ==================== */
        QProgressBar {{
            background-color: {colors['divider']};
            border: none;
            border-radius: 4px;
            height: 8px;
            text-align: center;
        }}

        QProgressBar::chunk {{
            background-color: {colors['primary']};
            border-radius: 4px;
        }}

        /* ==================== LABELS ==================== */
        QLabel {{
            color: {colors['text_primary']};
            background: transparent;
        }}

        QLabel#heading {{
            font-size: 24px;
            font-weight: 600;
            color: {colors['text_primary']};
        }}

        QLabel#subheading {{
            font-size: 18px;
            font-weight: 500;
            color: {colors['text_primary']};
        }}

        QLabel#caption {{
            font-size: 12px;
            color: {colors['text_secondary']};
        }}

        QLabel#status_ok {{
            color: {colors['success']};
            font-weight: 600;
        }}

        QLabel#status_warning {{
            color: {colors['warning']};
            font-weight: 600;
        }}

        QLabel#status_error {{
            color: {colors['error']};
            font-weight: 600;
        }}

        /* ==================== SCROLL BARS ==================== */
        QScrollBar:vertical {{
            background: {colors['background']};
            width: 12px;
            border-radius: 6px;
        }}

        QScrollBar::handle:vertical {{
            background: {colors['divider']};
            border-radius: 6px;
            min-height: 30px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {colors['text_disabled']};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        /* ==================== TEXT EDIT ==================== */
        QTextEdit, QPlainTextEdit {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            padding: 8px;
        }}

        /* ==================== STATUS BAR ==================== */
        QStatusBar {{
            background-color: {colors['surface']};
            color: {colors['text_secondary']};
            border-top: 1px solid {colors['border']};
        }}

        /* ==================== MENU BAR ==================== */
        QMenuBar {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border-bottom: 1px solid {colors['border']};
            padding: 4px;
        }}

        QMenuBar::item {{
            padding: 8px 12px;
            border-radius: 4px;
        }}

        QMenuBar::item:selected {{
            background-color: {colors['hover']};
        }}

        QMenu {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            padding: 4px;
        }}

        QMenu::item {{
            padding: 8px 24px 8px 12px;
            border-radius: 4px;
        }}

        QMenu::item:selected {{
            background-color: {colors['primary']};
            color: white;
        }}

        /* ==================== TOOL TIP ==================== */
        QToolTip {{
            background-color: {colors['surface_elevated']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 6px;
            padding: 8px;
            font-size: 12px;
        }}

        /* ==================== CARDS (Custom Widget) ==================== */
        QFrame#card {{
            background-color: {colors['surface']};
            border-radius: 12px;
            border: 1px solid {colors['border']};
            padding: 16px;
        }}

        QFrame#card_elevated {{
            background-color: {colors['surface_elevated']};
            border-radius: 12px;
            border: none;
        }}
        """

    @staticmethod
    def get_palette(theme_name: str = 'modern_light') -> QPalette:
        """
        Get QPalette for the theme

        Args:
            theme_name: 'modern_light', 'modern_dark', or 'classic'

        Returns:
            QPalette configured for the theme
        """
        themes = {
            'modern_light': ModernTheme.MODERN_LIGHT,
            'modern_dark': ModernTheme.MODERN_DARK,
            'classic': ModernTheme.CLASSIC
        }

        colors = themes.get(theme_name, ModernTheme.MODERN_LIGHT)

        palette = QPalette()

        # Window colors
        palette.setColor(QPalette.Window, QColor(colors['background']))
        palette.setColor(QPalette.WindowText, QColor(colors['text_primary']))

        # Base colors (for edit widgets)
        palette.setColor(QPalette.Base, QColor(colors['surface']))
        palette.setColor(QPalette.AlternateBase, QColor(colors['hover']))

        # Text colors
        palette.setColor(QPalette.Text, QColor(colors['text_primary']))
        palette.setColor(QPalette.BrightText, QColor(colors['text_primary']))
        palette.setColor(QPalette.ToolTipBase, QColor(colors['surface_elevated']))
        palette.setColor(QPalette.ToolTipText, QColor(colors['text_primary']))

        # Button colors
        palette.setColor(QPalette.Button, QColor(colors['primary']))
        palette.setColor(QPalette.ButtonText, QColor('white'))

        # Highlight colors
        palette.setColor(QPalette.Highlight, QColor(colors['primary']))
        palette.setColor(QPalette.HighlightedText, QColor('white'))

        # Link colors
        palette.setColor(QPalette.Link, QColor(colors['primary']))
        palette.setColor(QPalette.LinkVisited, QColor(colors['primary_dark']))

        return palette

    @staticmethod
    def get_font() -> QFont:
        """Get the default font for the application"""
        font = QFont()
        font.setFamily('Segoe UI')
        font.setPointSize(10)
        return font
