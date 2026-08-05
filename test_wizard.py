from browser_use import *

start_local_daemon()
new_tab("http://127.0.0.1:8000/")
wait_for_load()
print(page_info())
