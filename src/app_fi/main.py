import flet as ft


def main(page: ft.Page) -> None:
    page.title = "App FI"
    page.add(ft.Text("App FI — base do projeto rodando."))


if __name__ == "__main__":
    ft.app(target=main)
