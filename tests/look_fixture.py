"""Helper for tests that switch the real look (theme, text size, old base style): put everything back afterwards, so the tests that run later see what they expect."""
from deadlock_fps.shell import theme


def keep_look(case, app):
    """Remember the application's widget style, stylesheet and theme state now; restore them when the test ends."""
    sheet, base, choice, style = app.styleSheet(), theme._base_style, theme.choice(), app.style().objectName()

    def restore():
        app.setStyle(style)
        theme._base_style = base
        theme.apply(app, *choice)
        app.setStyleSheet(sheet)
    case.addCleanup(restore)
