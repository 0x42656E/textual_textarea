from textual.app import App, ComposeResult
from textual.widgets import Input

from textual_textarea import TextArea


class MyApp(App):
    def compose(self) -> ComposeResult:
        yield TextArea()


my_app = MyApp()
my_app.run()
