import win32print
from services.auth import get_me


def print_receipt(text: str):
    printer_name = win32print.GetDefaultPrinter()

    handle = win32print.OpenPrinter(printer_name)
    try:
        job = win32print.StartDocPrinter(
            handle, 1, ("Cupom PDV", '', "RAW")
        )

        win32print.StartPagePrinter(handle)
        win32print.WritePrinter(handle,text.encode("utf-8"))
        win32print.EndPagePrinter(handle)
        win32print.EndDocPrinter(handle)

        print("Recibo impresso com sucesso.")
        print(text)
    finally:
        win32print.ClosePrinter(handle)
