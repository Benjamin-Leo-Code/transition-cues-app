"""Offline PIN recovery. Stop the running app and back up its data first."""
import getpass
from pathlib import Path
import sys
from server import Store

if __name__ == '__main__':
    if len(sys.argv) != 2 or not (Path(sys.argv[1]) / 'library.json').is_file():
        sys.exit('Usage: python3 reset_pin.py /path/to/existing/transition-cues-data')
    print('Stop the app and back up library.json before continuing.')
    pin = getpass.getpass('New PIN (4 to 8 digits): ')
    if pin != getpass.getpass('Confirm new PIN: '):
        sys.exit('PINs did not match. Nothing changed.')
    store = Store(sys.argv[1])
    try:
        store.set_pin(pin)
        store.save()
    except ValueError as error:
        sys.exit(str(error))
    print('PIN updated. Restart the app.')
