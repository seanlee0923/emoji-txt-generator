# emoji-txt-generator
image to ascii / braille text

- remove_backgroud.py: remove solid-color background (jpg/jpeg/png -> transparent png)
- img_to_ascii.py: image -> ascii
- img_to_braille.py: image -> braille (dot characters)

usage

1. pip install

```bash
pip install pillow --break-system-packages
```

or

```bash
pip3 install pillow --break-system-packages
```

2. remove background (optional)

```bash
python3 remove_backgroud.py image.jpg -o image.png
```

3. image -> txt (choose ascii or braille)

```bash
python3 img_to_ascii.py image.png -w 60
python3 img_to_braille.py image.png -w 60
```

- `--color`: show colors in terminal
- `--fill`: use with `--color` to fill non-transparent areas
- `-w 60`: adjust size (width in characters)
- `--solid-color 39C5BB`: use one color with `--color` (optional)
- `--sharpen 1.5`: sharpen the result (optional, try 1.0~2.0)
- `--help`: see all options

run without `-o` and adjust while checking the terminal output. when it looks good, add `-o output.txt` to save as a text file.
