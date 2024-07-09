## drm_player


frambuffer setup in C in drm_display.c
compile with: 
```gcc -shared -o libdrm_display.so -I/usr/include/libdrm -fPIC drm_display.c -ldrm```bash

python bindings in drm_display.py

to use
 
```
import DRMdisplay
```python

initialize a display

```
display = DRMDisplay('/dev/dri/card0')
```python

```
display.send_full_image(img)
```python
