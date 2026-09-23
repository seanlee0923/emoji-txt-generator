#!/usr/bin/env python3
"""
이미지를 유니코드 브레일(점자) 아트로 변환하는 스크립트
문자 하나가 2x4 픽셀 블록을 표현해서 일반 아스키보다 훨씬 정교한 결과가 나옴

사용법: python img2braille.py <이미지경로> [옵션]
"""

import argparse
from PIL import Image, ImageFilter, ImageEnhance

# 브레일 문자 내 점 위치 -> 비트 매핑
# (dx, dy) : bit
#   (0,0)=0x01  (1,0)=0x08
#   (0,1)=0x02  (1,1)=0x10
#   (0,2)=0x04  (1,2)=0x20
#   (0,3)=0x40  (1,3)=0x80
DOT_BITS = {
    (0, 0): 0x01, (0, 1): 0x02, (0, 2): 0x04, (0, 3): 0x40,
    (1, 0): 0x08, (1, 1): 0x10, (1, 2): 0x20, (1, 3): 0x80,
}
BRAILLE_BASE = 0x2800


RESAMPLE_FILTERS = {
    "nearest": Image.NEAREST,
    "bilinear": Image.BILINEAR,
    "bicubic": Image.BICUBIC,
    "lanczos": Image.LANCZOS,
}


def resize_image(image, char_width, aspect_correction=1.0, resample="lanczos", sharpen=0.0):
    """브레일 문자 1개 = 가로 2픽셀, 세로 4픽셀 도트 블록.
    터미널 글자 셀 자체가 이미 세로로 긴 형태(보통 높이:너비 ≈ 2:1)인데,
    브레일 문자가 그 셀 안에 2x4 도트를 채우는 구조라서
    "도트 하나가 차지하는 실제 화면 비율"은 (셀비율 2 / 도트비율 4:2=2) = 1에 가까움.
    즉 별도 축소 보정이 거의 필요 없고, aspect_correction으로 미세 조정만 함
    (터미널 폰트가 더 세로로 길면 1.1~1.3 쪽으로, 더 정사각형에 가까우면 0.8~0.9 쪽으로).

    resample: 리샘플링 방식. lanczos가 기본이며 저해상도로 줄일 때 윤곽을 가장 또렷하게 보존함
              (nearest/bilinear/bicubic도 선택 가능, 비교해보고 싶을 때 사용)
    sharpen: 리사이즈 직후 샤픈 강도 (0 = 적용 안 함, 1.0~2.0 정도가 적당). 저해상도에서
             뭉개지는 경계선을 다시 강조해서 디테일 체감을 높여줌. RGB 채널에만 적용되고
             알파(투명도) 채널은 그대로 유지됨"""
    pixel_width = char_width * 2
    orig_w, orig_h = image.size
    aspect_ratio = orig_h / orig_w
    pixel_height = int(aspect_ratio * pixel_width * aspect_correction)
    # 세로를 4의 배수로 맞춤
    pixel_height = max(4, round(pixel_height / 4) * 4)
    # 가로를 2의 배수로 맞춤
    pixel_width = max(2, round(pixel_width / 2) * 2)

    resample_filter = RESAMPLE_FILTERS.get(resample, Image.LANCZOS)
    resized = image.resize((pixel_width, pixel_height), resample=resample_filter)

    if sharpen and sharpen > 0:
        has_alpha = "A" in resized.getbands()
        if has_alpha:
            alpha_channel = resized.getchannel("A")
            rgb = resized.convert("RGB")
        else:
            rgb = resized

        rgb = ImageEnhance.Sharpness(rgb).enhance(1.0 + sharpen)

        if has_alpha:
            resized = rgb.convert("RGBA")
            resized.putalpha(alpha_channel)
        else:
            resized = rgb

    return resized


def get_alpha(image):
    if "A" not in image.getbands():
        return None
    return list(image.getchannel("A").getdata())


def image_to_braille(path, width=60, threshold=128, invert=False, alpha_threshold=20,
                      aspect_correction=1.0, fill=False, resample="lanczos", sharpen=0.0):
    try:
        image = Image.open(path)
    except Exception as e:
        print(f"이미지를 열 수 없습니다: {e}")
        return None

    image = resize_image(image, width, aspect_correction, resample, sharpen)
    alpha = get_alpha(image)
    gray = image.convert("L")
    gray_pixels = list(gray.getdata())

    img_w, img_h = image.size
    lines = []

    for cy in range(0, img_h, 4):
        line = ""
        for cx in range(0, img_w, 2):
            dot_pattern = 0
            for dy in range(4):
                for dx in range(2):
                    x, y = cx + dx, cy + dy
                    if x >= img_w or y >= img_h:
                        continue
                    idx = y * img_w + x
                    is_opaque = alpha is None or alpha[idx] >= alpha_threshold
                    if not is_opaque:
                        continue  # 투명 -> 점 안 찍음
                    if fill:
                        is_on = True
                    else:
                        brightness = gray_pixels[idx]
                        is_on = brightness < threshold
                        if invert:
                            is_on = not is_on
                    if is_on:
                        dot_pattern |= DOT_BITS[(dx, dy)]
            line += chr(BRAILLE_BASE + dot_pattern)
        lines.append(line)

    return "\n".join(lines)


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def image_to_braille_color(path, width=60, threshold=128, invert=False, alpha_threshold=20,
                            aspect_correction=1.0, solid_color=None, fill=False,
                            resample="lanczos", sharpen=0.0):
    """블록 평균 색상(또는 solid_color 지정 시 단일 색상)으로 ANSI 컬러를 입힌 버전

    fill=False (기본): 흑백 라인아트용. 밝기가 threshold보다 어두운 픽셀만 점으로 찍음
    fill=True: 꽉 찬 컬러 일러스트용. 투명하지 않은(불투명한) 픽셀은 밝기 상관없이 다 점으로 찍어서
               실루엣 전체를 채우고, 그 부분의 원본 색을 그대로 입힘
    """
    try:
        image = Image.open(path)
    except Exception as e:
        print(f"이미지를 열 수 없습니다: {e}")
        return None

    image = resize_image(image, width, aspect_correction, resample, sharpen)
    alpha = get_alpha(image)
    rgb_image = image.convert("RGB")
    gray = image.convert("L")
    rgb_pixels = list(rgb_image.getdata())
    gray_pixels = list(gray.getdata())

    solid_rgb = hex_to_rgb(solid_color) if solid_color else None

    img_w, img_h = image.size
    lines = []

    for cy in range(0, img_h, 4):
        line = ""
        for cx in range(0, img_w, 2):
            dot_pattern = 0
            rs, gs, bs, n = 0, 0, 0, 0
            for dy in range(4):
                for dx in range(2):
                    x, y = cx + dx, cy + dy
                    if x >= img_w or y >= img_h:
                        continue
                    idx = y * img_w + x
                    is_opaque = alpha is None or alpha[idx] >= alpha_threshold
                    if not is_opaque:
                        continue

                    if fill:
                        is_on = True
                    else:
                        brightness = gray_pixels[idx]
                        is_on = brightness < threshold
                        if invert:
                            is_on = not is_on

                    if is_on:
                        dot_pattern |= DOT_BITS[(dx, dy)]
                        r, g, b = rgb_pixels[idx]
                        rs += r; gs += g; bs += b; n += 1
            char = chr(BRAILLE_BASE + dot_pattern)
            if n > 0 and dot_pattern != 0:
                if solid_rgb is not None:
                    r, g, b = solid_rgb
                else:
                    r, g, b = rs // n, gs // n, bs // n
                line += f"\033[38;2;{r};{g};{b}m{char}\033[0m"
            else:
                line += char
        lines.append(line)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="이미지를 브레일(점자) 아트로 변환")
    parser.add_argument("image", help="변환할 이미지 파일 경로")
    parser.add_argument("-w", "--width", type=int, default=60, help="출력 가로 문자 수 (기본값: 60). 실제 픽셀 가로는 이 값의 2배")
    parser.add_argument("-o", "--output", help="결과를 저장할 파일 경로 (지정 안 하면 화면에 출력)")
    parser.add_argument("-t", "--threshold", type=int, default=128, help="밝기 임계값 0~255 (기본값: 128). 낮을수록 어두운 부분만 점으로 찍힘")
    parser.add_argument("--invert", action="store_true", help="밝기 반전 (배경이 어둡고 캐릭터가 밝은 이미지일 때 유용)")
    parser.add_argument("--color", action="store_true", help="ANSI 컬러 코드 포함 (터미널에서 컬러로 보임, fastfetch용)")
    parser.add_argument("--alpha-threshold", type=int, default=20, help="이 값보다 투명도가 낮은 픽셀은 배경으로 간주해 비움 (기본값: 20, 0~255)")
    parser.add_argument("--aspect-correction", type=float, default=1.0, help="세로 비율 미세 보정 (기본값: 1.0). 결과가 위아래로 짜부라지면 값을 올리고, 위아래로 늘어나면 값을 내리세요")
    parser.add_argument("--solid-color", help="지정한 단일 색상(HEX, 예: 39C5BB)으로 전체를 칠함. --color와 함께 사용. 지정 안 하면 원본 이미지 색상을 그대로 씀")
    parser.add_argument("--fill", action="store_true", help="흑백 라인아트가 아니라 꽉 찬 컬러 일러스트용. 밝기 무시하고 불투명한 영역 전체를 점으로 채움 (--color와 함께 쓰면 부위별 원본 색이 그대로 입혀짐)")
    parser.add_argument("--resample", choices=list(RESAMPLE_FILTERS.keys()), default="lanczos",
                         help="다운스케일 리샘플링 방식 (기본값: lanczos, 저해상도에서 윤곽을 가장 또렷하게 보존함)")
    parser.add_argument("--sharpen", type=float, default=0.0,
                         help="리사이즈 후 샤픈 강도 (기본값: 0 = 미적용). 1.0~2.0 정도로 주면 저해상도에서도 경계가 또렷해짐")

    args = parser.parse_args()

    if args.color:
        result = image_to_braille_color(
            args.image, width=args.width, threshold=args.threshold,
            invert=args.invert, alpha_threshold=args.alpha_threshold,
            aspect_correction=args.aspect_correction, solid_color=args.solid_color,
            fill=args.fill, resample=args.resample, sharpen=args.sharpen
        )
    else:
        result = image_to_braille(
            args.image, width=args.width, threshold=args.threshold,
            invert=args.invert, alpha_threshold=args.alpha_threshold,
            aspect_correction=args.aspect_correction, fill=args.fill,
            resample=args.resample, sharpen=args.sharpen
        )

    if result is None:
        return

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"저장 완료: {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()
