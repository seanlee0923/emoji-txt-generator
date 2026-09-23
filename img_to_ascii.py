#!/usr/bin/env python3
"""
이미지를 컬러 아스키 아트로 변환하는 스크립트 (img2braille.py의 아스키 버전)

문자 하나 = 픽셀 하나(밝기 기반으로 문자 종류 선택) + 그 픽셀의 실제 색상을 ANSI 컬러로 입힘.
브레일 버전보다 해상도는 낮지만(문자당 1픽셀 vs 2x4픽셀), 문자 자체의 굵기 변화로
음영 표현이 가능해서 느낌이 다름.

사용법: python img_to_ascii.py <이미지경로> [옵션]
"""

import argparse
from PIL import Image, ImageEnhance

# 밝기 순서대로 나열된 문자 세트 (어두운 것 -> 밝은 것)
ASCII_CHARS_DETAILED = "@%#*+=-:. "
ASCII_CHARS_SIMPLE = "@#S%?*+;:,. "

RESAMPLE_FILTERS = {
    "nearest": Image.NEAREST,
    "bilinear": Image.BILINEAR,
    "bicubic": Image.BICUBIC,
    "lanczos": Image.LANCZOS,
}


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def resize_image(image, new_width, aspect_correction=0.55, resample="lanczos", sharpen=0.0):
    """터미널 폰트 비율(세로가 가로보다 긴 셀) 보정해서 리사이즈.
    아스키는 문자 하나 = 픽셀 하나라서, 브레일과 달리 세로를 줄여주는 보정(기본 0.55)이 필요함."""
    width, height = image.size
    aspect_ratio = height / width
    new_height = max(1, int(aspect_ratio * new_width * aspect_correction))

    resample_filter = RESAMPLE_FILTERS.get(resample, Image.LANCZOS)
    resized = image.resize((new_width, new_height), resample=resample_filter)

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


def image_to_ascii(path, width=100, threshold=128, invert=False, alpha_threshold=20,
                    aspect_correction=0.55, detailed=True, fill=False,
                    resample="lanczos", sharpen=0.0):
    """흑백 아스키 아트 (컬러 없음).

    fill=False (기본): 밝기 그라데이션에 따라 문자를 고름 (@ 진하게 ~ 공백 연하게) — 일반적인 아스키 아트
    fill=True: 밝기 threshold보다 어두운 픽셀은 진한 문자(@), 나머지는 공백 — 흑백 라인아트/실루엣용
    """
    try:
        image = Image.open(path)
    except Exception as e:
        print(f"이미지를 열 수 없습니다: {e}")
        return None

    image = resize_image(image, width, aspect_correction, resample, sharpen)
    alpha = get_alpha(image)
    gray = image.convert("L")
    gray_pixels = list(gray.getdata())

    chars = ASCII_CHARS_DETAILED if detailed else ASCII_CHARS_SIMPLE
    if invert:
        chars = chars[::-1]

    img_w = image.width
    lines = []
    for y in range(image.height):
        line = ""
        for x in range(img_w):
            idx = y * img_w + x
            is_opaque = alpha is None or alpha[idx] >= alpha_threshold
            if not is_opaque:
                line += " "
                continue
            brightness = gray_pixels[idx]
            if fill:
                char = chars[0] if brightness < threshold else " "
                if invert:
                    char = " " if brightness < threshold else chars[0]
            else:
                char = chars[brightness * (len(chars) - 1) // 255]
            line += char
        lines.append(line)

    return "\n".join(lines)


def image_to_ascii_color(path, width=100, threshold=128, invert=False, alpha_threshold=20,
                          aspect_correction=0.55, detailed=True, fill=False, solid_color=None,
                          resample="lanczos", sharpen=0.0):
    """컬러 아스키 아트 (ANSI 트루컬러 코드 포함, fastfetch 등에서 컬러로 보임).

    fill=False (기본): 흑백 라인아트용. 밝기 그라데이션대로 문자 종류를 고르고, 그 픽셀의 원래 색을 입힘
    fill=True: 꽉 찬 컬러 일러스트용. 불투명한 픽셀은 밝기 상관없이 진한 문자(@)로 채우고 원래 색을 입힘
               (실루엣 전체가 색칠된 블록처럼 보임)
    solid_color: 지정하면 원본 색 대신 이 색 하나로 통일 (HEX)
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

    chars = ASCII_CHARS_DETAILED
    if invert:
        chars = chars[::-1]

    solid_rgb = hex_to_rgb(solid_color) if solid_color else None

    img_w = image.width
    lines = []
    for y in range(image.height):
        line = ""
        for x in range(img_w):
            idx = y * img_w + x
            is_opaque = alpha is None or alpha[idx] >= alpha_threshold
            if not is_opaque:
                line += " "
                continue

            brightness = gray_pixels[idx]
            if fill:
                is_on = True
                char = chars[0]
            else:
                is_on = True  # 흑백 라인아트 모드는 항상 그라데이션 문자를 찍되, threshold보다 밝으면 공백 취급 안 함
                char = chars[brightness * (len(chars) - 1) // 255]

            if not is_on or char == " ":
                line += " "
                continue

            r, g, b = solid_rgb if solid_rgb is not None else rgb_pixels[idx]
            line += f"\033[38;2;{r};{g};{b}m{char}\033[0m"
        lines.append(line)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="이미지를 컬러 아스키 아트로 변환")
    parser.add_argument("image", help="변환할 이미지 파일 경로")
    parser.add_argument("-w", "--width", type=int, default=100, help="출력 가로 문자 수 (기본값: 100)")
    parser.add_argument("-o", "--output", help="결과를 저장할 파일 경로 (지정 안 하면 화면에 출력)")
    parser.add_argument("-t", "--threshold", type=int, default=128, help="밝기 임계값 0~255 (기본값: 128), --fill 모드에서 사용")
    parser.add_argument("--simple", action="store_true", help="더 단순한 문자셋 사용 (흑백 모드에서만 적용)")
    parser.add_argument("--invert", action="store_true", help="밝기 반전 (배경이 밝은 이미지일 때 유용)")
    parser.add_argument("--color", action="store_true", help="ANSI 컬러 코드 포함 (터미널에서 컬러로 보임, fastfetch용)")
    parser.add_argument("--fill", action="store_true", help="꽉 찬 컬러 일러스트용. 불투명한 영역 전체를 진한 문자로 채움 (--color와 함께 쓰면 부위별 원본 색이 입혀짐)")
    parser.add_argument("--solid-color", help="지정한 단일 색상(HEX, 예: 39C5BB)으로 전체를 칠함. --color와 함께 사용")
    parser.add_argument("--alpha-threshold", type=int, default=20, help="이 값보다 투명도가 낮은 픽셀은 배경으로 간주해 비움 (기본값: 20, 0~255)")
    parser.add_argument("--aspect-correction", type=float, default=0.55, help="세로 비율 보정 (기본값: 0.55). 결과가 위아래로 늘어나면 값을 내리고, 짜부라지면 값을 올리세요")
    parser.add_argument("--resample", choices=list(RESAMPLE_FILTERS.keys()), default="lanczos", help="다운스케일 리샘플링 방식 (기본값: lanczos)")
    parser.add_argument("--sharpen", type=float, default=0.0, help="리사이즈 후 샤픈 강도 (기본값: 0 = 미적용). 1.0~2.0 권장")

    args = parser.parse_args()

    if args.color:
        result = image_to_ascii_color(
            args.image, width=args.width, threshold=args.threshold,
            invert=args.invert, alpha_threshold=args.alpha_threshold,
            aspect_correction=args.aspect_correction, fill=args.fill,
            solid_color=args.solid_color, resample=args.resample, sharpen=args.sharpen
        )
    else:
        result = image_to_ascii(
            args.image, width=args.width, threshold=args.threshold,
            invert=args.invert, alpha_threshold=args.alpha_threshold,
            aspect_correction=args.aspect_correction, detailed=not args.simple,
            fill=args.fill, resample=args.resample, sharpen=args.sharpen
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
